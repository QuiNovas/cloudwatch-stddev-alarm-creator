import boto3
import json
import logging.config
import re

from datetime import datetime, timedelta
from os import environ
from statistics import mean, pstdev


ALARM_ACTIONS = [ x.strip() for x in environ.get('ALARM_ACTIONS', '').split(',') if x ]
ALARM_NAME = environ.get('ALARM_NAME')
BOUNDS = environ.get('BOUNDS', 'Both')
CLOUDWATCH = boto3.client('cloudwatch')
DATAPOINTS_TO_ALARM = int(environ['DATAPOINTS_TO_ALARM'])
EVALUATION_PERIODS = int(environ['EVALUATION_PERIODS'])
INSUFFICIENT_DATA_ACTIONS = [ x.strip() for x in environ.get('INSUFFICIENT_DATA_ACTIONS', '').split(',') if x ]
METRIC_DIMENSIONS = {key: value for (key, value) in [ [ y.strip() for y in x.strip().split(',') if y ] for x in environ.get('METRIC_DIMENSIONS','').split(';') if x ]}
METRIC_NAME = environ['METRIC_NAME']
METRIC_NAMESPACE = environ['METRIC_NAMESPACE']
METRIC_SAMPLE_DAYS = int(environ.get('METRIC_SAMPLE_DAYS', '15'))
METRIC_STAT = environ['METRIC_STAT']
METRIC_UNIT = environ['METRIC_UNIT']
NUM_STANDARD_DEVIATION = int(environ.get('NUM_STANDARD_DEVIATION', '3'))
OK_ACTIONS = [ x.strip() for x in environ.get('OK_ACTIONS', '').split(',') if x ]
PERIOD = int(environ['PERIOD'])
TREAT_MISSING_DATA = environ.get('TREAT_MISSING_DATA', 'missing')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
  start_time, end_time, period = _calculate_period()
  logger.info('Examining  {} to {} at {} second period'.format(start_time.isoformat(), end_time.isoformat(), period))
  for metric in _get_metrics():
    logger.info('Found metric {}, getting metric data'.format(json.dumps(metric, separators=(',',':'))))
    metric_data = _get_metric_data(metric, start_time, end_time, period)
    if metric_data:
      data_mean = mean(metric_data)
      data_pstdev = pstdev(metric_data)
      if not data_pstdev:
        _delete_metric_alarm(metric, 'AlarmHigh')
        _delete_metric_alarm(metric, 'AlarmLow')
      else:
        high_threshold = data_mean + (data_pstdev * NUM_STANDARD_DEVIATION)
        low_threshold = data_mean - (data_pstdev * NUM_STANDARD_DEVIATION)
        logger.info('Mean: {}; Stddev: {}; High: {}; Low: {}'.format(data_mean, data_pstdev, high_threshold, low_threshold))
        if BOUNDS == 'Both':
          _put_metric_alarm(metric, period, 'AlarmHigh', high_threshold)
          _put_metric_alarm(metric, period, 'AlarmLow', max(low_threshold, 0.0))
        elif BOUNDS == 'AlarmHigh':
          _put_metric_alarm(metric, period, 'AlarmHigh', high_threshold)
          _delete_metric_alarm(metric, 'AlarmLow')
        elif BOUNDS == 'AlarmLow':
          _put_metric_alarm(metric, period, 'AlarmLow', max(low_threshold, 0.0))
          _delete_metric_alarm(metric, 'AlarmHigh')
        else:
          raise ValueError('ALARM_BOUNDS {} unrecognized, must be one of AlarmHigh, AlarmLow, or Both'.format(BOUNDS))
  return event


def _create_alarm_name(metric, bound):
  dimensions_string = '/'.join([ x['Value'] for x in sorted(metric.get('Dimensions', []), key=lambda x: x['Name']) ])
  if not ALARM_NAME:
    if dimensions_string:
      name = '{}/{}/{}-{}'.format(metric['Namespace'], metric['MetricName'], dimensions_string, bound)
    else:
      name = '{}/{}-{}'.format(metric['Namespace'], metric['MetricName'], bound)
  else:
    if dimensions_string:
      name = '{}/{}-{}'.format(ALARM_NAME, dimensions_string, bound)
    else:
      name = '{}-{}'.format(ALARM_NAME, bound)
  return name


def _delete_metric_alarm(metric, bound):
  alarm_name = _create_alarm_name(metric, bound)
  logger.info('Deleting alarm {}'.format(alarm_name))
  CLOUDWATCH.delete_alarms(
    AlarmNames=[
      alarm_name
    ]
  )


def _put_metric_alarm(metric, period, bound, threshhold):
  alarm_name = _create_alarm_name(metric, bound)
  logger.info('Putting alarm {}'.format(alarm_name))
  response = CLOUDWATCH.put_metric_alarm(
    AlarmName=alarm_name,
    AlarmDescription='{} {} Standard Deviations metric for {}/{}, dimensions {}'.format(
      bound, 
      NUM_STANDARD_DEVIATION, 
      metric['Namespace'], 
      metric['MetricName'], 
      json.dumps(metric.get('Dimensions',[]), separators=(',', ':'))
    ),
    OKActions=OK_ACTIONS,
    AlarmActions=ALARM_ACTIONS,
    InsufficientDataActions=INSUFFICIENT_DATA_ACTIONS,
    MetricName=metric['MetricName'],
    Namespace=metric['Namespace'],
    Statistic=METRIC_STAT,
    Dimensions=metric.get('Dimensions', []),
    Period=period,
    Unit=METRIC_UNIT,
    EvaluationPeriods=EVALUATION_PERIODS,
    DatapointsToAlarm=DATAPOINTS_TO_ALARM,
    Threshold=threshhold,
    ComparisonOperator='GreaterThanThreshold' if bound == 'AlarmHigh' else 'LessThanThreshold' if threshhold > 0.0 else 'LessThanOrEqualToThreshold',
    TreatMissingData=TREAT_MISSING_DATA
  )


def _calculate_period():
  end_time = datetime.utcnow().replace(second=0,microsecond=0)
  if METRIC_SAMPLE_DAYS <= 15:
    period = max(PERIOD, 60)
  elif METRIC_SAMPLE_DAYS <= 63:
    period = max(PERIOD, 300)
    end_time = end_time.replace(minute=end_time.minute-end_time.minute%5)
  elif METRIC_SAMPLE_DAYS <= 455:
    period = max(PERIOD, 3600)
    end_time.replace(minute=0)
  else:
    raise ValueError('METRIC_SAMPLE_DAYS cannot be greater than 455')
  return end_time - timedelta(days=METRIC_SAMPLE_DAYS), end_time, period


def _get_metrics():
  metrics = _list_metrics()
  return metrics \
    if not len(METRIC_DIMENSIONS) \
      else [ metric for metric in metrics if _do_dimensions_match(metric.get('Dimensions', [])) ]


def _do_dimensions_match(dimensions):
  if sorted([ x['Name'] for x in dimensions ]) != sorted(METRIC_DIMENSIONS.keys()):
    return False
  for dimension in dimensions:
    if not re.match(METRIC_DIMENSIONS[dimension['Name']], dimension['Value']):
      return False
  return True


def _list_metrics(next_token=None):
  if next_token:
    response = CLOUDWATCH.list_metrics(
      Namespace=METRIC_NAMESPACE,
      MetricName=METRIC_NAME,
      NextToken=next_token
    )
  else:
    response = CLOUDWATCH.list_metrics(
      Namespace=METRIC_NAMESPACE,
      MetricName=METRIC_NAME
    )
  metrics = []
  if 'Metrics' in response:
    metrics = response['Metrics']
  return metrics \
    if 'NextToken' not in response \
      else metrics.extend(_list_metrics(next_token=response['NextToken']))


def _get_metric_data(metric, start_time, end_time, period, next_token=None):
  if next_token:
    response = CLOUDWATCH.get_metric_data(
      MetricDataQueries=[
        {
          'Id': 'data',
          'MetricStat': {
              'Metric': metric,
              'Period': period,
              'Stat': METRIC_STAT,
              'Unit': METRIC_UNIT
          },
          'ReturnData': True
        },
      ],
      StartTime=start_time,
      EndTime=end_time,
      NextToken=next_token,
      ScanBy='TimestampAscending'
    )
  else:
    response = CLOUDWATCH.get_metric_data(
      MetricDataQueries=[
        {
          'Id': 'data',
          'MetricStat': {
              'Metric': metric,
              'Period': period,
              'Stat': METRIC_STAT,
              'Unit': METRIC_UNIT
          },
          'ReturnData': True
        },
      ],
      StartTime=start_time,
      EndTime=end_time,
      ScanBy='TimestampAscending'
    )
  metric_data = []
  if 'Values' in response['MetricDataResults'][0]:
    metric_data = response['MetricDataResults'][0]['Values']
  return metric_data \
    if 'NextToken' not in response \
      else metric_data.extend(_get_metric_data(metric, start_time, end_time, period, response['NextToken']))

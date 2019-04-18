import boto3
import logging.config
import random
import re
import string

from os import environ


CLOUDWATCH = boto3.client('cloudwatch')
METRIC_NAMESPACE = environ['METRIC_NAMESPACE']
METRIC_NAME = environ['METRIC_NAME']
METRIC_REGEX_DIMENSIONS = [x.split(',') for x in environ.get('METRIC_REGEX_DIMENSIONS','').split(';') if x]
METRIC_STAT = environ['METRIC_STAT']
METRIC_UNIT = environ['METRIC_UNIT']
ID_CHARS = string.lowercase+string.digits

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
  metrics = _get_metrics()
  return event

def _get_metrics():
  metrics = _list_metrics()
  if not len(METRIC_REGEX_DIMENSIONS):
    return metrics
  filtered_metrics = []
  for metric in metrics:
    if _do_dimensions_match(metric['Dimensions']):
      filtered_metrics.append(metric)

def _do_dimensions_match(dimensions):
  for dimension in dimensions:
    for regex_dimension in METRIC_REGEX_DIMENSIONS:
      if not re.match(regex_dimension[0], dimension['Name']) \
        or not re.match(regex_dimension[1], dimension['Value']):
        return False
  return True

def _list_metrics(next_token=None):
  response = CLOUDWATCH.list_metrics(
    Namespace=METRIC_NAMESPACE,
    MetricName=METRIC_NAME,
    NextToken=next_token
  )
  metrics = []
  if 'Metrics' in response:
    metrics = response['Metrics']
  return metrics \
    if 'NextToken' not in response \
      else metrics.extend(_list_metrics(next_token=response['NextToken']))

def _get_metric_data(metric, next_token=None):
  response = CLOUDWATCH.get_metric_data(
    MetricDataQueries=[
        {
            'Id': ''.join(random.sample(ID_CHARS,10)),
            'MetricStat': {
                'Metric': metric,
                'Period': 60,
                'Stat': METRIC_STAT,
                'Unit': METRIC_UNIT
            },
            'ReturnData': True
        },
    ],
    StartTime=datetime(2015, 1, 1),
    EndTime=datetime(2015, 1, 1),
    NextToken=next_token,
    ScanBy='TimestampAscending'
  )
  value = response['MetricDataResults']['Values']
  return values \
    if 'NextToken' not in response \
      else values.extend(_get_metric_data(metric, next_token=response['NextToken']))
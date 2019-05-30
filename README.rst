===============================
cloudwatch-stddev-alarm-creator
===============================

.. _APL2: http://www.apache.org/licenses/LICENSE-2.0.txt
.. _Evaluating an Alarm: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html#alarm-evaluation

Retrieves metrics from Cloudwatch, calculates standard deviation, and sets
upper and/or lower alarms based on same. Cloudwatch will only calculate
a Standard Deviation based alarm using the values within the period
measured. This function allows you to calculate the Standard Deviation
across a much longer period (e.g. - 12 months) and use that value from
thresholding a Cloudwatch alarm.

This Lambda function is designed to be invoked by a Cloudwatch Scheduled
Event, but it may be invoked by any Lambda trigger. It ignores the incoming
event.

Required Permissions
--------------------
- cloudwatch:DeleteAlarms
- cloudwatch:GetMetricData
- cloudwatch:ListMetrics
- cloudwatch:PutMetricAlarm

All permissions require ``*`` as the resource.

Environment Variables
---------------------
**ALARM_ACTIONS** (Optional)

  The actions to execute when this alarm transitions to the *ALARM* state from
  any other state. Each action is specified as an Amazon Resource Name (ARN),
  seperated by commas.

**BOUNDS** (Optional)

  The type of alarm threshold(s) to set. Either ``AlarmHigh``, ``AlarmLow`` or
  ``Both``. Defaults to ``Both``.

**DATAPOINTS_TO_ALARM** (Required)

  The number of datapoints that must be breaching to trigger the alarm. This is
  used only if you are setting an "M out of N" alarm. In that case, this value
  is the M. For more information, see `Evaluating an Alarm`_ in the Amazon
  CloudWatch User Guide.

**EVALUATION_PERIODS** (Required)

  The number of periods over which data is compared to the specified threshold.
  If you are setting an alarm that requires that a number of consecutive data
  points be breaching to trigger the alarm, this value specifies that number.

  If you are setting an "M out of N" alarm, this value is the N.
  An alarm's total current evaluation period can be no longer than one day, so
  this number multiplied by ``PERIOD`` cannot be more than 86,400 seconds.

**INSUFFICIENT_DATA_ACTIONS** (Optional)

  The actions to execute when this alarm transitions to the *INSUFFICIENT_DATA*
  state from any other state. Each action is specified as an Amazon Resource
  Name (ARN), seperated by commas.

**METRIC_DIMENSIONS** (Optional)

  The dimensions for the metric specified in ``METRIC_NAME``. This is a list of
  dimension name and value pairs (seperated by commas) that are seperated by
  semicolons. The dimension values may be regular expressions. If not present,
  all metrics that match ``METRIC_NAMESPACE`` and ``METRIC_NAME`` will have
  alarms created for them.

  For example: name1,foo.*;name2,bar[1-9]*

**METRIC_NAME** (Required)

  The name for the metric associated with the alarm.

**METRIC_NAMESPACE** (Required)

  The namespace for the metric associated with the alarm.

**METRIC_SAMPLE_DAYS** (Optional)

  The number of days to use to calculate the mean and population standard
  deviation from. Must be less than ``455``. Defaults to ``15``.

**METRIC_STAT** (Required)

  The statistic to use for the metric. It can include any CloudWatch statistic.

**METRIC_UNIT** (Required)

  The unit to use for the metric data points.

**NUM_STANDARD_DEVIATION** (Optional)

  The number of standard deviations used to caluculate high/low thresholds.
  Default is ``3``.

**OK_ACTIONS** (Optional)

  The actions to execute when this alarm transitions to an *OK* state from any
  other state. Each action is specified as an Amazon Resource Name (ARN)
  , seperated by commas.

**PERIOD** (Required)

  The length, in seconds, used each time the metric specified in
  ``METRIC_NAME`` is evaluated. Valid values are 10, 30, and any multiple of
  60.

  An alarm's total current evaluation period can be no longer than one day,
  so this multiplied by ``EVALUATION_PERIODS`` cannot be more than 86,400
  seconds.

  The actual period used may be changed by ``MAX_SAMPLE_DAYS`` as CloudWatch
  places certain requirements of period length when retrieving metric data.

License: `APL2`_

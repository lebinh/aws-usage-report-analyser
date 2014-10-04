# !/usr/bin/env python

"""usage_report

Usage:
    usage_report [options] [--exclude=<resource>]... <reports.csv> ...

Options:
    -a, --stacked  Draw a stacked line / bar chart
    -b, --bar-chart  Draw bar chart instead of the default Line chart
    -d, --daily  Force daily report even if hourly data are available
    -t <usage type>, --usage-type=<usage type>  UsageType in report to visualise [default: APS1-DataTransfer-Out-Bytes]
    -l <limit>, --limit=<limit>  Limit the number of resource included  [default: 10]
    -s <start time>, --start-time=<start time>  Fixed first day of the report (yy-mm-dd)
    -e <end time>, --end-time=<end time>  Fixed last day of the report (yy-mm-dd)
    -x <resource>, --exclude=<resource>  Exclude this resource from report
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import chain
import sys

from docopt import docopt
import pygal
import pygal.config
import pygal.util
from pygal.style import SolidColorStyle


__author__ = 'binhle'


def read_report(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def parse_record_time(record):
    return datetime.strptime(record[' StartTime'], '%m/%d/%y %H:%M:%S')


def filter_report(report, args):
    """ Filter for only interested records of given type and time frame """
    report = (record for record in report if record[' UsageType'] == args['--usage-type'])
    report = (record for record in report if record[' Resource'] not in args['--exclude'])
    report = ((parse_record_time(record), record) for record in report)
    if args['--start-time'] is not None:
        report = ((time, record) for time, record in report if time > args['--start-time'])
    if args['--end-time'] is not None:
        report = ((time, record) for time, record in report if time < args['--end-time'])
    return report


def group_usage(report, force_daily=False, value_type=int):
    """ Group usage value by resource and time """
    usage = defaultdict(lambda: defaultdict(value_type))  # map: { resource -> { time -> usage } }
    for time, record in report:
        if force_daily:
            time = time.date()
        usage[record[' Resource']][time] += value_type(record[' UsageValue'])
    return usage


def get_time_range(start_time, end_time, usage_data, force_daily=False):
    times = set(chain.from_iterable(usage_data.values()))
    start_time = min(times) if start_time is None else start_time
    end_time = max(times) if end_time is None else end_time

    if is_hourly(times) and not force_daily:
        delta = timedelta(0, 3600)
    else:
        delta = timedelta(1)

    while start_time < end_time:
        yield start_time
        start_time += delta


def is_hourly(time_range):
    for time in time_range:
        if isinstance(time, datetime) and time.hour != 0:
            return True
    return False


def init_chart(args):
    config = pygal.config.Config()
    config.human_readable = True
    config.legend_at_bottom = True
    config.style = SolidColorStyle
    config.legend_font_size = 9
    config.x_labels_major_count = 5
    config.x_label_rotation = 0
    config.truncate_label = 100
    config.show_minor_x_labels = False
    config.dots_size = 2
    if args['--bar-chart']:
        if args['--stacked']:
            return pygal.StackedBar(config=config)
        else:
            return pygal.Bar(config=config)
    else:
        if args['--stacked']:
            config.fill = True
            return pygal.StackedLine(config=config)
        else:
            return pygal.Line(config=config)


def build_usage_chart(usage_data, args):
    time_range = list(get_time_range(args['--start-time'], args['--end-time'], usage_data, args['--daily']))

    total = 0
    # sum total usage for each resource, used to sort and limit resources to be showed
    for resource, usage in usage_data.items():
        usage['sum'] = sum(usage.values())
        total += usage['sum']
    resources = sorted(usage_data.keys(), key=lambda r: usage_data[r]['sum'], reverse=True)
    if args['--limit'] > 0:
        resources = resources[:args['--limit']]

    chart = init_chart(args)
    if is_hourly(time_range):
        label_format = '%Y-%m-%d %H:%M'
    else:
        label_format = '%Y-%m-%d'
    chart.config.x_labels = [time.strftime(label_format) for time in time_range]
    chart.config.title = '%s from %s to %s [total: %s]' % (
        args['--usage-type'], chart.config.x_labels[0], chart.config.x_labels[-1], pygal.util.humanize(total))

    for resource in resources:
        values = [
            {
                'value': usage_data[resource].get(time, 0),
                'label': '%s %s' % (resource, time)
            } for time in time_range]
        title = '%s [%s]' % (resource, pygal.util.humanize(sum(v['value'] for v in values)))
        chart.add(title, values)

    return chart


def main():
    args = docopt(__doc__)
    args['--limit'] = int(args['--limit'])
    if args['--start-time'] is not None:
        args['--start-time'] = datetime.strptime(args['--start-time'], '%y-%m-%d')
    if args['--end-time'] is not None:
        args['--end-time'] = datetime.strptime(args['--end-time'], '%y-%m-%d')

    reports = (read_report(path) for path in args['<reports.csv>'])
    report = chain.from_iterable(reports)
    report = filter_report(report, args)
    usage = group_usage(report, force_daily=args['--daily'])
    if not usage:
        print('No data in specified period.')
        sys.exit(1)
    chart = build_usage_chart(usage, args)
    chart.render_in_browser()


if __name__ == '__main__':
    main()

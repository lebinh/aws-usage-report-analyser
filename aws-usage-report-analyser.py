"""usage_report

Usage:
    usage_report [options] [--exclude=<resource>]... <reports.csv> ...

Options:
    -a, --stacked  Draw a stacked line / bar chart
    -b, --bar-chart  Draw bar chart instead of the default Line chart
    -t <usage type>, --usage-type=<usage type>  UsageType in report to visualise [default: APS1-DataTransfer-Out-Bytes]
    -l <limit>, --limit=<limit>  Limit the number of resource included  [default: 10]
    -s <start time>, --start-time=<start time>  Fixed first day of the report (yy-mm-dd)
    -e <end time>, --end-time=<end time>  Fixed last day of the report (yy-mm-dd)
    -x <resource>, --exclude=<resource>  Exclude this resource from report
"""
import csv
import datetime
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


def group_usage_by_resource(report, usage_type, value_type=int):
    """ Group usage value by resource end start time for given usage type """
    result = defaultdict(lambda: defaultdict(value_type))  # map: { resource -> { time -> usage } }
    for record in report:
        if record[' UsageType'] == usage_type and record[' Resource'] not in args['--exclude']:
            time = datetime.datetime.strptime(record[' StartTime'], '%m/%d/%y %H:%M:%S')
            if args['--start-time'] is not None and time < args['--start-time']:
                continue
            if args['--end-time'] is not None and time > args['--end-time']:
                continue
            result[record[' Resource']][time] += value_type(record[' UsageValue'])
    return result


def get_time_range(usage_data):
    start_time = args['--start-time']
    end_time = args['--end-time']
    hourly = False
    if start_time is None or end_time is None:
        for usage in usage_data.values():
            for time in usage:
                if time.hour != 0:
                    hourly = True
                if start_time is None or start_time > time:
                    start_time = time
                if end_time is None or end_time < time:
                    end_time = time

    delta = datetime.timedelta(0, 3600) if hourly else datetime.timedelta(1)
    while start_time < end_time:
        yield start_time
        start_time += delta


def is_hourly(time_range):
    for time in time_range:
        if time.hour != 0:
            return True
    return False


def init_chart():
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


def build_usage_chart(usage_data, usage_type, limit=10):
    time_range = list(get_time_range(usage_data))

    total = 0
    for resource, usage in usage_data.items():
        usage['sum'] = sum(usage.values())
        total += usage['sum']
    resources = sorted(usage_data.keys(), key=lambda r: usage_data[r]['sum'], reverse=True)
    if limit > 0:
        resources = resources[:limit]

    chart = init_chart()
    if is_hourly(time_range):
        label_format = '%Y-%m-%d %H:%M'
    else:
        label_format = '%Y-%m-%d'
    chart.config.x_labels = [time.strftime(label_format) for time in time_range]
    chart.config.title = '%s from %s to %s [total: %s]' % (
        usage_type, chart.config.x_labels[0], chart.config.x_labels[-1], pygal.util.humanize(total))

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
    reports = (read_report(path) for path in args['<reports.csv>'])
    report = chain.from_iterable(reports)
    usage = group_usage_by_resource(report, args['--usage-type'])
    if not usage:
        print('No data in specified period.')
        sys.exit(1)
    chart = build_usage_chart(usage, args['--usage-type'], limit=args['--limit'])
    chart.render_in_browser()


if __name__ == '__main__':
    args = docopt(__doc__)
    if args['--start-time'] is not None:
        args['--start-time'] = datetime.datetime.strptime(args['--start-time'], '%y-%m-%d')
    if args['--end-time'] is not None:
        args['--end-time'] = datetime.datetime.strptime(args['--end-time'], '%y-%m-%d')
    args['--limit'] = int(args['--limit'])
    main()

aws-usage-report-analyser
=====

Analyse and visualise your AWS usage reports.

Running `aws-usage-report-analyser` with default settings will create a graph for data transfer out to internet, grouped by resource type (bucket in case of S3) and limited to top 10 resources.

```
python aws-usage-report-analyser.py report.csv
```

![Data Transfer By Bucket Graph](/../screenshots/screenshots/data-transfer-report.jpg)

You can change the usage type to be graphed with `--usage-type` option and the number of displayed resource with `--limit` option. For example, this command creates graph of numbers of GET requests to top 3 buckets.

```
python aws-usage-report-analyser.py --usage-type APS1-Requests-Tier2 --limit 3 report1.csv report2.csv
```

![GET Requests By Bucket Graph](/../screenshots/screenshots/requests-report.jpg)

---
layout: default
title: Data formats
nav_order: 5
---

# Data formats
{: .no_toc }

Measurement data can be recorded to disk in various data formats.
{: .fs-6 .fw-300 }

See *Edit* &rarr; *Preferences* &rarr; *Options* to select the data formats to be
written for all measurement.

## Table of contents
{: .no_toc .text-delta }

* TOC
{:toc}

---

## JSON

The JSON format consists of a meta data dictionary, a series unit definition and
a data series dictionary.

## Synopsis

```
{
  "meta": {
    <key>: <value>,
    ...
  },
  "series_units": {
    <series>: <unit>,
    ...
  },
  "series": {
    <series>: [<values...>],
    ...
  },
  "analysis": {
    <key>: <value>,
    ...
  }
}
```

### Example

```json
{
  "meta": {
    "uuid": "7f21460d-cec0-4ef8-b927-0cf7708c5469",
    "sample_name": "HPK_VPX112233_042_PSS",
    "sample_type": "PQCFlutesLeft",
    "sample_position": "Pos1",
    "sample_comment": "Nobody expects the Spanish Inquisition!",
    "contact_name": "PQC Flute 1",
    "measurement_name": "Diode IV",
    "measurement_type": "iv_ramp",
    "measurement_tags": ["spam", "cheese"],
    "table_position": [0, 0, 0],
    "start_timestamp": "2021-11-11T10:32:14",
    "operator": "Monty",
    "pqc_version": "0.41.1",
    "analysis_pqc_version": "0.3.1",
    ...
  },
  "series_units": {
    "timestamp": "s",
    "voltage": "V",
    "current": "A"
  },
  "series": {
    "timestamp": [
      0.03315091133117676,
      0.6038780212402344,
      1.2724788188934326,
      ...
    ],
    "voltage": [
      0.0,
      -10.0,
      -20.0,
      ...
    ],
    "current": [
      0.0003741383,
      0.0004212192,
      0.0008708322,
      ...
    ]
  },
  "analysis": {}
}
```

## Plain Text

The used plain text format consists of a header containing meta data in key and
value pairs, a data table header and a data table. Table header and body uses
`\t` separators.

**Note:** analysis results are not written to plain text format.

## Synopsis

```
<key>: <value>
...
<<series>[<unit>]\t...>
<values...>
...
```

### Example

```
uuid: 7f21460d-cec0-4ef8-b927-0cf7708c5469
sample_name: HPK_VPX112233_042_PSS
sample_type: PQCFlutesLeft
sample_position: Pos1
sample_comment: Nobody expects the Spanish Inquisition!
contact_name: PQC Flute 1
measurement_name: Diode IV
measurement_type: iv_ramp
measurement_tags: spam, cheese
table_position: (0, 0, 0)
start_timestamp: 2021-11-11T10:32:14
operator: Monty
pqc_version: 0.41.1
analysis_pqc_version: 0.3.1
...
timestamp[s]	voltage[V]	current[A]
3.315091E-02	0.000000E+00	3.741383E-04
6.038780E-01	-1.000000E+01	4.212192E-04
1.272479E+00	-2.000000E+01	8.708322E-04
...         	...          	...
```

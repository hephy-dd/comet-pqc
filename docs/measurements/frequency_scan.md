---
layout: default
title: Frequency Scan
parent: Measurements
nav_order: 30
---

# Frequency Scan

**Note:** available in future releases.
{: .label .label-yellow }

Type: `frequency_scan`

## Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enable`            |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |

## Data columns

None.

## Example configuration

```yaml
- id: fscan_example
  name: Freq. Scan Example
  type: frequency_scan
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: []
```

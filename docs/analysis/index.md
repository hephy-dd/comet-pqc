---
layout: default
title: Analysis Functions
nav_order: 3
has_children: true
---


# Analysis Functions
{: .no_toc }

Evaluation of measurement data using PQC analysis functions.
{: .fs-6 .fw-300 }

Analysis functions used from project [analysis-pqc](https://github.com/hephy-dd/analysis-pqc) (version 0.8.1).

## Example configuration

Example configuration applying analysis function `mos` with custom parameter
`min_r_value` and range limits for `v_fb2` and `t_ox`. If the results are not
within the specified limits the analysis will fail.

```yaml
- name: MOS capacitor (HV Source)
  type: cv_ramp
  parameters:
    analysis_functions:
      - type: mos
        parameters:
          min_r_value: 0.4
        limits:
          v_fb2: {minimum: 1, maximum: 7}
          t_ox: {minimum: 0.2, maximum: 1.5}
```

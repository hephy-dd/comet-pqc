---
layout: default
title: IV Ramp with Bias and ELM
parent: Measurements
nav_order: 14
---

# IV Ramp with Bias and Electrometer

Type: `iv_ramp_bias_elm`

## Parameters

| Parameter                    | Type    | Default | Description |
|------------------------------|---------|---------|-------------|
|`matrix_enable`               |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`             |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_source`              |`str`    |`vsrc`   |Possible values are: `hvsrc`, `vsrc`. |
|`voltage_start`               |`volt`   |`0`      | |
|`voltage_stop`                |`volt`   |`-100 V` | |
|`voltage_step`                |`volt`   |`10 V`   | |
|`waiting_time`                |`second` |`1 s`    |Additional delay between ramp steps (`0 ms` to `3600 s`). |
|`voltage_step_before`         |`volt`   |`voltage_step` ||
|`waiting_time_before`         |`second` |`100 ms` ||
|`voltage_step_after`          |`volt`   |`voltage_step` ||
|`waiting_time_after`          |`second` |`100 ms` ||
|`waiting_time_start`          |`second` |`0 s`    |Additional delay before starting with measurement ramp. |
|`waiting_time_end`            |`second` |`0 s`    |Additional delay after final ramp down. |
|`bias_voltage_source`         |`str`    |`hvsrc`  |Possible values are: `hvsrc`, `vsrc`. |
|`bias_voltage_start`          |`volt`   |`10 V`   | |
|`bias_voltage_stop`           |`volt`   |`-90 V`  | |
|`hvsrc_current_compliance`    |`volt`   |required |HV Source current compliance. |
|`hvsrc_accept_compliance`     |`bool`   |`false`  |Stop measurement gracefully if HV Source compliance tripped. |
|`hvsrc_sense_mode`            |`str`    |`local`  |HV Source sense mode. Possible values are: `local`, `remote`. |
|`hvsrc_route_terminal`        |`str`    |`rear`   |HV Source route terminal. Possible values are: `front`, `rear`. |
|`hvsrc_filter_enable`         |`bool`   |`false`  |Enable HV Source filter. |
|`hvsrc_filter_count`          |`int`    |`10`     |HV Source filter count (`1` to `100`). |
|`hvsrc_filter_type`           |`str`    |`repeat` |Type of applied HV Source filter. Possible values are: `moving`, `repeat`. |
|`hvsrc_source_voltage_autorange_enable` | `bool`   |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range`  |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`vsrc_current_compliance`     |`volt`   |required |V Source current compliance. |
|`vsrc_accept_compliance`      |`bool`   |`false`  |Stop measurement gracefully if V Source compliance tripped. |
|`vsrc_sense_mode`             |`str`    |`local`  |Possible values are: `local`, `remote`.
|`vsrc_filter_enable`          |`bool`   |`false`  | |
|`vsrc_filter_count`           |`int`    |`10`     | |
|`vsrc_filter_type`            |`str`    |`repeat` | Possible values are: `moving`, `repeat`. |
|`vsrc_source_voltage_autorange_enable`  | `bool`  |`true`  |Enable source voltage auto range. |
|`vsrc_source_voltage_range`   |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`elm_filter_enable`           |`bool`   |`false`  |Enable Electrometer filter. |
|`elm_filter_count`            |`int`    |`10`     |Electrometer filter count (`1` to `100`). |
|`elm_filter_type`             |`str`    |`repeat` |Type of applied Electrometer filter. Possible values are: `moving`, `repeat`. |
|`elm_current_range`           |`ampere` |`20 pA`  |Current range for measurements. |
|`elm_current_autorange_enable` |`bool`   |`False`  |Enable current auto range. |
|`elm_current_autorange_minimum` |`ampere`   |`20 pA`  |Lower current limit for auto range. |
|`elm_current_autorange_maximum` |`ampere`    |`20 mA`     |Upper current limit for auto range. |
|`elm_zero_correction`         |`bool`   |`false`  |Perform Electrometer zero correction. |
|`elm_integration_rate`        |`int`    |`50`     |Electrometer integration rate (`50` or `60`). |
|`elm_read_timeout`            |`second` |`60 s`   |Timeout for read operation. |
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `gcd`, `fet`, `contact`, `meander`, `breakdown`. See also [Analysis Functions]({{ site.baseurl }}{% link analysis/index.md %}) page. |

## Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage`                  |`volt`   |Voltage assigned to HV source. |
|`current_elm`              |`ampere` |Current reading of electrometer. |
|`current_vsrc`             |`ampere` |Current reading of V source. |
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`bias_voltage`             |`volt`   |Bias voltage assigned to V source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

## Example configuration

```yaml
- id: iv_bias_example
  name: IV Bias Example
  type: iv_ramp_bias_elm
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: []
      analysis_functions: [iv]
```

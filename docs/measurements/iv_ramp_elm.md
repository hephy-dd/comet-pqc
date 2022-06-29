---
layout: default
title: IV Ramp with ELM
parent: Measurements
nav_order: 11
---

# IV Ramp with Electrometer

IV ramp using HV Source and Electrometer for measurements.

Type: `iv_ramp_elm`

## Parameters

| Parameter                    | Type    | Default | Description |
|------------------------------|---------|---------|-------------|
|`matrix_enable`               |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`             |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_start`               |`volt`   |required |Start voltage for HV Source ramp. (`-1 kV` to `1 kV`). |
|`voltage_stop`                |`volt`   |required |End voltage for HV Source ramp. (`-1 kV` to `1 kV`). |
|`voltage_step`                |`volt`   |required |Step voltage for HV Source ramp (`1 mV` to `100 V`). |
|`waiting_time`                |`second` |`1 s`    |Additional delay between ramp steps (`0 ms` to `3600 s`). |
|`voltage_step_before`         |`volt`   |`voltage_step` ||
|`waiting_time_before`         |`second` |`100 ms` ||
|`voltage_step_after`          |`volt`   |`voltage_step` ||
|`waiting_time_after`          |`second` |`100 ms` ||
|`waiting_time_start`          |`second` |`0 s`    |Additional delay before starting with measurement ramp. |
|`waiting_time_end`            |`second` |`0 s`    |Additional delay after final ramp down. |
|`hvsrc_current_compliance`    |`ampere` |required |HV Source current compliance (`1 nA` to `1 mA`). |
|`hvsrc_accept_compliance`     |`bool`   |`false`  |Stop measurement gracefully if HV Source compliance tripped. |
|`hvsrc_sense_mode`            |`str`    |`local`  |HV Source sense mode. Possible values are: `local`, `remote`. |
|`hvsrc_route_terminal`        |`str`    |`rear`   |HV Source route terminal. Possible values are: `front`, `rear`. |
|`hvsrc_filter_enable`         |`bool`   |`false`  |Enable HV Source filter. |
|`hvsrc_filter_count`          |`int`    |`10`     |HV Source filter count (`1` to `100`). |
|`hvsrc_filter_type`           |`str`    |`repeat` |Type of applied HV Source filter. Possible values are: `moving`, `repeat`. |
|`hvsrc_source_voltage_autorange_enable` | `bool`   |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range`  |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
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
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`current_elm`              |`ampere` |Current reading of electrometer. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

## Example configuration

```yaml
- id: iv_example
  name: IV Example
  type: iv_ramp_elm
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [1A02, 2C11]
      voltage_start: 0 V
      voltage_stop: -1000 V
      voltage_step: 10 V
      waiting_time: 1 s
      hvsrc_current_compliance: 1 uA
      hvsrc_sense_mode: local
      hvsrc_route_terminal: rear
      hvsrc_filter_enable: false
      hvsrc_filter_count: 10
      hvsrc_filter_type: repeat
      elm_filter_enable: false
      elm_filter_count: 10
      elm_filter_type: repeat
      elm_zero_correction: false
      elm_integration_rate: 50
      analysis_functions: [iv]
```

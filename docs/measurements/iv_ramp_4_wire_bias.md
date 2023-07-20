---
layout: default
title: IV Ramp 4-Wire with Bias
parent: Measurements
nav_order: 17
---

# IV Ramp 4-Wire with Bias

IV ramp using V Source for ramp and measurements and HV source to apply a bias voltage.

Type: `iv_ramp_4_wire_bias`

## Parameters

| Parameter                | Type    | Default | Description |
|--------------------------|---------|---------|-------------|
|`matrix_enable`           |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`         |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`current_source`          |`str`    |`vsrc`   |Possible values are: `hvsrc`, `vsrc`. |
|`current_start`           |`ampere` |required |Start current for V Source ramp. (`-250 mA` to `250 mA`). |
|`current_stop`            |`ampere` |required |End current for V Source ramp. (`-250 mA` to `250 mA`). |
|`current_step`            |`ampere` |required |Step current for V Source ramp (`1 nA` to `250 mA`). |
|`waiting_time`            |`second` |`1 s`    |Additional delay between ramp steps (`0 ms` to `3600 s`). |
|`current_step_before`     |`ampere`   |`current_step` ||
|`waiting_time_before`     |`second` |`100 ms` ||
|`current_step_after`      |`ampere`   |`current_step` ||
|`waiting_time_after`      |`second` |`100 ms` ||
|`waiting_time_start`      |`second` |`0 s`    |Additional delay before starting with measurement ramp. |
|`waiting_time_end`        |`second` |`0 s`    |Additional delay after final ramp down. |
|`bias_voltage_source`     |`str`    |`hvsrc`  |Possible values are: `hvsrc`, `vsrc`. |
|`bias_voltage`            |`volt`   |required | |
|`bias_voltage_step`       |`volt`   |`1 V`  | |
|`bias_waiting_time_start` |`second` |`1 s`    |Additional delay after reaching bias voltage. |
|`hvsrc_current_compliance`|`volt`   |required |HV Source current compliance. |
|`hvsrc_accept_compliance` |`bool`   |`false`  |Stop measurement gracefully if HV Source compliance tripped. |
|`hvsrc_sense_mode`        |`str`    |`local`  |HV Source sense mode. Possible values are: `local`, `remote`. |
|`hvsrc_route_terminal`    |`str`    |`rear`   |HV Source route terminal. Possible values are: `front`, `rear`. |
|`hvsrc_filter_enable`     |`bool`   |`false`  |Enable HV Source filter. |
|`hvsrc_filter_count`      |`int`    |`10`     |HV Source filter count (`1` to `100`). |
|`hvsrc_filter_type`       |`str`    |`repeat` |Type of applied HV Source filter. Possible values are: `moving`, `repeat`. |
|`hvsrc_source_voltage_autorange_enable` | `bool`  |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range`  |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`vsrc_current_compliance` |`volt`   |required |V Source current compliance (`1 mV` to `1000 V`). |
|`vsrc_accept_compliance`  |`bool`   |`false`  |Stop measurement gracefully if V Source compliance tripped. |
|`vsrc_sense_mode`         |`str`    |`local`  |V Source sense mode. Possible values are: `local`, `remote`. |
|`vsrc_route_terminal`     |`str`    |`rear`   |V Source route terminal. Possible values are: `front`, `rear`. |
|`vsrc_filter_enable`      |`bool`   |`false`  |Enable V Source filter. |
|`vsrc_filter_count`       |`int`    |`10`     |V Source filter count (`1` to `100`). |
|`vsrc_filter_type`        |`str`    |`repeat` |Type of applied V Source filter. Possible values are: `moving`, `repeat`. |
|`vsrc_source_voltage_autorange_enable` | `bool`  |`true`  |Enable source voltage auto range. |
|`vsrc_source_voltage_range` |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`analysis_functions`      |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `van_der_pauw`, `cross`, `linewidth`, `cbkr`, `contact`, `meander`, `breakdown`. See also [Analysis Functions]({{ site.baseurl }}{% link analysis/index.md %}) page. |

## Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`current`                  |`ampere` |Current assigned to V source. |
|`voltage_vsrc`             |`volt`   |Voltage reading of V source. |
|`bias_voltage`             |`volt`   |Voltage reading of HV source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

## Example configuration

```yaml
- id: 4wire_example
  name: IV 4-Wire Bias Example
  type: iv_ramp_4_wire_bias
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [2D12, 2E09, 2F10, 2G11]
      current_start: -10 uA
      current_stop: 10 uA
      current_step: 500 nA
      waiting_time: 500 ms
      bias_voltage: 10 V
      bias_voltage_step: 1 V
      bias_waiting_time_start: 5 s
      vsrc_voltage_compliance: 20 V
      vsrc_sense_mode: remote
      vsrc_filter_enable: false
      vsrc_filter_count: 10
      vsrc_filter_type: repeat
      analysis_functions: [iv, van_der_pauw]
```

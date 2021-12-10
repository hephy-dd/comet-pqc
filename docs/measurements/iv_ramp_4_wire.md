---
layout: default
title: IV Ramp 4-Wire
parent: Measurements
nav_order: 16
---

# IV Ramp 4-Wire

IV ramp using V Source for ramp and measurements.

Type: `iv_ramp_4_wire`

## Parameters

| Parameter                | Type    | Default | Description |
|--------------------------|---------|---------|-------------|
|`matrix_enable`           |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`         |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
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
|`vsrc_current_compliance` |`volt`   |required |V Source current compliance (`1 mV` to `1000 V`). |
|`vsrc_accept_compliance`  |`bool`   |`false`  |Stop measurement gracefully if V Source compliance tripped. |
|`vsrc_sense_mode`         |`str`    |`local`  |V Source sense mode. Possible values are: `local`, `remote`. |
|`vsrc_route_terminal`     |`str`    |`rear`   |V Source route terminal. Possible values are: `front`, `rear`. |
|`vsrc_filter_enable`      |`bool`   |`false`  |Enable V Source filter. |
|`vsrc_filter_count`       |`int`    |`10`     |V Source filter count (`1` to `100`). |
|`vsrc_filter_type`        |`str`    |`repeat` |Type of applied V Source filter. Possible values are: `moving`, `repeat`. |
|`vsrc_source_voltage_autorange_enable` | `bool`  |`true`  |Enable source voltage auto range. |
|`vsrc_source_voltage_range` |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`analysis_functions`      |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `van_der_pauw`, `cross`, `linewidth`, `cbkr`, `contact`, `meander`, `breakdown`. |

## Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`current`                  |`ampere` |Current assigned to V source. |
|`voltage_vsrc`             |`volt`   |Voltage reading of V source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

## Example configuration

```yaml
- id: 4wire_example
  name: IV 4-Wire Example
  type: iv_ramp_4_wire
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [2D12, 2E09, 2F10, 2G11]
      current_start: -10 uA
      current_stop: 10 uA
      current_step: 500 nA
      waiting_time: 500 ms
      vsrc_voltage_compliance: 20 V
      vsrc_sense_mode: remote
      vsrc_filter_enable: false
      vsrc_filter_count: 10
      vsrc_filter_type: repeat
      analysis_functions: [iv, van_der_pauw]
```

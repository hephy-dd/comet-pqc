---
layout: default
title: CV Ramp (V Source)
parent: Measurements
nav_order: 21
---

# CV Ramp (V Source)

CV ramp using V Source and LCR for CpRp measurements.

Type: `cv_ramp_vsrc`

## Parameters

| Parameter                    | Type    | Default | Description |
|------------------------------|---------|---------|-------------|
|`matrix_enable`               |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`             |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`bias_voltage_start`          |`volt`   |required | |
|`bias_voltage_step`           |`volt`   |required | |
|`bias_voltage_stop`           |`volt`   |required | |
|`waiting_time`                |`second` |`1 s`    |Additional delay between ramp steps (`0 ms` to `3600 s`). |
|`bias_voltage_step_before`    |`volt`   |`bias_voltage_step` ||
|`waiting_time_before`         |`second` |`100 ms` ||
|`bias_voltage_step_after`     |`volt`   |`bias_voltage_step` ||
|`waiting_time_after`          |`second` |`100 ms` ||
|`waiting_time_start`          |`second` |`0 s`    |Additional delay before starting with measurement ramp. |
|`waiting_time_end`            |`second` |`0 s`    |Additional delay after final ramp down. |
|`vsrc_current_compliance`     |`ampere` |`1 uA`   | |
|`vsrc_accept_compliance`      |`bool`   |`false`  |Stop measurement gracefully if V Source compliance tripped. |
|`vsrc_sense_mode`             |`str`    |`local`  |Possible values are: `local`, `remote`.
|`vsrc_filter_enable`          |`bool`   |`false`  | |
|`vsrc_filter_count`           |`int`    |`10`     | |
|`vsrc_filter_type`            |`str`    |`repeat` |Possible values are: `moving`, `repeat`. |
|`vsrc_source_voltage_autorange_enable`  | `bool`  |`true`  |Enable source voltage auto range. |
|`vsrc_source_voltage_range`   |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`lcr_soft_filter`             |`bool`   |`true`   |Apply software STD/mean<0.005 filter. |
|`lcr_frequency`               |`herz`   |`1 kHz`  |Possible range from `1 Hz` to `25 kHz`. |
|`lcr_amplitude`               |`volt`   |`250 mV` | |
|`lcr_integration_time`        |`str`    |`medium` |Possible values are: `short`, `medium`, `long`. |
|`lcr_averaging_rate`          |`int`    |`1`      |Possible range from `1` to `10`. |
|`lcr_auto_level_control`      |`bool`   |`true`   | |
|`lcr_open_correction_mode`    |`str`    |`single` |Possible values are: `single`, `multi`. |
|`lcr_open_correction_channel` |`int`    |`0`      |Possible range from `0` to `127`. |
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `cv`, `mos`, `capacitor`. See also [Analysis Functions]({{ site.baseurl }}{% link analysis/index.md %}) page. |

## Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage_vsrc`             |`volt`   |Voltage assigned to V source. |
|`current_vsrc`             |`ampere` |Current reading of V source. |
|`capacitance`              |`farad`  |First value of Cp reading of LCR. |
|`capacitance2`             |`float`  |Second value of Cp reading of LCR. |
|`resistance`               |`ohm`    |Resistance reading of LCR. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

## Example configuration

```yaml
- id: cv_example
  name: CV Example
  type: cv_ramp_vsrc
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [1A01, 1B02, 2H11, 2G12]
      bias_voltage_start: -5 V
      bias_voltage_stop: 10 V
      bias_voltage_step: 0.1 V
      waiting_time: 100 ms
      vsrc_current_compliance: 100 uA
      vsrc_sense_mode: local
      vsrc_filter_enable: false
      vsrc_filter_count: 10
      vsrc_filter_type: moving
      lcr_soft_filter: true
      lcr_frequency: 10 kHz
      lcr_amplitude: 250 mV
      lcr_integration_time: medium
      lcr_averaging_rate: 1
      lcr_auto_level_control: true
      lcr_open_correction_mode: multi
      lcr_open_correction_channel: 8
      analysis_functions: [cv]
```

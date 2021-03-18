---
layout: default
title: Measurements
nav_order: 2
---

# Measurements
{: .no_toc }

Available measurements for PQC.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

* TOC
{:toc}

---

## IV Ramp

IV ramp using HV Source as source and for taking current measurements.

Type: `iv_ramp`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enable`            |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_start`            |`volt`   |required |Start voltage for HV Source ramp. (`-1 kV` to `1 kV`). |
|`voltage_stop`             |`volt`   |required |End voltage for HV Source ramp. (`-1 kV` to `1 kV`). |
|`voltage_step`             |`volt`   |required |Step voltage for HV Source ramp (`1 mV` to `100 V`). |
|`waiting_time`             |`second` |`1 s`    |Additional delay between ramp steps (`0 ms` to `3600 s`). |
|`voltage_step_before`      |`volt`   |`voltage_step` ||
|`waiting_time_before`      |`second` |`100 ms` ||
|`voltage_step_after`       |`volt`   |`voltage_step` ||
|`waiting_time_after`       |`second` |`100 ms` ||
|`waiting_time_start`       |`second` |`0 s`    |Additional delay before starting with measurement ramp. |
|`waiting_time_end`         |`second` |`0 s`    |Additional delay after final ramp down. |
|`hvsrc_current_compliance` |`ampere` |required |HV Source current compliance (`1 nA` to `1 mA`). |
|`hvsrc_accept_compliance`  |`bool`   |`false`  |Stop measurement gracefully if HV Source compliance tripped. |
|`hvsrc_sense_mode`         |`str`    |`local`  |HV Source sense mode. Possible values are: `local`, `remote`. |
|`hvsrc_route_terminal`     |`str`    |`rear`   |HV Source route terminal. Possible values are: `front`, `rear`. |
|`hvsrc_filter_enable`      |`bool`   |`false`  |Enable HV Source filter. |
|`hvsrc_filter_count`       |`int`    |`10`     |HV Source filter count (`1` to `100`). |
|`hvsrc_filter_type`        |`str`    |`moving` |Type of applied HV Source filter.  Possible values are: `moving`, `repeat`. |
|`hvsrc_source_voltage_autorange_enable` | `bool`   |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range` |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`analysis_functions`       |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `gcd`, `fet`, `contact`, `meander`, `breakdown`. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage`                  |`volt`   |Voltage assigned to HV source. |
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

```yaml
- id: iv_example
  name: IV Example
  type: iv_ramp
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [1A02, 2C11]
      voltage_start: 0 V
      voltage_stop: -1000 V
      voltage_step: 10 V
      waiting_time: 1 s
      current_compliance: 1 uA
      sense_mode: local
      route_terminal: rear
      hvsrc_filter_enable: true
      hvsrc_filter_count: 10
      hvsrc_filter_type: moving
      analysis_functions: [iv]
```

## IV Ramp with Electrometer

IV ramp using HV Source and Electrometer for measurements.

Type: `iv_ramp_elm`

### Parameters

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
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `gcd`, `fet`, `contact`, `meander`, `breakdown`. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage`                  |`volt`   |Voltage assigned to HV source. |
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`current_elm`              |`ampere` |Current reading of electrometer. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

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

## IV Ramp 4-Wire

IV ramp using V Source for ramp and measurements.

Type: `iv_ramp_4_wire`

### Parameters

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

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`current`                  |`ampere` |Current assigned to V source. |
|`voltage_vsrc`             |`volt`   |Voltage reading of V source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

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

## IV Ramp with Bias

Type: `iv_ramp_bias`

### Parameters

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
|`hvsrc_source_voltage_autorange_enable` | `bool`  |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range`  |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`vsrc_current_compliance`     |`volt`   |required |V Source current compliance. |
|`vsrc_accept_compliance`      |`bool`   |`false`  |Stop measurement gracefully if V Source compliance tripped. |
|`vsrc_sense_mode`             |`str`    |`local`  |Possible values are: `local`, `remote`.
|`vsrc_filter_enable`          |`bool`   |`false`  | |
|`vsrc_filter_count`           |`int`    |`10`     | |
|`vsrc_filter_type`            |`str`    |`repeat` |Possible values are: `moving`, `repeat`. |
|`vsrc_source_voltage_autorange_enable`  | `bool`  |`true`  |Enable source voltage auto range. |
|`vsrc_source_voltage_range`  |`volt`    |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `gcd`, `fet`, `contact`, `meander`, `breakdown`. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage`                  |`volt`   |Voltage assigned to HV source. |
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`bias_voltage`             |`volt`   |Bias voltage assigned to V source. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

```yaml
- id: iv_bias_example
  name: IV Bias Example
  type: iv_ramp_bias
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: []
      analysis_functions: [iv]
```

## IV Ramp with Bias and Electrometer

Type: `iv_ramp_bias_elm`

### Parameters

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
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `iv`, `gcd`, `fet`, `contact`, `meander`, `breakdown`. |

### Data columns

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

### Example configuration

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

## CV Ramp (HV Source)

CV ramp using HV Source and LCR for CpRp measurements.

Type: `cv_ramp`

### Parameters

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
|`hvsrc_current_compliance`    |`ampere` |`1 uA`   | |
|`hvsrc_accept_compliance`     |`bool`   |`false`  |Stop measurement gracefully if HV Source compliance tripped. |
|`hvsrc_route_terminal`        |`str`    |`rear`   | |
|`hvsrc_sense_mode`            |`str`    |`local`  | Possible values are: `local`, `remote`.
|`hvsrc_filter_enable`         |`bool`   |`false`  | |
|`hvsrc_filter_count`          |`int`    |`10`     | |
|`hvsrc_filter_type`           |`str`    |`repeat` | Possible values are: `moving`, `repeat`. |
|`hvsrc_source_voltage_autorange_enable` | `bool`   |`true`  |Enable source voltage auto range. |
|`hvsrc_source_voltage_range`  |`volt`   |`20 V`   |Set source voltage range. (`-1 kV` to `1 kV`). |
|`lcr_soft_filter`             |`bool`   |`true`   | Apply software STD/mean<0.005 filter. |
|`lcr_frequency`               |`herz`   |`1 kHz`  | Possible range from `1 Hz` to `25 kHz`. |
|`lcr_amplitude`               |`volt`   |`250 mV` | |
|`lcr_integration_time`        |`str`    |`medium` | Possible values are: `short`, `medium`, `long`. |
|`lcr_averaging_rate`          |`int`    |`1`      | Possible range from `1` to `10`. |
|`lcr_auto_level_control`      |`bool`   |`true`   | |
|`lcr_open_correction_mode`    |`str`    |`single` | Possible values are: `single`, `multi`. |
|`lcr_open_correction_channel` |`int`    |`0`      | Possible range from `0` to `127`. |
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `cv`, `mos`, `capacitor`. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage_hvsrc`            |`volt`   |Voltage assigned to HV source. |
|`current_hvsrc`            |`ampere` |Current reading of HV source. |
|`capacitance`              |`farad`  |First value of Cp reading of LCR. |
|`capacitance2`             |`float`  |Second value of Cp reading of LCR. |
|`resistance`               |`ohm`    |Resistance reading of LCR. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

```yaml
- id: cv_example
  name: CV Example
  type: cv_ramp
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [1A01, 1B02, 2H11, 2G12]
      bias_voltage_start: -5 V
      bias_voltage_stop: 10 V
      bias_voltage_step: 0.1 V
      waiting_time: 100 ms
      hvsrc_current_compliance: 100 uA
      hvsrc_route_terminal: rear
      hvsrc_sense_mode: local
      hvsrc_filter_enable: false
      hvsrc_filter_count: 10
      hvsrc_filter_type: moving
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

## CV Ramp (V Source)

CV ramp using V Source and LCR for CpRp measurements.

Type: `cv_ramp_vsrc`

### Parameters

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
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `cv`, `mos`, `capacitor`. |

### Data columns

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

### Example configuration

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

## CV Ramp (LCR only)

Type: `cv_ramp_alt`

### Parameters

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
|`lcr_soft_filter`             |`bool`   |`true`   |Apply software STD/mean<0.005 filter. |
|`lcr_frequency`               |`herz`   |`1 kHz`  |Possible range from `1 Hz` to `25 kHz`. |
|`lcr_amplitude`               |`volt`   |`250 mV` | |
|`lcr_integration_time`        |`str`    |`medium` |Possible values are: `short`, `medium`, `long`. |
|`lcr_averaging_rate`          |`int`    |`1`      |Possible range from `1` to `10`. |
|`lcr_auto_level_control`      |`bool`   |`true`   | |
|`lcr_open_correction_mode`    |`str`    |`single` |Possible values are: `single`, `multi`. |
|`lcr_open_correction_channel` |`int`    |`0`      |Possible range from `0` to `127`. |
|`analysis_functions`          |`list`   |`[]`     |List of applied analysis functions. Possible values are: `cv`, `mos`, `capacitor`. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|
|`timestamp`                |`second` |Time offset in seconds. |
|`voltage_lcr`              |`volt`   |Voltage assigned to V source. |
|`current_lcr`              |`ampere` |Current reading of V source. |
|`capacitance`              |`farad`  |First value of Cp reading of LCR. |
|`capacitance2`             |`float`  |Second value of Cp reading of LCR. |
|`resistance`               |`ohm`    |Resistance reading of LCR. |
|`temperature_box`          |`degC`   |Box temperature in degree Celcius. |
|`temperature_chuck`        |`degC`   |Chuck temperature in degree Celcius. |
|`humidity_box`             |`percent`|Relative box humidity in percent. |

### Example configuration

```yaml
- id: cv_alt_example
  name: CV Alternate Example
  type: cv_ramp_alt
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: [1A01, 1B02, 2H11, 2G12]
      bias_voltage_start: -5 V
      bias_voltage_stop: 10 V
      bias_voltage_step: 0.1 V
      waiting_time: 100 ms
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

## Frequency Scan

**Note:** available in future releases.

Type: `frequency_scan`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enable`            |`bool`   |`true`   |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |

### Data columns

| Column                    | Type    | Description |
|---------------------------|---------|-------------|

### Example configuration

```yaml
- id: fscan_example
  name: Freq. Scan Example
  type: frequency_scan
  enabled: true
  description: An example measurement.
  parameters:
      matrix_channels: []
```

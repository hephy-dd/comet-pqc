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

IV ramp using VSource as source and for taking current measurements.

Type: `iv_ramp`

### Parameters

| Parameter                | Type    | Default | Description |
|--------------------------|---------|---------|-------------|
|`matrix_enabled`          |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`         |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_start`           |`volt`   |required |Start voltage for VSource ramp. (`-1 kV` to `1 kV`). |
|`voltage_stop`            |`volt`   |required |End voltage for VSource ramp. (`-1 kV` to `1 kV`). |
|`voltage_step`            |`volt`   |required |Step voltage for VSource ramp (`1 mV` to `100 V`). |
|`waiting_time`            |`second` |`1 s`    |Additional waiting time between ramp steps (`100 ms` to `3600 s`). |
|`vsrc_current_compliance` |`ampere` |required |VSource current compliance (`1 nA` to `1 mA`).|
|`vsrc_sense_mode`         |`str`    |`local`  |VSource sense mode. Possible values are: `local`, `remote`. |
|`vsrc_route_termination`  |`str`    |`rear`   |VSource route termination. Possible values are: `front`, `rear`. |
|`vsrc_filter_enable`      |`bool`   |`false`  |Enable VSource filter. |
|`vsrc_filter_count`       |`int`    |`10`     |VSource filter count (`1` to `100`). |
|`vsrc_filter_type`        |`str`    |`moving` |Type of applied VSource filter.  Possible values are: `moving`, `repeat`. |

### Example configuration

```yaml
- name: IV Example
  type: iv_ramp
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: true
      matrix_channels: [1A02, 2C11]
      voltage_start: 0 V
      voltage_stop: -1000 V
      voltage_step: 10 V
      waiting_time: 1 s
      current_compliance: 1 uA
      sense_mode: local
      route_termination: rear
      vsrc_filter_enable: true
      vsrc_filter_count: 10
      vsrc_filter_type: moving
```

## IV Ramp with Electrometer

IV ramp using VSource and Electrometer for measurements.

Type: `iv_ramp_elm`

### Parameters

| Parameter                | Type    | Default | Description |
|--------------------------|---------|---------|-------------|
|`matrix_enabled`          |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`         |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_start`           |`volt`   |required |Start voltage for VSource ramp. (`-1 kV` to `1 kV`). |
|`voltage_stop`            |`volt`   |required |End voltage for VSource ramp. (`-1 kV` to `1 kV`). |
|`voltage_step`            |`volt`   |required |Step voltage for VSource ramp (`1 mV` to `100 V`). |
|`waiting_time`            |`second` |`1 s`    |Additional waiting time between ramp steps (`100 ms` to `3600 s`). |
|`vsrc_current_compliance` |`ampere` |required |VSource current compliance (`1 nA` to `1 mA`). |
|`vsrc_sense_mode`         |`str`    |`local`  |VSource sense mode. Possible values are: `local`, `remote`. |
|`vsrc_route_termination`  |`str`    |`rear`   |VSource route termination. Possible values are: `front`, `rear`. |
|`vsrc_filter_enable`      |`bool`   |`false`  |Enable VSource filter. |
|`vsrc_filter_count`       |`int`    |`10`     |VSource filter count (`1` to `100`). |
|`vsrc_filter_type`        |`str`    |`repeat` |Type of applied VSource filter. Possible values are: `moving`, `repeat`. |
|`elm_filter_enable`       |`bool`   |`false`  |Enable Electrometer filter. |
|`elm_filter_count`        |`int`    |`10`     |Electrometer filter count (`1` to `100`). |
|`elm_filter_type`         |`str`    |`repeat` |Type of applied Electrometer filter. Possible values are: `moving`, `repeat`. |
|`elm_current_range`       |`ampere` |`20 pA`  |Current range for measurements. |
|`elm_current_autorange_enable` |`bool`   |`True`  |Enable current auto range. |
|`elm_current_autorange_minimum` |`ampere`   |`20 pA`  |Lower current limit for auto range. |
|`elm_current_autorange_maximum` |`ampere`    |`20 mA`     |Upper current limit for auto range. |
|`elm_zero_correction`     |`bool`   |`false`  |Perform Electrometer zero correction. |
|`elm_integration_rate`    |`int`    |`50`     |Electrometer integration rate (`50` or `60`). |

### Example configuration

```yaml
- name: IV Example
  type: iv_ramp_elm
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: true
      matrix_channels: [1A02, 2C11]
      voltage_start: 0 V
      voltage_stop: -1000 V
      voltage_step: 10 V
      waiting_time: 1 s
      vsrc_current_compliance: 1 uA
      vsrc_sense_mode: local
      vsrc_route_termination: rear
      vsrc_filter_enable: false
      vsrc_filter_count: 10
      vsrc_filter_type: repeat
      elm_filter_enable: false
      elm_filter_count: 10
      elm_filter_type: repeat
      elm_zero_correction: false
      elm_integration_rate: 50
```

## IV Ramp 4-Wire

IV ramp using HVSource for ramp and measurements.

Type: `iv_ramp_4_wire`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`current_start`            |`ampere` |required |Start current for HVSource ramp. (`-250 mA` to `250 mA`). |
|`current_stop`             |`ampere` |required |End current for HVSource ramp. (`-250 mA` to `250 mA`). |
|`current_step`             |`ampere` |required |Step current for HVSource ramp (`1 nA` to `250 mA`). |
|`waiting_time`             |`second` |`1 s`    |Additional waiting time between ramp steps (`100 ms` to `3600 s`). |
|`hvsrc_current_compliance` |`volt`   |required |HVSource current compliance (`1 mV` to `1000 V`). |
|`hvsrc_sense_mode`         |`str`    |`local`  |HVSource sense mode. Possible values are: `local`, `remote`. |
|`hvsrc_route_termination`  |`str`    |`rear`   |HVSource route termination. Possible values are: `front`, `rear`. |
|`hvsrc_filter_enable`      |`bool`   |`false`  |Enable HVSource filter. |
|`hvsrc_filter_count`       |`int`    |`10`     |HVSource filter count (`1` to `100`). |
|`hvsrc_filter_type`        |`str`    |`repeat` |Type of applied HVSource filter. Possible values are: `moving`, `repeat`. |

### Example configuration

```yaml
- name: IV 4-Wire Example
  type: iv_ramp_4_wire
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: true
      matrix_channels: [2D12, 2E09, 2F10, 2G11]
      current_start: -10 uA
      current_stop: 10 uA
      current_step: 500 nA
      waiting_time: 500 ms
      hvsrc_voltage_compliance: 20 V
      hvsrc_sense_mode: remote
      hvsrc_filter_enable: false
      hvsrc_filter_count: 10
      hvsrc_filter_type: repeat
```

## IV Ramp with Bias

Type: `iv_ramp_bias`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_source`           |`str`    |`hvsrc`  |Possible values are: `vsrc`, `hvsrc`. |
|`voltage_start`            |`volt`   |`0`      | |
|`voltage_stop`             |`volt`   |`-100 V` | |
|`voltage_step`             |`volt`   |`10 V`   | |
|`bias_voltage_source`      |`str`    |`vsrc`   |Possible values are: `vsrc`, `hvsrc`. |
|`bias_voltage_start`       |`volt`   |`10 V`   | |
|`bias_voltage_stop`        |`volt`   |`-90 V`  | |
|`vsrc_current_compliance`  |`volt`   |required |VSource current compliance. |
|`hvsrc_current_compliance` |`volt`   |required |HVSource current compliance. |

### Example configuration

```yaml
- name: IV Bias Example
  type: iv_ramp_bias
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: false
      matrix_channels: []
```

## IV Ramp with Bias and Electrometer

Type: `iv_ramp_bias_elm`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_source`           |`str`    |`hvsrc`  |Possible values are: `vsrc`, `hvsrc`. |
|`voltage_start`            |`volt`   |`0`      | |
|`voltage_stop`             |`volt`   |`-100 V` | |
|`voltage_step`             |`volt`   |`10 V`   | |
|`bias_voltage_source`      |`str`    |`vsrc`   |Possible values are: `vsrc`, `hvsrc`. |
|`bias_voltage_start`       |`volt`   |`10 V`   | |
|`bias_voltage_stop`        |`volt`   |`-90 V`  | |
|`vsrc_current_compliance`  |`volt`   |required |VSource current compliance. |
|`hvsrc_current_compliance` |`volt`   |required |HVSource current compliance. |
|`elm_filter_enable`        |`bool`   |`false`  |Enable Electrometer filter. |
|`elm_filter_count`         |`int`    |`10`     |Electrometer filter count (`1` to `100`). |
|`elm_filter_type`          |`str`    |`repeat` |Type of applied Electrometer filter. Possible values are: `moving`, `repeat`. |
|`elm_current_range`        |`ampere` |`20 pA`  |Current range for measurements. |
|`elm_current_autorange_enable` |`bool`   |`True`  |Enable current auto range. |
|`elm_current_autorange_minimum` |`ampere`   |`20 pA`  |Lower current limit for auto range. |
|`elm_current_autorange_maximum` |`ampere`    |`20 mA`     |Upper current limit for auto range. |
|`elm_zero_correction`     |`bool`   |`false`  |Perform Electrometer zero correction. |
|`elm_integration_rate`    |`int`    |`50`     |Electrometer integration rate (`50` or `60`). |

### Example configuration

```yaml
- name: IV Bias Example
  type: iv_ramp_bias_elm
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: false
      matrix_channels: []
```

## CV Ramp (VSource)

CV ramp using VSource and LCR for CpRp measurements.

Type: `cv_ramp`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`bias_voltage_start`       |`volt`   |required | |
|`bias_voltage_step`        |`volt`   |required | |
|`bias_voltage_stop`        |`volt`   |required | |
|`waiting_time`             |`second` |`1 s`    | |
|`vsrc_current_compliance`  |`ampere` |`1 uA`   | |
|`vsrc_route_termination`   |`str`    |`rear`   | |
|`vsrc_sense_mode`          |`str`    |`local`  | Possible values are: `local`, `remote`.
|`vsrc_filter_enable`       |`bool`   |`false`  | |
|`vsrc_filter_count`        |`int`    |`10`     | |
|`vsrc_filter_type`         |`str`    |`repeat` | Possible values are: `moving`, `repeat`. |
|`lcr_soft_filter`          |`bool`   |`true`   | Apply software STD/mean<0.005 filter. |
|`lcr_frequency`            |`herz`   |`1 kHz`  | Possible range from `1 Hz` to `25 kHz`. |
|`lcr_amplitude`            |`volt`   |`250 mV` | |
|`lcr_integration_time`     |`str`    |`medium` | Possible values are: `short`, `medium`, `long`. |
|`lcr_averaging_rate`       |`int`    |`1`      | Possible range from `1` to `10`. |
|`lcr_auto_level_control`   |`bool`   |`true`   | |

### Example configuration

```yaml
- name: CV Example
  type: cv_ramp
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: true
      matrix_channels: [1A01, 1B02, 2H11, 2G12]
      bias_voltage_start: -5 V
      bias_voltage_stop: 10 V
      bias_voltage_step: 0.1 V
      waiting_time: 100 ms
      vsrc_current_compliance: 100 uA
      vsrc_route_termination: rear
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
```

## CV Ramp (HVSource)

CV ramp using HVSource and LCR for CpRp measurements.

Type: `cv_ramp_hv`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |
|`bias_voltage_start`       |`volt`   |required | |
|`bias_voltage_step`        |`volt`   |required | |
|`bias_voltage_stop`        |`volt`   |required | |
|`waiting_time`             |`second` |`1 s`    | |
|`hvsrc_current_compliance`  |`ampere` |`1 uA`   | |
|`hvsrc_sense_mode`          |`str`    |`local`  | Possible values are: `local`, `remote`.
|`hvsrc_filter_enable`       |`bool`   |`false`  | |
|`hvsrc_filter_count`        |`int`    |`10`     | |
|`hvsrc_filter_type`         |`str`    |`repeat` | Possible values are: `moving`, `repeat`. |
|`lcr_soft_filter`          |`bool`   |`true`   | Apply software STD/mean<0.005 filter. |
|`lcr_frequency`            |`herz`   |`1 kHz`  | Possible range from `1 Hz` to `25 kHz`. |
|`lcr_amplitude`            |`volt`   |`250 mV` | |
|`lcr_integration_time`     |`str`    |`medium` | Possible values are: `short`, `medium`, `long`. |
|`lcr_averaging_rate`       |`int`    |`1`      | Possible range from `1` to `10`. |
|`lcr_auto_level_control`   |`bool`   |`true`   | |

### Example configuration

```yaml
- name: CV Example
  type: cv_ramp_hv
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: true
      matrix_channels: [1A01, 1B02, 2H11, 2G12]
      bias_voltage_start: -5 V
      bias_voltage_stop: 10 V
      bias_voltage_step: 0.1 V
      waiting_time: 100 ms
      hvsrc_current_compliance: 100 uA
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
```

## CV Ramp (LCR only)

Available in future releases.

Type: `cv_ramp_alt`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |

### Example configuration

```yaml
- name: CV Alternate Example
  type: cv_ramp_alt
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: false
      matrix_channels: []
```

## Frequency Scan

Available in future releases.

Type: `frequency_scan`

### Parameters

| Parameter                 | Type    | Default | Description |
|---------------------------|---------|---------|-------------|
|`matrix_enabled`           |`bool`   |`false`  |Enable matrix configuration. |
|`matrix_channels`          |`list`   |`[]`     |List of matrix channels to be closed. All matrix slots can be addressed. |

### Example configuration

```yaml
- name: Freq. Scan Example
  type: frequency_scan
  enabled: true
  description: An example measurement.
  parameters:
      matrix_enabled: false
      matrix_channels: []
```

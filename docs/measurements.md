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

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |
|`voltage_start` |`volt` |`0 V` |Start voltage for ramp. (`-1 kV` to `1 kV`). |
|`voltage_stop` |`volt` |`10 V` |End voltage for ramp. (`-1 kV` to `1 kV`). |
|`voltage_step` |`volt` |`1 V` |Step voltage for ramp (`1 mV` to `100 V`). |
|`waiting_time` |`second` |`1 s` |Additional waiting time between ramp steps (`100 ms` to `3600 s`). |
|`current_compliance` |`ampere` |`1 uA` |VSource current compliance |
|`sense_mode` |`str` |`local` |VSource sense mode |
|`route_termination` |`str` |`rear` |VSource route termination. Possible values are: `front`, `rear`. |
|`vsrc_filter_enable` |`bool` |`false` |Enable VSource filter |
|`vsrc_filter_count` |`int` |`10` |VSource filter count (`1` to `100`). |
|`vsrc_filter_type` |`str` |`moving` |Type of applied VSource filter.  Possible values are: `moving`, `repeat`. |

### Example configuration

```yaml
- name: IV Example
  type: iv_ramp
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

IV ramp using VSource and ELM (Keithley 6517B) for measurements.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |

## IV Ramp 4-Wire

IV ramp using HVSource and ELM (Keithley 6517B) for measurements.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |

## IV Ramp with Bias

Available in future releases.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |

## CV Ramp (VSource and LCR)

CV ramp using VSource and LCR (Keysight E4980A) for CpRp measurements.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |
| `bias_voltage_start` | `volt` |  | |
| `bias_voltage_step` | `volt` |  | |
| `bias_voltage_stop` | `volt` |  | |
| `waiting_time` | `second` | `1 s` | |
| `route_termination` | `str` | `rear` | |
| `sense_mode` | `str` | `local` | Possible values are: `local`, `remote`.
| `current_compliance` | `ampere` | `1 uA` | |
| `vsrc_filter_type` | `str` | `repeat` | Possible values are: `moving`, `repeat`. |
| `vsrc_filter_count` | `int` | `10` | |
| `vsrc_filter_enable` | `bool` | `false` | |
| `lcr_soft_filter` | `bool` | `true` | Apply software STD/mean<0.005 filter. |
| `lcr_frequency` | `herz` | `1 kHz` | Possible range from `1 Hz` to `25 kHz`. |
| `lcr_amplitude` | `volt` | `250 mV`| |
| `lcr_integration_time` | `str` | `medium` | Possible values are: `short`, `medium`, `long`. |
| `lcr_averaging_rate` | `int` | `1` | Possible range from `1` to `10`. |
| `lcr_auto_level_control` | `bool` | `true` | |


## CV Ramp (LCR only)

Available in future releases.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |

## Frequency Scan

Available in future releases.

### Parameters

| Parameter | Type | Default | Description |
|------|------|---------|-------------|
|`matrix_enabled` |`bool` |`false` |enable matrix configuration. |
|`matrix_channels` |`list[str]` |`[]` | List of matrix channels to be closed. All matrix slots can be addressed. |

---
layout: default
title: Configuration
nav_order: 2
---

# Configuration

Measurement sequences, wafer and chuck geometries can be configured using YAML configuration files.
{: .fs-6 .fw-300 }

## Sequences

A sequence configuration must provide properties `id`, `name` and `connections`. Optional properties are `description` and `enabled`.

```yaml
id: my_sequence
name: My Sequence
description: A custom sequence
enabled: true
connections: []
```

### Connections

A sequence consists of a list of connection points on a wafer. Such connections are also referred as _flutes_.

A connection must provide properties `name`, `connection` and `measurements`. Optional properties are `description` and `enabled`.

Property `connection` must reflect a connection ID defined in the selected wafer configuration.

```yaml
...
connections:
  - name: Flute 1
    description: A custom connection
    enabled: true
    connection: flute_1
    measurements: []
```

### Measurements

A connection consists of a list of measurements to be performed with this connection.

A connection must provide properties `name`, `type` and `parameters`. Optional properties are `description` and `enabled`.

Property `type` must reflect a built in measurement ID. Valid types are `iv_ramp`, `iv_ramp_bias`, `iv_ramp_4_wire`, `cv_ramp`, `cv_ramp_alt`, `frequency_scan`.

Property `parameters` defines default values specified by the measurement.

```yaml
...
    measurements:
      - name: Polysilicon Van-der-Pauw cross
        type: 4wire_iv_ramp
        parameters:
            current_start: -10 uA
            current_stop: 10 uA
            current_step: 500 nA
```

### Example

This example defines a sequence consisting of a single connection _PQC Flute 1_ with a single measurement _Diode IV_ at this connection.

```yaml
id: default
name: Default
description: Default measurement sequence.
connections:
  - name: PQC Flute 1
    connection: flute_1
    measurements:
      - name: Diode IV
        description: Performing IV ramp measurements.
        type: iv_ramp
        parameters:
            matrix_channels: []
            voltage_start: 0 V
            voltage_stop: -1000 V
            voltage_step: 10 V
            waiting_time: 1 s
            current_compliance: 1 uA
            sense_mode: local
```

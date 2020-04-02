---
layout: default
title: Configuration
nav_order: 2
---

# Configuration
{: .no_toc }

Measurement sequences, wafer and chuck geometries can be configured using YAML configuration files.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

* TOC
{:toc}

---

## Sequence

A sequence defines a list of measurements to be executed at physical contact points located on a silicon sample. A sequence can be executed manually step-by-step or in a semi-automatic way (using the autopilot).

A sequence configuration must provide properties `id`, `name` and `contacts`. Optional properties are `description` and `enabled`.

```yaml
id: my_sequence
name: My Sequence
description: A custom sequence
enabled: true
contacts: []
```

See [config/sequence/default.yaml](https://github.com/hephy-dd/comet-pqc/blob/master/comet_pqc/config/sequence/default.yaml) for reference.

Custom sequence configuration files can be imported using `File` &rarr; `Sequence` &rarr; `Import...`.

### Contacts

A sequence consists of a list of contact points on a silicon sample. Such contact points are also referred as _flutes_.

A contact must provide properties `name`, `contact_id` and `measurements`. Optional properties are `description` and `enabled`.

Property `contact_id` must reflect a contact ID defined in the selected silicon `sample` configuration.

```yaml
...
contacts:
  - name: Flute 1
    description: A custom contact point
    enabled: true
    contact_id: flute_1
    measurements: []
```

### Measurements

A connection consists of a list of measurements to be performed with this connection.

A connection must provide properties `name`, `type` and `parameters`. Optional properties are `description` and `enabled`.

Property `type` must reflect a built in measurement ID. Valid types are `iv_ramp`, `iv_ramp_bias`, `iv_ramp_4_wire`, `cv_ramp`, `cv_ramp_alt`, `frequency_scan`.

Property `parameters` defines default values specified by an individual measurement.

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

If a parameter value is followed by a unit abbreviation [Pint](https://pint.readthedocs.io/en/latest/) is used to convert the
value into a physical quantity of the specified unit. For example `10 V` will return a `<Quantity(10.0, 'Volt')>` object.

### Example

This example defines a sequence consisting of a single contact _PQC Flute 1_ with a single measurement _Diode IV_ at this location.

```yaml
id: default
name: Default
description: Default measurement sequence.
contacts:
  - name: PQC Flute 1
    contact_id: flute_1  # refs. sample configuration
    enabled: true
    measurements:
      - name: Diode IV
        description: Performing IV ramp measurements.
        enabled: true
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

## Sample

A sample defines available contact points and geometry of a silicon sample (wafer slice with test structures and contact points).

A sample configuration must provide properties `id`, `name` and `contacts`. Optional properties are `description` and `enabled`.

```yaml
id: my_sample
name: My Sample
description: A custom silicon sample
enabled: true
contacts: []
```

See [config/sample/default_hme_n.yaml](https://github.com/hephy-dd/comet-pqc/blob/master/comet_pqc/config/sample/default_hmw_n.yaml) for reference.

### Contacts

A sample consists of a list of contact points located on the silicon sample. A sequence must refer to contact points specified in the sample configuration.

Contact points are also referred as _flutes_.

A contact point must provide properties `id`, `name`, and `pos`. Optional properties are `description` and `enabled`.

```yaml
...
contacts:
  - id: flute_1  # ref. sequence configuration
    name: Flute 1
    pos:
        x: 29
        y: 34
        z: 0
```

## Chuck

A chuck defines the geometry of the available silicon sample positions on the chuck.

A chuck configuration must provide properties `id`, `name`, and `positions`. Optional properties are `description` and `enabled`.

```yaml
id: default
name: Default
description: Default chuck providing four sample positions.
enabled: true
positions: []
```

### Positions

A position defines an area on the chuck surface where a silicon sample can be placed. Usually there are multiple positions an a chuck.

A position must provide properties `id`, `name`, and `pos`. Optional property is `enabled`.

```yaml
...
positions:
  - id: pos_1
    name: Sample 1
    enabled: true
    pos:
        x: 100
        y: 250
        z: 0
```

See [config/chuck/default.yaml](https://github.com/hephy-dd/comet-pqc/blob/master/comet_pqc/config/chuck/default.yaml) for reference.

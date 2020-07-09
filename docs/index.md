---
layout: default
title: Home
nav_order: 1
permalink: /
---

# COMET PQC

Process Quality Control for CMS tracker
{: .fs-6 .fw-300 }

## Getting started

### Required instruments:

- Keithley 707B Switching Matrix
- Keysight E4980A LCR Meter
- Keithley 6517B Electrometer
- Keithley 2410 Source Meter (HV Source)
- Keithley 2657A Source Meter (V Source)
- Corvus TT positioning controller
- HEPHY Environment Box

### Install

Install from GitHub using pip

```bash
pip install git+https://github.com/hephy-dd/comet-pqc.git@0.15.1
```

### Setup

When running for the first time make sure to configure the VISA resource settings according to the individual setup by using `Edit` &rarr; `Preferences`.

### Safety

**Note:** this software controls a highly complex, high voltage measurement setup in a laboratory environment. Always take care and double check the situation before taking actual measurements.

### Usage

Measurements can be executed individual by selecting a measurement from the sequence tree and clicking `Run` inside the measurement panel. An active measurement can be stopped using the `Stop` button.

To execute a sequence of measurements click `Start` in the control panel blow the current sequence tree. Check option `Autopilot` to automatically execute all checked measurements in the sequence.

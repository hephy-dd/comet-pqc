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

### Required instruments

|Instrument                       |Role |
|:--------------------------------|:----|
|Keithley 707B Switching Matrix   |Matrix |
|Keysight E4980A LCR Meter        |LCR Meter |
|Keithley 6517B Electrometer      |ELM |
|Keithley 2410 Source Meter       |HV Source, V Source |
|Keithley 2657A Source Meter      |V Source, HV Source |
|Corvus TT positioning controller |Table |
|HEPHY Environment Box            |Environment |

### Setup schematic

![PQC setup schematic](assets/MatrixCardsDesign_v10_Diss2.png)

### Install

Install from GitHub using pip

```bash
pip install git+https://github.com/hephy-dd/comet-pqc.git@0.32.1
```

### Setup

When running for the first time make sure to configure the VISA resource settings according to the individual setup by using `Edit` &rarr; `Preferences`.

Select the correct SMU instrument models (K2410, K2657A) for V source and HV source in the preferences.

### Safety

**Note:** this software controls a highly complex, high voltage measurement setup in a laboratory environment. Always take care and double check the situation before taking actual measurements.

### Usage

Measurements can be executed individual by selecting a measurement from the sequence tree and clicking `Run` inside the measurement panel. An active measurement can be stopped using the `Stop` button.

To execute a sequence of measurements click `Start` in the control panel blow the current sequence tree.

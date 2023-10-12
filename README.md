# PQC

Process Quality Control for CMS tracker

## Overview

This application provides PQC sensor measurements.

### Required instruments

|Instrument                            |Role |
|:-------------------------------------|:----|
|Keithley 707B Switching Matrix        |Matrix |
|Keysight E4980A LCR Meter             |LCR Meter |
|Keithley 6517B Electrometer           |ELM |
|Keithley 2410 Source Meter            |HV Source, V Source |
|Keithley 2470 Source Meter (optional) |HV Source, V Source |
|Keithley 2657A Source Meter           |V Source, HV Source |
|Corvus TT positioning controller      |Table |
|HEPHY Environment Box                 |Environment |

### Setup schematic

![PQC setup schematic](docs/assets/MatrixCardsDesign_v10_Diss2.png)

## Install

Install using pip in a virtual environment.

```bash
pip install git+https://github.com/hephy-dd/comet-pqc.git@<version>
```

## Run

```bash
pqc
```

## Binaries

See for pre-built Windows binaries in the [releases](https://github.com/hephy-dd/comet-pqc/releases) section.

## License

comet-pqc is licensed under the [GNU General Public License Version 3](https://github.com/hephy-dd/comet-pqc/tree/main/LICENSE).

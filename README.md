# COMET PQC

PQC sensor measurements

## Overview

This COMET application provides PQC sensor measurements.

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
pip install git+https://github.com/hephy-dd/comet-pqc.git@0.41.1
comet-pqc
```

## Instrument emulation

In _Edit_ &rarr; _Preferences_ &rarr; _Resources_ update resource
names to `TCPIP::localhost::1100x::SOCKET` to match the local emulation
sockets and set read/write termination to `\r\n`. Run every emulator
in a separate shell and termiante by using `Ctrl+C`.

```bash
python -m comet.emulator.keithley.k707 -p 11001
python -m comet.emulator.keithley.k2410 -p 11002
python -m comet.emulator.keithley.k2657a -p 11003
python -m comet.emulator.keithley.k6517b -p 11004
python -m comet_pqc.emulator.e4980a -p 11005
python -m comet_pqc.emulator.environmentbox -p 11006
python -m comet_pqc.emulator.venus1 -p 11007
```

## Binaries

See for pre-built Windows binaries in the releases section.

## License

comet-pqc is licensed under the [GNU General Public License Version 3](https://github.com/hephy-dd/comet-pqc/tree/master/LICENSE).

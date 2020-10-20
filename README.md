# COMET PQC

PQC sensor measurements

## Overview

This COMET application provides PQC sensor measurements.

### Required instruments:

- Keithley 707B Switching Matrix (matrix)
- Keysight E4980A LCR Meter (lcr)
- Keithley 6517B Electrometer (elm)
- Keithley 2410 Source Meter (HV Source)
- Keithley 2657A Source Meter (V Source)
- Corvus TT positioning controller (table)
- HEPHY Environment Box (environ)

## Install

Install using pip in a virtual environment.

```bash
pip install git+https://github.com/hephy-dd/comet-pqc.git@0.25.3
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
python -m comet.emulator.corvus.venus1 -p 11007
```

## Binaries

See for pre-built Windows binaries in the releases section.

## License

comet-pqc is licensed under the [GNU General Public License Version 3](https://github.com/hephy-dd/comet-pqc/tree/master/LICENSE).

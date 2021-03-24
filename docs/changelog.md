---
layout: default
title: Changelog
nav_order: 10
---

# Changelog
{: .no_toc }

## 0.33.0

### Changed
- Migrated to analysis-pqc version 0.2.0.

## 0.32.1

### Fixed
- Crash if log record timestamp is `NaN`.

## 0.32.0

### Added
- Repeat measurements based on analysis results.
- Accept compliance measurement options.
- Limits for analysis results.
- Step up function for table control.

### Changed
- Optimized measurement waiting time.
- Enable matrix at default.

## 0.31.0

### Added
- Delay after automatic table contact.
- Optional ramp delay parameters.

## 0.30.0

### Added
- Restricted limits for joystick use.
- Show points in plot line series.
- Disable table controls if not calibrated.

### Changed
- Move position assignment into edit dialog.

## 0.29.2

### Changed
- Migration to comet 0.13.1

### Fixed
- Prevent table collision while calibrating.
- Collapse sequence tree items.

## 0.29.1

### Fixed
- PNG images from plots only.

## 0.29.0

### Added
- Instrument abstraction using abstract class interface.
- Reload sequence configuration from file.

## 0.28.0

### Added
- Support for multiple samples.
- Automatic table movement to contacts.

## 0.27.1

### Changed
- Refactored V Source/HV Source communication.

## 0.27.0

### Added
- Start sequence dialog.

### Fixed
- Table error 1004 issue.

## 0.26.0

### Added
- Analysis functions parameter.
- Configurable steps for table control.
- Persistent history of working directories.

## 0.25.5

### Changed
- Round table position to microns.

## 0.25.4

### Added
- Backport of configurable table positions.

## 0.25.3

### Added
- Laser sensor state in table control dialog.
- Improved logging and exception forwarding.

### Fixed
- Persistent dialog size for HiDPI monitors.

## 0.25.2

### Fixed
- LCR fetch reading issue.

## 0.25.1

### Fixed
- Default HV source range value.
- Releasing multiple resources using ExitStack.

## 0.25.0

### Added
- Environment tab in dashboard.
- CV ramp measurement using only LCR.
- HV source range parameter.
- Analyze measurement data using [analysis-pqc](https://github.com/hephy-dd/analysis-pqc/).

### Fixed
- Sequence double click issue while running.

## 0.24.3

### Added
- Software version to measurement meta data.

### Fixed
- Missing package data in setup.py

## 0.24.2

### Fixed
- Table position meta data in millimeters.

## 0.24.1

### Added

- Table position to measurement meta data.
### Fixed
- Newline issue with CSV writer.

### Removed
- Laser sensor state from table control dialog.

## 0.24.0

### Added
- Sequence manager dialog.
- Changelog in online documentation.
- Write measurement data in JSON.
- Write measurement log files and.
- Laser sensor state in table control dialog.

## 0.23.4

### Fixed
- Inconsistent data column names.
- Incorrect data values for column `current_elm` in `iv_ramp_bias_elm`.

## 0.23.3

### Changed
- Migrated to COMET 0.11.1.

## 0.23.2

### Fixed
- Contents URL.

## 0.23.1

### Fixed
- Application crash if working directory permission denied.
- Mirrored table X/Y controls to match camera image movement.

## 0.23.0

### Added
- Operator name for measurement results.
- Save plots to PNG image and preferences option.
- Set environment TEST LED.

## 0.22.0

### Changed
- Migrated to COMET 0.11.0.
- Simplified Start/Stop mechanism.
- Rotated X/Y table controls.
- Set K2547A display.

## 0.21.1

### Fixed
- Auto generated `id` attributes can contain mixed case.

## 0.21.0

### Added
- Configuration attribute `id` for connections and measurements.

### Changed
- Measurement data filename schema.
- Keeping previous measurement states when running a sequence.

## 0.20.1

### Fixed
- Electrometer read.
- Show error message on YAML parser errors.

## 0.20.0

### Added
- Resource process.
- Environment process.
- Additional measurement states.
- Reset sequence tree on sample name changes.

### Changed
- Environment access using a process.
- Resized dialogs for table HiDPI screens.
- Simplified output directory structure.

### Fixed
- Sequence execution
- Timeouts while reading from electrometer.

## 0.19.1

### Added
- Restore previous window size.

## 0.19.0

### Added
- Open correction mode and channel option for LCR meter.
- Auto switch of box lights on start sequence/measurement.
- Configurable Z soft limit for table movements.
- This changelog file.

## 0.18.0

### Added
- Laser sensor toggle button.
- Microscope control toggle button.

## 0.17.1

### Changed
- Reduced ramp delays for initial/final ramps to speed up measurements.

## 0.17.0

### Added
- Table calibration dialog and process.
- Table control dialog and process.
- Table move dialog and process.
- Metric widget for numeric unit inputs.
- Property `passed` to Estimate class.

### Changed
- Moved config and schema to assets directory.
- Updated default matrix channel configurations.
- Filter selection for type `moving`.
- Default HV source route terminal `rear`.

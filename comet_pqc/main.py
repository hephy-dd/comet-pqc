import argparse
import logging
import sys

from PyQt5 import QtWidgets

import comet
from comet.driver import Driver
from comet.driver.keithley import K707B
from comet.driver.keithley import K2657A
from comet.driver.keysight import E4980A
from comet.driver.keithley import K6517B
from comet.driver.keithley import K2410
from comet.driver.corvus import Venus1

from . import __version__

from .processes import StatusProcess
from .processes import CalibrateProcess
from .processes import MeasureProcess
from .processes import SequenceProcess

from .dashboard import Dashboard

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()

def main():

    args = parse_args()

    app = comet.Application("comet-pqc")
    app.version = __version__
    app.title = f"PQC {__version__}"
    app.about = f"COMET application for PQC measurements, version {__version__}."

    logging.info("PQC version %s", __version__)

    # Register devices

    app.devices.add("matrix", K707B(comet.Resource(
        resource_name="TCPIP::10.0.0.2::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("k2657", K2657A(comet.Resource(
        resource_name="TCPIP::10.0.0.3::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("lcr", E4980A(comet.Resource(
        resource_name="TCPIP::10.0.0.6::5025::SOCKET",
        read_termination="\n",
        write_termination="\n",
        timeout=8000.0
    )))
    app.devices.add("k6517", K6517B(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=8000.0
    )))
    app.devices.add("k2410", K2410(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10002::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("corvus", Venus1(comet.Resource(
        resource_name="TCPIP::10.0.0.6::23::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=8000.0
    )))
    app.devices.add("environ", Driver(comet.Resource(
        resource_name="TCPIP::10.0.0.8::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.load_settings()

    # Dashboard

    dashboard = Dashboard()

    # Callbacks

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        comet.show_exception(exc, tb)

    def on_message(message):
        logging.info(message)
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    # Register processes

    app.processes.add("status", StatusProcess(
        events=dict(
            finished=dashboard.on_status_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress
        )
    ))
    app.processes.add("calibrate", CalibrateProcess(
        events=dict(
            finished=dashboard.on_calibrate_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress
        )
    ))
    app.processes.add("measure", MeasureProcess(
        events=dict(
            finished=dashboard.on_measure_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress,
            measurement_state=dashboard.on_measurement_state,
            reading=lambda name, x, y: logging.info("READING: %s %s %s", name, x, y)
        )
    ))
    app.processes.add("sequence", SequenceProcess(
        events=dict(
            finished=dashboard.on_sequence_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress,
            continue_contact=dashboard.on_continue_contact,
            continue_measurement=dashboard.on_continue_measurement,
            measurement_state=dashboard.on_measurement_state,
            reading=lambda name, x, y: logging.info("READING: %s %s %s", name, x, y)
        )
    ))

    # Layout

    app.layout = dashboard
    app.width = 1280
    app.height = 800

    # Tweaks

    # There's no hook, so it's a hack.
    ui = app.qt.window.ui
    sequenceMenu = QtWidgets.QMenu("&Sequence")
    ui.fileMenu.insertMenu(ui.quitAction, sequenceMenu)
    importAction = QtWidgets.QAction("&Import...")
    importAction.triggered.connect(dashboard.on_import_sequence)
    sequenceMenu.addAction(importAction)
    ui.fileMenu.insertSeparator(ui.quitAction)

    # Load configurations

    dashboard.load_chucks()
    dashboard.load_samples()
    dashboard.load_sequences()

    return app.run()

if __name__ == '__main__':
    sys.exit(main())

import argparse
import logging
import sys

from PyQt5 import QtWidgets

import comet
from comet import ui

from . import __version__

from .processes import EnvironmentProcess
from .processes import StatusProcess
from .processes import ControlProcess
from .processes import MoveProcess
from .processes import CalibrateProcess
from .processes import MeasureProcess
from .processes import SequenceProcess

from .dashboard import Dashboard
from .preferences import OptionsTab

CONTENTS_URL = 'https://hephy-dd.github.io/comet-pqc/'
GITHUB_URL = 'https://github.com/hephy-dd/comet-pqc/'

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()

def main():

    args = parse_args()

    # Logging

    logging.getLogger().setLevel(logging.INFO)
    logging.info("PQC version %s", __version__)

    app = comet.Application("comet-pqc")
    app.version = __version__
    app.title = f"PQC {__version__}"
    app.about = f"COMET application for PQC measurements, version {__version__}."

    # Register devices

    app.resources.add("matrix", comet.Resource(
        resource_name="TCPIP::10.0.0.2::5025::SOCKET",
        encoding='latin1',
        read_termination="\n",
        write_termination="\n"
    ))
    app.resources.add("hvsrc", comet.Resource(
        resource_name="TCPIP::10.0.0.5::10002::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=4000
    ))
    app.resources.add("vsrc", comet.Resource(
        resource_name="TCPIP::10.0.0.3::5025::SOCKET",
        encoding='latin1',
        read_termination="\n",
        write_termination="\n"
    ))
    app.resources.add("lcr", comet.Resource(
        resource_name="TCPIP::10.0.0.4::5025::SOCKET",
        read_termination="\n",
        write_termination="\n",
        timeout=8000
    ))
    app.resources.add("elm", comet.Resource(
        resource_name="TCPIP::10.0.0.5::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=8000
    ))
    app.resources.add("table", comet.Resource(
        resource_name="TCPIP::10.0.0.6::23::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=8000
    ))
    app.resources.add("environ", comet.Resource(
        resource_name="TCPIP::10.0.0.8::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    ))
    app.resources.load_settings()

    # Dashboard

    dashboard = Dashboard()

    # Callbacks

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        logging.error(tb)
        ui.show_exception(exc, tb)

    def on_message(message):
        ## logging.info(message)
        app.message = message

    def on_progress(value, maximum):
        if value == maximum:
            app.progress = None
        else:
            app.progress = value, maximum

    # Register processes

    app.processes.add("environment", EnvironmentProcess(
        name="environ",
        failed=on_show_error
    ))
    app.processes.add("status", StatusProcess(
        finished=dashboard.on_status_finished,
        failed=on_show_error,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("control", ControlProcess(
        failed=on_show_error,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("move", MoveProcess(
        failed=on_show_error,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("calibrate", CalibrateProcess(
        failed=on_show_error,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("measure", MeasureProcess(
        finished=dashboard.on_measure_finished,
        failed=on_show_error,
        message=on_message,
        progress=on_progress,
        measurement_state=dashboard.on_measurement_state,
        save_to_image=dashboard.on_save_to_image,
        reading=None
    ))
    app.processes.add("sequence", SequenceProcess(
        finished=dashboard.on_sequence_finished,
        failed=on_show_error,
        message=on_message,
        progress=on_progress,
        measurement_state=dashboard.on_measurement_state,
        save_to_image=dashboard.on_save_to_image,
        reading=None
    ))

    # Layout

    app.layout = dashboard

    # Restore window size
    app.width, app.height = app.settings.get('window_size', (1420, 920))

    # Extend actions
    app.window.github_action = ui.Action(
        text="&GitHub",
        triggered=dashboard.on_github
    )

    # Extend menus
    app.window.file_menu.insert(-1, ui.Action(separator=True))
    app.window.help_menu.insert(1, app.window.github_action)

    # Extend preferences
    options_tab = OptionsTab()
    app.window.preferences_dialog.tab_widget.append(options_tab)
    app.window.preferences_dialog.options_tab = options_tab

    # Set URLs
    app.window.contents_url = CONTENTS_URL
    app.window.github_url = GITHUB_URL

    # Fix progress bar width
    app.window.progress_bar.width = 600

    # Load configurations
    dashboard.load_sequences()
    dashboard.on_reset_sequence_state()

    # Start services
    app.processes.get("environment").start()

    # Sync environment controls
    if dashboard.environment_groupbox.checked:
        dashboard.sync_environment_controls()

    # HACK: resize preferences dialog for HiDPI
    dialog_size = app.settings.get('preferences_dialog_size', (640, 480))
    app.window.preferences_dialog.resize(*dialog_size)

    result = app.run()

    # Store window size
    app.settings['window_size'] = app.width, app.height
    dialog_size = app.window.preferences_dialog.size
    app.settings['preferences_dialog_size'] = dialog_size

    return result

if __name__ == '__main__':
    sys.exit(main())

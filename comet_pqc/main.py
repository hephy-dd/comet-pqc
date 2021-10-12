import argparse
import logging
import os
import sys

from logging import Formatter
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

import analysis_pqc

import comet
from comet import ui

from . import __version__
from .utils import user_home

from .processes import ContactQualityProcess
from .processes import EnvironmentProcess
from .processes import StatusProcess
from .processes import AlternateTableProcess
from .processes import MeasureProcess
from .processes import WebAPIProcess

from .dashboard import Dashboard
from .preferences import TableTab
from .preferences import WebAPITab
from .preferences import OptionsTab

from .settings import settings

CONTENTS_URL = 'https://hephy-dd.github.io/comet-pqc/'
GITHUB_URL = 'https://github.com/hephy-dd/comet-pqc/'

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()

def configure_logging():
    logger = logging.getLogger()
    # Stream handler
    stream_formatter = Formatter(
        fmt='%(levelname)s:%(name)s:%(message)s'
    )
    stream_handler = StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    # Rotating file handler
    filename = os.path.join(user_home(), 'comet-pqc.log')
    file_formatter = Formatter(
        fmt='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    file_handler = RotatingFileHandler(
        filename=filename,
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

def main():

    args = parse_args()

    # Logging

    configure_logging()

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

    # Callbacks

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        logging.error(tb)
        ui.show_exception(exc, tb)

    def on_message(message):
        app.message = message

    def on_progress(value, maximum):
        if value == maximum:
            app.progress = None
        else:
            app.progress = value, maximum

    # Register processes

    app.processes.add("environ", EnvironmentProcess(
        name="environ",
        failed=on_show_error
    ))
    app.processes.add("status", StatusProcess(
        failed=on_show_error,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("table", AlternateTableProcess(
        failed=on_show_error
    ))
    app.processes.add("measure", MeasureProcess(
        failed=on_show_error,
        message=on_message,
        progress=on_progress,
    ))
    app.processes.add("contact_quality", ContactQualityProcess(
        failed=on_show_error
    ))
    app.processes.add("webapi", WebAPIProcess(
        failed=on_show_error
    ))

    # Z-Limit notice
    temporary_z_limit_label = ui.Label(
        text="Temporary Probecard Z-Limit applied. "
             "Revert after finishing current measurements.",
        stylesheet="QLabel{background: yellow; padding: 4px; border-radius: 4px;}",
        visible=False
    )

    # Dashboard

    dashboard = Dashboard(
        message_changed=on_message,
        progress_changed=on_progress
    )

    logger.info("PQC version %s", __version__)
    logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

    # Layout

    app.layout = ui.Column(
        temporary_z_limit_label,
        dashboard,
        stretch=(0, 1)
    )

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
    table_tab = TableTab()
    temporary_z_limit_label.visible = settings.table_temporary_z_limit
    def toggle_temporary_z_limit(enabled):
        logger.info("Temporary Z-Limit enabled: %s", enabled)
        temporary_z_limit_label.visible = enabled
    table_tab.temporary_z_limit_changed = toggle_temporary_z_limit
    app.window.preferences_dialog.tab_widget.append(table_tab)
    app.window.preferences_dialog.table_tab = table_tab
    webapi_tab = WebAPITab()
    app.window.preferences_dialog.tab_widget.append(webapi_tab)
    app.window.preferences_dialog.webapi_tab = webapi_tab
    options_tab = OptionsTab()
    app.window.preferences_dialog.tab_widget.append(options_tab)
    app.window.preferences_dialog.options_tab = options_tab

    # Set URLs
    app.window.contents_url = CONTENTS_URL
    app.window.github_url = GITHUB_URL

    # Fix progress bar width
    app.window.progress_bar.width = 600

    # Load configurations
    dashboard.load_settings()

    # Sync environment controls
    if dashboard.use_environment():
        dashboard.environ_process.start()
        dashboard.sync_environment_controls()

    if dashboard.use_table():
        dashboard.table_process.start()
        dashboard.sync_table_controls()
        dashboard.table_process.enable_joystick(False)

    app.processes.get("webapi").start()

    # HACK: resize preferences dialog for HiDPI
    dialog_size = app.settings.get('preferences_dialog_size', (640, 480))
    app.window.preferences_dialog.resize(*dialog_size)

    result = app.run()

    dashboard.store_settings()

    # Store window size
    app.settings['window_size'] = app.width, app.height
    dialog_size = app.window.preferences_dialog.size
    app.settings['preferences_dialog_size'] = dialog_size

    return result

if __name__ == '__main__':
    sys.exit(main())

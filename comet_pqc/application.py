import logging
import sys

import analysis_pqc

import comet
from comet import ui

from . import __version__

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


class Application(comet.ResourceMixin, comet.ProcessMixin, comet.SettingsMixin):

    def __init__(self):
        self.app = comet.Application("comet-pqc")
        self.app.version = __version__
        self.app.title = f"PQC {__version__}"
        self.app.about = f"COMET application for PQC measurements, version {__version__}."

        self._setup_resources()
        self._setup_processes()

        # Dashboard
        self.dashboard = Dashboard(
            message_changed=self.on_message,
            progress_changed=self.on_progress
        )
        self.app.layout = self.dashboard

        # Fix progress bar width
        self.app.window.progress_bar.width = 600

        # Set URLs
        self.app.window.contents_url = CONTENTS_URL
        self.app.window.github_url = GITHUB_URL

        self._setup_actions()
        self._setup_menus()
        self._setup_preferences()

        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

    def _setup_resources(self):
        self.resources.add("matrix", comet.Resource(
            resource_name="TCPIP::10.0.0.2::5025::SOCKET",
            encoding='latin1',
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("hvsrc", comet.Resource(
            resource_name="TCPIP::10.0.0.5::10002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        ))
        self.resources.add("vsrc", comet.Resource(
            resource_name="TCPIP::10.0.0.3::5025::SOCKET",
            encoding='latin1',
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("lcr", comet.Resource(
            resource_name="TCPIP::10.0.0.4::5025::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        ))
        self.resources.add("elm", comet.Resource(
            resource_name="TCPIP::10.0.0.5::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("table", comet.Resource(
            resource_name="TCPIP::10.0.0.6::23::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("environ", comet.Resource(
            resource_name="TCPIP::10.0.0.8::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        ))
        self.resources.load_settings()

    def _setup_processes(self):
        self.processes.add("environ", EnvironmentProcess(
            name="environ",
            failed=self.on_show_error
        ))
        self.processes.add("status", StatusProcess(
            failed=self.on_show_error,
            message=self.on_message,
            progress=self.on_progress
        ))
        self.processes.add("table", AlternateTableProcess(
            failed=self.on_show_error
        ))
        self.processes.add("measure", MeasureProcess(
            failed=self.on_show_error,
            message=self.on_message,
            progress=self.on_progress,
        ))
        self.processes.add("contact_quality", ContactQualityProcess(
            failed=self.on_show_error
        ))
        self.processes.add("webapi", WebAPIProcess(
            failed=self.on_show_error
        ))

    def _setup_actions(self):
        self.app.window.github_action = ui.Action(
            text="&GitHub",
            triggered=self.dashboard.on_github
        )

    def _setup_menus(self):
        self.app.window.file_menu.insert(-1, ui.Action(separator=True))
        self.app.window.help_menu.insert(1, self.app.window.github_action)

    def _setup_preferences(self):
        table_tab = TableTab()
        self.dashboard.on_toggle_temporary_z_limit(settings.table_temporary_z_limit)
        table_tab.temporary_z_limit_changed = self.dashboard.on_toggle_temporary_z_limit
        self.app.window.preferences_dialog.tab_widget.append(table_tab)
        self.app.window.preferences_dialog.table_tab = table_tab

        webapi_tab = WebAPITab()
        self.app.window.preferences_dialog.tab_widget.append(webapi_tab)
        self.app.window.preferences_dialog.webapi_tab = webapi_tab

        options_tab = OptionsTab()
        self.app.window.preferences_dialog.tab_widget.append(options_tab)
        self.app.window.preferences_dialog.options_tab = options_tab

    def load_settings(self):
        # Restore window size
        self.app.width, self.app.height = self.settings.get('window_size', (1420, 920))
        # HACK: resize preferences dialog for HiDPI
        dialog_size = self.settings.get('preferences_dialog_size', (640, 480))
        self.app.window.preferences_dialog.resize(*dialog_size)
        # Load configurations
        self.dashboard.load_settings()

    def store_settings(self):
        self.dashboard.store_settings()
        # Store window size
        self.settings['window_size'] = self.app.width, self.app.height
        dialog_size = self.app.window.preferences_dialog.size
        self.settings['preferences_dialog_size'] = dialog_size

    def event_loop(self):
        # Sync environment controls
        if self.dashboard.use_environment():
            self.dashboard.environ_process.start()
            self.dashboard.sync_environment_controls()

        if self.dashboard.use_table():
            self.dashboard.table_process.start()
            self.dashboard.sync_table_controls()
            self.dashboard.table_process.enable_joystick(False)

        self.processes.get("webapi").start()

        return self.app.run()

    def on_show_error(self, exc, tb):
        self.app.message = "Exception occured!"
        self.app.progress = None
        logger.exception(exc)
        ui.show_exception(exc, tb)

    def on_message(self, message):
        self.app.message = message

    def on_progress(self, value, maximum):
        if value == maximum:
            self.app.progress = None
        else:
            self.app.progress = value, maximum

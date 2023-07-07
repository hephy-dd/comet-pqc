import logging
import sys
import signal

from PyQt5 import QtCore, QtGui, QtWidgets
import analysis_pqc
import comet
from comet import ui
from .mainwindow import MainWindow

from . import __version__
from .dashboard import Dashboard
from .processes import (
    AlternateTableProcess,
    ContactQualityProcess,
    EnvironmentProcess,
    MeasureProcess,
    StatusProcess,
    WebAPIProcess,
)
from .settings import settings
from .core.utils import make_path

from .plugins import PluginManager
from .plugins.logger import LoggerPlugin
from .plugins.summary import SummaryPlugin

CONTENTS_URL: str = "https://hephy-dd.github.io/comet-pqc/"
GITHUB_URL: str = "https://github.com/hephy-dd/comet-pqc/"

logger = logging.getLogger(__name__)


class Application(comet.ResourceMixin, comet.ProcessMixin, comet.SettingsMixin):

    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setApplicationName("comet-pqc")
        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("HEPHY")
        self.app.setOrganizationDomain("hephy.at")
        self.app.setApplicationDisplayName(f"PQC {__version__}")
        self.app.setWindowIcon(QtGui.QIcon(make_path("assets", "icons", "pqc.ico")))
        self.app.setProperty("contentsUrl", CONTENTS_URL)
        self.app.setProperty("githubUrl", GITHUB_URL)
        self.app.lastWindowClosed.connect(self.app.quit)

        # TODO
        self.app.reflection = lambda: self.app
        self.app.name = self.app.applicationName()
        self.app.organization = self.app.organizationName()

        self._setup_resources()
        self._setup_processes()

        # Dashboard
        self.dashboard = Dashboard(
            lock_state_changed=self.on_lock_state_changed,
            message_changed=self.on_message,
            progress_changed=self.on_progress,
        )
        self.central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.central_widget)
        layout.addWidget(self.dashboard.qt)

        # Initialize main window
        self.window = MainWindow()
        self.window.setCentralWidget(self.central_widget)

        self.preferences_dialog = self.window.preferences_dialog

        self.plugin_manager = PluginManager()
        self.plugin_manager.register_pugin(LoggerPlugin(self.dashboard))
        self.plugin_manager.register_pugin(SummaryPlugin(self.dashboard))

        self.dashboard.plugin_manager = self.plugin_manager

        self._setup_preferences()

    def _setup_resources(self):
        self.resources.add("matrix", comet.Resource(
            resource_name="TCPIP::10.0.0.2::5025::SOCKET",
            encoding="latin1",
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
            encoding="latin1",
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

    def _setup_preferences(self):
        self.dashboard.on_toggle_temporary_z_limit(settings.table_temporary_z_limit)
        self.preferences_dialog.table_tab.temporary_z_limit_changed = self.dashboard.on_toggle_temporary_z_limit

    def load_settings(self):
        # Restore window size
        width, height = self.settings.get("window_size", (1420, 920))
        self.window.resize(width, height)
        # HACK: resize preferences dialog for HiDPI
        width, height = self.settings.get("preferences_dialog_size", (640, 480))
        self.preferences_dialog.resize(width, height)
        # Load configurations
        self.dashboard.load_settings()

    def store_settings(self):
        self.dashboard.store_settings()
        # Store window size
        width, height = self.window.width(), self.window.height()
        self.settings["window_size"] = width, height
        width, height = self.preferences_dialog.size
        self.settings["preferences_dialog_size"] = width, height

    def event_loop(self):
        self.plugin_manager.install_plugins()

        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

        # Sync environment controls
        if self.dashboard.use_environment():
            self.dashboard.environ_process.start()
            self.dashboard.sync_environment_controls()

        if self.dashboard.use_table():
            self.dashboard.table_process.start()
            self.dashboard.sync_table_controls()
            self.dashboard.table_process.enable_joystick(False)

        self.processes.get("webapi").start()

        # Register interupt signal handler
        def signal_handler(signum, frame):
            if signum == signal.SIGINT:
                self.app.quit()
        signal.signal(signal.SIGINT, signal_handler)

        # Run timer to process interrupt signals
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(250)

        self.window.show()
        self.window.raise_()

        try:
            return self.app.exec_()
        finally:
            # Stop processes
            self.processes.stop()
            self.processes.join()
            self.plugin_manager.uninstall_plugins()

    def on_show_error(self, exc, tb):
        self.on_message("Exception occured!")
        self.on_progress(None, None)
        logger.exception(exc)
        ui.show_exception(exc, tb)

    def on_lock_state_changed(self, state):
        self.window.preferences_action.setEnabled(not state)

    def on_message(self, message):
        if message is None:
            self.window.hide_message()
        else:
            self.window.show_message(message)

    def on_progress(self, value, maximum):
        if value == maximum:
            self.window.hide_progress()
        else:
            self.window.show_progress(value, maximum)

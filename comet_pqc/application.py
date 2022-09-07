import logging
import sys
import signal
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

import analysis_pqc
import comet

from . import __version__
from .mainwindow import MainWindow
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
        self.app.lastWindowClosed.connect(self.app.quit)

        # TODO for SettingsMixin
        self.app.reflection = lambda: self.app
        self.app.name = self.app.applicationName()
        self.app.organization = self.app.organizationName()

        self._setup_resources()
        self._setup_processes()

        self.window = MainWindow()
        self.window.setProperty("contentsUrl", CONTENTS_URL)
        self.window.setProperty("githubUrl", GITHUB_URL)

        self.dashboard = self.window.dashboard
        self.dashboard.message_changed = self.on_message,
        self.dashboard.progress_changed = self.on_progress

        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

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

    def load_settings(self):
        # Restore window size
        width, height = self.settings.get("window_size", (1420, 920))
        self.window.resize(width, height)
        # HACK: resize preferences dialog for HiDPI
        width, height = self.settings.get("preferences_dialog_size", (640, 480))
        self.window.preferencesDialog.resize(width, height)
        # Load configurations
        self.dashboard.load_settings()

    def store_settings(self):
        self.dashboard.store_settings()
        # Store window size
        width, height = self.window.width(), self.window.height()
        self.settings["window_size"] = width, height
        width, height = self.window.preferencesDialog.size
        self.settings["preferences_dialog_size"] = width, height

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

        try:
            return self.app.exec()
        finally:
            # Stop processes
            self.processes.stop()
            self.processes.join()

    def on_show_error(self, exc, tb):
        logger.exception(exc)
        self.window.showMessage("Exception occured!")
        self.window.hideProgress()
        self.window.showException(exc, tb)

    def on_message(self, message: Optional[str]) -> None:
        if message is None:
            self.window.hideMessage()
        else:
            self.window.showMessage(message)

    def on_progress(self, value: int, maximum: int) -> None:
        minimum = 0
        if value == maximum:
            self.window.hideProgress()
        else:
            self.window.showProgress(minimum, maximum, value)

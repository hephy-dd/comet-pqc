import logging
import sys
import signal

from PyQt5 import QtCore, QtGui, QtWidgets
import analysis_pqc
import comet
from comet import ui
from .mainwindow import MainWindow

from . import __version__
from .processes import (
    AlternateTableProcess,
    ContactQualityProcess,
    EnvironmentProcess,
    MeasureProcess,
)
from .settings import settings
from .core.utils import make_path

from .plugins import PluginManager
from .plugins.status import StatusPlugin
from .plugins.logger import LoggerPlugin
from .plugins.webapi import WebAPIPlugin
from .plugins.notification import NotificationPlugin
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

        # Register interupt signal handler
        def signal_handler(signum, frame):
            if signum == signal.SIGINT:
                self.app.quit()

        signal.signal(signal.SIGINT, signal_handler)

        self._setup_resources()
        self._setup_processes()

        self.window = MainWindow()

        self.plugin_manager = PluginManager()
        self.plugin_manager.register_pugin(StatusPlugin(self.window))
        self.plugin_manager.register_pugin(LoggerPlugin(self.window))
        self.plugin_manager.register_pugin(WebAPIPlugin(self.window))
        self.plugin_manager.register_pugin(SummaryPlugin(self.window))
        self.plugin_manager.register_pugin(NotificationPlugin(self.window))

        self.window.dashboard.plugin_manager = self.plugin_manager

    def _setup_resources(self):
        self.resources.add("matrix", comet.Resource(
            resource_name="TCPIP::localhost::11001::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("hvsrc", comet.Resource(
            resource_name="TCPIP::localhost::11002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        ))
        self.resources.add("vsrc", comet.Resource(
            resource_name="TCPIP::localhost::11003::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("lcr", comet.Resource(
            resource_name="TCPIP::localhost::11004::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        ))
        self.resources.add("elm", comet.Resource(
            resource_name="TCPIP::localhost::11005::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("table", comet.Resource(
            resource_name="TCPIP::localhost::11006::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("environ", comet.Resource(
            resource_name="TCPIP::localhost::11007::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        ))
        self.resources.load_settings()

    def _setup_processes(self):
        self.processes.add("environ", EnvironmentProcess(name="environ"))
        self.processes.add("table", AlternateTableProcess())
        self.processes.add("measure", MeasureProcess())
        self.processes.add("contact_quality", ContactQualityProcess())

    def readSettings(self) -> None:
        self.window.readSettings()

    def writeSettings(self) -> None:
        self.window.writeSettings()

    def eventLoop(self) -> None:
        self.plugin_manager.install_plugins()

        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

        self.window.dashboard.on_toggle_temporary_z_limit(settings.table_temporary_z_limit)

        # Sync environment controls
        if self.window.dashboard.use_environment():
            self.window.dashboard.environ_process.start()
            self.window.dashboard.sync_environment_controls()

        if self.window.dashboard.use_table():
            self.window.dashboard.table_process.start()
            self.window.dashboard.sync_table_controls()
            self.window.dashboard.table_process.enable_joystick(False)

        # Run timer to process interrupt signals
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(250)

        self.window.readSettings()
        self.window.show()

        self.app.exec_()

        # Stop processes
        self.processes.stop()
        self.processes.join()
        self.plugin_manager.uninstall_plugins()

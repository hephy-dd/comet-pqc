import logging
import sys
import signal
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

import analysis_pqc
import comet

from .. import __version__
from ..processes import (
    AlternateTableProcess,
    ContactQualityProcess,
    EnvironmentProcess,
    MeasureProcess,
    StatusProcess,
)
from ..core.resource import resource_registry
from ..core.utils import make_path
from ..settings import settings
from ..plugins import PluginSystem
from ..plugins.webapi import WebAPIPlugin
from ..plugins.quickedit import QuickEditPlugin
from ..plugins.summary import SummaryPlugin

from .mainwindow import MainWindow

CONTENTS_URL: str = "https://hephy-dd.github.io/comet-pqc/"
GITHUB_URL: str = "https://github.com/hephy-dd/comet-pqc/"

logger = logging.getLogger(__name__)


class Application(comet.ProcessMixin):

    def __init__(self) -> None:
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setApplicationName("comet-pqc")
        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("HEPHY")
        self.app.setOrganizationDomain("hephy.at")
        self.app.setApplicationDisplayName(f"PQC {__version__}")
        self.app.setWindowIcon(QtGui.QIcon(make_path("assets", "icons", "pqc.ico")))

        # Register interupt signal handler
        def signal_handler(signum, frame):
            if signum == signal.SIGINT:
                self.app.quit()
        signal.signal(signal.SIGINT, signal_handler)

        # TODO for SettingsMixin
        self.app.reflection = lambda: self.app
        self.app.name = self.app.applicationName()
        self.app.organization = self.app.organizationName()

        self._setupResources()
        self._setupProcesses()

        self._loadResourceSettings()

        self.window = MainWindow()
        self.window.setProperty("contentsUrl", CONTENTS_URL)
        self.window.setProperty("githubUrl", GITHUB_URL)

        self.dashboard = self.window.dashboard  # TODO
        self.dashboard.messageChanged.connect(self.updateMessage)
        self.dashboard.progressChanged.connect(self.updateProgress)

        self.plugins = PluginSystem(self.window)
        self.plugins.addPlugin(WebAPIPlugin())
        self.plugins.addPlugin(QuickEditPlugin())
        self.plugins.addPlugin(SummaryPlugin())

        self.app.lastWindowClosed.connect(self.app.quit)
        self.app.aboutToQuit.connect(self.shutdown)

        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)

        self.plugins.installPlugins()

    def _setupResources(self) -> None:
        resource_registry["matrix"] = comet.Resource(
            resource_name="TCPIP::10.0.0.2::5025::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        )
        resource_registry["hvsrc"] = comet.Resource(
            resource_name="TCPIP::10.0.0.5::10002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        )
        resource_registry["vsrc"] = comet.Resource(
            resource_name="TCPIP::10.0.0.3::5025::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        )
        resource_registry["lcr"] = comet.Resource(
            resource_name="TCPIP::10.0.0.4::5025::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        )
        resource_registry["elm"] = comet.Resource(
            resource_name="TCPIP::10.0.0.5::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        )
        resource_registry["table"] = comet.Resource(
            resource_name="TCPIP::10.0.0.6::23::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        )
        resource_registry["environ"] = comet.Resource(
            resource_name="TCPIP::10.0.0.8::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        )

    def _loadResourceSettings(self) -> None:
        # Load settings TODO
        resource_settings = settings.resources()
        for name, resource in resource_registry.items():
            if name in resource_settings:
                if "address" in resource_settings[name]:
                    resource.resource_name = resource_settings[name]["address"]
                resource.visa_library = "@py"
                if "termination" in resource_settings[name]:
                    resource.options["read_termination"] = resource_settings[name]["termination"]
                    resource.options["write_termination"] = resource_settings[name]["termination"]
                if "timeout" in resource_settings[name]:
                    resource.options["timeout"] = resource_settings[name]["timeout"] * 1e3  # to millisconds

    def _setupProcesses(self) -> None:
        self.processes.add("environ", EnvironmentProcess(
            name="environ",
            failed=self.showException
        ))
        self.processes.add("status", StatusProcess(
            failed=self.showException,
            message=self.updateMessage,
            progress=self.updateProgress
        ))
        self.processes.add("table", AlternateTableProcess(
            failed=self.showException
        ))
        self.processes.add("measure", MeasureProcess(
            failed=self.showException,
            message=self.updateMessage,
            progress=self.updateProgress,
        ))
        self.processes.add("contact_quality", ContactQualityProcess(
            failed=self.showException
        ))

    def readSettings(self) -> None:
        self.window.readSettings()

    def writeSettings(self) -> None:
        self.window.writeSettings()

    def eventLoop(self) -> None:
        # Sync environment controls
        if self.dashboard.use_environment():  # TODO
            self.dashboard.environ_process.start()
            self.dashboard.sync_environment_controls()

        if self.dashboard.use_table():  # TODO
            self.dashboard.table_process.start()
            self.dashboard.sync_table_controls()
            self.dashboard.table_process.enable_joystick(False)

        self.processes.get("webapi").start()

        # Run timer to process interrupt signals
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(250)

        self.window.show()

        self.app.exec()

    def shutdown(self) -> None:
        self.plugins.uninstallPlugins()
        self.processes.stop()
        self.processes.join()

    def showException(self, exc: Exception, tb) -> None:
        logger.exception(exc)
        self.window.showMessage("Exception occured!")
        self.window.hideProgress()
        self.window.showException(exc)

    def updateMessage(self, message: Optional[str]) -> None:
        if message is None:
            self.window.hideMessage()
        else:
            self.window.showMessage(message)

    def updateProgress(self, value: int, maximum: int) -> None:
        minimum: int = 0
        if value == maximum:
            self.window.hideProgress()
        else:
            self.window.showProgress(minimum, maximum, value)

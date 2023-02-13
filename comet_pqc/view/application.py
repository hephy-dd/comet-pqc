import logging
import signal
import sys

import analysis_pqc
import comet
from PyQt5 import QtCore, QtGui, QtWidgets

from .. import __version__
from ..core.utils import make_path
from .context import Context
from .mainwindow import MainWindow

CONTENTS_URL: str = "https://hephy-dd.github.io/comet-pqc/"
GITHUB_URL: str = "https://github.com/hephy-dd/comet-pqc/"

logger = logging.getLogger(__name__)


class Application:

    def __init__(self):
        self.app: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
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

        self.app.processEvents()

        self.context = Context()

        self.window = MainWindow(self.context)

        self.context.environ_process.failed = self.window.showException,

        self.context.status_process.failed = self.window.showException
        self.context.status_process.message = self.window.showMessage
        self.context.status_process.progress = self.window.showProgress

        self.context.table_process.failed = self.window.showException
        self.context.table_process.message_changed.connect(self.window.showMessage)
        self.context.table_process.progress_changed.connect(self.window.showProgress)

        self.context.measure_process.failed = self.window.showException
        self.context.measure_process.message = self.window.showMessage
        self.context.measure_process.progress = self.window.showProgress

        self.context.contact_quality_process.failed = self.window.showException

    def readSettings(self) -> None:
        self.context.resources.load_settings()
        self.window.readSettings()

    def writeSettings(self) -> None:
        self.window.writeSettings()

    def eventLoop(self) -> None:
        logger.info("PQC version %s", __version__)
        logger.info("Analysis-PQC version %s", analysis_pqc.__version__)
        logger.info("COMET version %s", comet.__version__)

        # Sync environment controls
        if self.window.dashboard.isEnvironmentEnabled():
            self.context.environ_process.start()
            self.window.dashboard.sync_environment_controls()

        if self.window.dashboard.isTableEnabled():
            self.context.table_process.start()
            self.window.dashboard.sync_table_controls()
            self.context.table_process.enable_joystick(False)

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

        self.app.exec()

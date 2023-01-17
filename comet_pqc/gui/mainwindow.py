import logging
import webbrowser
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet import ProcessMixin

from ..settings import settings
from ..utils import show_exception

from .dashboard import Dashboard
from .preferences import PreferencesDialog
from .resources import ResourcesDialog

__all__ = ["MainWindow"]

APP_TITLE: str = "PQC"
APP_COPY: str = "Copyright &copy; 2020-2023 HEPHY"
APP_LICENSE: str = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION: str = """Process Quality Control (PQC) for CMS Tracker."""


class MainWindow(QtWidgets.QMainWindow, ProcessMixin):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Actions

        self.quitAction = QtWidgets.QAction(self)
        self.quitAction.setText("&Quit")
        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.triggered.connect(self.close)

        self.preferencesAction = QtWidgets.QAction(self)
        self.preferencesAction.setText("Prefere&nces")
        self.preferencesAction.triggered.connect(self.showPreferences)

        self.resourcesAction = QtWidgets.QAction(self)
        self.resourcesAction.setText("&Resources")
        self.resourcesAction.triggered.connect(self.showResources)

        self.contentsAction = QtWidgets.QAction(self)
        self.contentsAction.setText("&Contents")
        self.contentsAction.setShortcut("F1")
        self.contentsAction.triggered.connect(self.showContents)

        self.githubAction = QtWidgets.QAction(self)
        self.githubAction.setText("&GitHub")
        self.githubAction.triggered.connect(self.showGithub)

        self.aboutQtAction = QtWidgets.QAction(self)
        self.aboutQtAction.setText("About Qt")
        self.aboutQtAction.triggered.connect(self.showAboutQt)

        self.aboutAction = QtWidgets.QAction(self)
        self.aboutAction.setText("&About")
        self.aboutAction.triggered.connect(self.showAbout)

        # Menus

        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.quitAction)

        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.preferencesAction)
        self.editMenu.addAction(self.resourcesAction)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.contentsAction)
        self.helpMenu.addAction(self.githubAction)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.aboutQtAction)
        self.helpMenu.addAction(self.aboutAction)

        # Setup status bar widgets

        self.messageLabel = QtWidgets.QLabel(self)
        self.statusBar().addPermanentWidget(self.messageLabel)

        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setFixedWidth(600)
        self.statusBar().addPermanentWidget(self.progressBar)

        # Dashboard

        self.temporaryNoticeLabel = QtWidgets.QLabel(self)
        self.temporaryNoticeLabel.setText(
            "Temporary Probecard Z-Limit applied. "
            "Revert after finishing current measurements."
        )
        self.temporaryNoticeLabel.setStyleSheet("QLabel{color: black; background-color: yellow; padding: 4px; border-radius: 4px;}")
        self.temporaryNoticeLabel.setVisible(settings.tableTemporaryZLimit())

        self.dashboard = Dashboard(self)

        widget = QtWidgets.QWidget()
        self.setCentralWidget(widget)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(self.temporaryNoticeLabel, 0)
        layout.addWidget(self.dashboard, 1)

        # State machine

        self.idleState = QtCore.QState()
        self.idleState.entered.connect(self.enterIdle)

        self.runningState = QtCore.QState()
        self.runningState.entered.connect(self.enterRunning)

        self.stoppingState = QtCore.QState()
        self.stoppingState.entered.connect(self.enterStopping)

        self.idleState.addTransition(self.dashboard.started, self.runningState)

        self.runningState.addTransition(self.dashboard.stopping, self.stoppingState)
        self.runningState.addTransition(self.dashboard.finished, self.idleState)

        self.stoppingState.addTransition(self.dashboard.finished, self.idleState)

        self.stateMachine= QtCore.QStateMachine(self)
        self.stateMachine.addState(self.idleState)
        self.stateMachine.addState(self.runningState)
        self.stateMachine.addState(self.stoppingState)
        self.stateMachine.setInitialState(self.idleState)
        self.stateMachine.start()

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("MainWindow")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)
        state = settings.value("state", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreState(state)
        settings.endGroup()

        self.dashboard.readSettings()

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.endGroup()

        self.dashboard.writeSettings()

    def enterIdle(self) -> None:
        self.preferencesAction.setEnabled(True)
        self.resourcesAction.setEnabled(True)
        self.hideMessage()
        self.hideProgress()

    def enterRunning(self) -> None:
        self.preferencesAction.setEnabled(False)
        self.resourcesAction.setEnabled(False)

    def enterStopping(self) -> None:
        ...

    def showPreferences(self) -> None:
        """Show modal preferences dialog."""
        try:
            dialog = PreferencesDialog()
            dialog.readSettings()
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                dialog.writeSettings()
                # Update temp. Z limit message
                self.temporaryNoticeLabel.setVisible(settings.tableTemporaryZLimit())
        except Exception as exc:
            self.showException(exc)

    def showResources(self) -> None:
        """Show modal resources dialog."""
        try:
            dialog = ResourcesDialog(self)
            dialog.readSettings()
            dialog.setResources(settings.resources())
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                dialog.writeSettings()
                settings.setResources(dialog.resources())
        except Exception as exc:
            self.showException(exc)

    def showContents(self) -> None:
        """Open local webbrowser with contents URL."""
        contents_url = self.property("contentsUrl")
        if isinstance(contents_url, str):
            webbrowser.open(contents_url)

    def showGithub(self) -> None:
        """Open local webbrowser with GitHub URL."""
        github_url = self.property("githubUrl")
        if isinstance(github_url, str):
            webbrowser.open(github_url)

    def showAboutQt(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    def showAbout(self) -> None:
        version = QtWidgets.QApplication.applicationVersion()
        QtWidgets.QMessageBox.about(self, "About", "".join([
            f"<h1>{APP_TITLE}</h1>",
            f"<p>Version {version}</p>",
            f"<p>{APP_DECRIPTION}</p>",
            f"<p>{APP_COPY}</p>",
            f"<p>{APP_LICENSE}</p>"
        ]))

    def showMessage(self, message: str) -> None:
        """Show status message."""
        self.messageLabel.setText(message)
        self.messageLabel.show()

    def hideMessage(self) -> None:
        """Hide status message."""
        self.messageLabel.clear()
        self.messageLabel.hide()

    def showProgress(self, minimum: int, maximum: int, value: int) -> None:
        """Show progress bar."""
        self.progressBar.setRange(minimum, maximum)
        self.progressBar.setValue(value)
        self.progressBar.show()

    def hideProgress(self) -> None:
        """Hide progress bar."""
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)
        self.progressBar.hide()

    def showException(self, exc: Exception) -> None:
        """Raise message box showing exception information."""
        self.showMessage("Error")
        self.hideProgress()
        logging.exception(exc)
        show_exception(exc)

    def shutdown(self) -> None:
        def shutdown():
            self.processes.stop()
            self.processes.join()
            dialog.close()

        dialog = QtWidgets.QProgressDialog(self)
        dialog.setRange(0, 0)
        dialog.setValue(0)
        dialog.setCancelButton(None)
        dialog.setLabelText("Stopping active threads...")
        QtCore.QTimer.singleShot(250, shutdown)
        dialog.exec()

        self.stateMachine.stop()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        result = QtWidgets.QMessageBox.question(
            self,
            "Quit?",
            "Do you want to quit the application?"
        )
        if result == QtWidgets.QMessageBox.Yes:
            self.shutdown()
            event.accept()
        else:
            event.ignore()

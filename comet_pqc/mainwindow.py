import webbrowser

from PyQt5 import QtCore, QtWidgets

from comet import ProcessMixin
from comet.ui.preferences import PreferencesDialog

from .dashboard import Dashboard
from .preferences import PreferencesDialog
from .resources import ResourcesDialog
from .settings import settings
from .utils import show_exception

__all__ = ["MainWindow"]

APP_TITLE: str = "PQC"
APP_COPY: str = "Copyright &copy; 2020-2022 HEPHY"
APP_LICENSE: str = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION: str = """Process Quality Control (PQC) for CMS Tracker."""


class MainWindow(QtWidgets.QMainWindow, ProcessMixin):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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

        self.dashboard = Dashboard(
            lock_state_changed = self.setLocked,
        )
        self.dashboard.on_toggle_temporary_z_limit(settings.table_temporary_z_limit)

        widget = QtWidgets.QWidget()
        self.setCentralWidget(widget)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(self.dashboard.qt)

        # Dialogs

        self.preferencesDialog = PreferencesDialog()
        self.preferencesDialog.hide()
        self.preferencesDialog.table_tab.temporary_z_limit_changed = self.dashboard.on_toggle_temporary_z_limit

        # Events

        self.setLocked(False)
        self.hideMessage()
        self.hideProgress()

    def setLocked(self, state: bool) -> None:
        self.preferencesAction.setEnabled(not state)
        self.resourcesAction.setEnabled(not state)

    def showPreferences(self) -> None:
        """Show modal preferences dialog."""
        try:
            self.preferencesDialog.run()
        except Exception as exc:
            self.showException(exc)

    def showResources(self) -> None:
        """Show modal resources dialog."""
        try:
            dialog = ResourcesDialog(self)
            dialog.readSettings()
            dialog.setResources(settings.resources())
            dialog.exec()
            dialog.syncSettings()
            if dialog.result() == dialog.Accepted:
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

    def showException(self, exc: Exception, tb=None) -> None:
        """Raise message box showing exception information."""
        self.showMessage("Error")
        self.hideProgress()
        show_exception(exc, tb)

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

    def closeEvent(self, event: QtCore.QEvent) -> None:
        result = QtWidgets.QMessageBox.question(self, "", "Quit application?")
        if result == QtWidgets.QMessageBox.Yes:
            self.shutdown()
            event.accept()
        else:
            event.ignore()

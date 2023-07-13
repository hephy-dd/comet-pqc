import webbrowser

from PyQt5 import QtCore, QtWidgets

from comet import ui, ProcessMixin
from comet.ui.preferences import PreferencesDialog

from .dashboard import Dashboard
from .preferences import OptionsTab, TableTab

__all__ = ["MainWindow"]

APP_TITLE = "PQC"
APP_COPY = "Copyright &copy; 2020-2023 HEPHY"
APP_LICENSE = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION = """Process Quality Control (PQC) for CMS Tracker."""


class MainWindow(QtWidgets.QMainWindow, ProcessMixin):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Actions

        self.quitAction = QtWidgets.QAction(self)
        self.quitAction.setText("&Quit")
        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.triggered.connect(self.close)

        self.preferencesAction = QtWidgets.QAction(self)
        self.preferencesAction.setText("Prefere&nces")
        self.preferencesAction.triggered.connect(self.showPreferences)

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

        # Dialogs
        self.preferencesDialog = PreferencesDialog()
        self.preferencesDialog.hide()

        table_tab = TableTab()
        self.preferencesDialog.tab_widget.append(table_tab)
        self.preferencesDialog.table_tab = table_tab

        options_tab = OptionsTab()
        self.preferencesDialog.tab_widget.append(options_tab)
        self.preferencesDialog.options_tab = options_tab

        self.hideMessage()
        self.hideProgress()

        self.dashboard = Dashboard()
        self.dashboard.lockStateChanged.connect(lambda state: self.preferencesAction.setEnabled(not state))
        self.dashboard.messageChanged.connect(self.showMessage)
        self.dashboard.progressChanged.connect(self.showProgress)
        self.dashboard.failed.connect(self.showException)
        self.setCentralWidget(self.dashboard)

        self.preferencesDialog.table_tab.temporary_z_limit_changed = self.dashboard.on_toggle_temporary_z_limit

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        geometry = settings.value("geometry", None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("state", None)
        if state is not None:
            self.restoreState(state)
        settings.endGroup()
        settings.beginGroup("preferences")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not geometry.isEmpty():
            self.preferencesDialog.qt.restoreGeometry(geometry)
        settings.endGroup()
        self.dashboard.readSettings()

    def writeSettings(self):
        self.dashboard.writeSettings()
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.endGroup()
        settings.beginGroup("preferences")
        settings.setValue("geometry", self.preferencesDialog.qt.saveGeometry())
        settings.endGroup()

    def showPreferences(self) -> None:
        """Show modal preferences dialog."""
        self.preferencesDialog.run()

    def showContents(self) -> None:
        """Open local webbrowser with contents URL."""
        contents_url = QtWidgets.QApplication.instance().property("contentsUrl")
        if isinstance(contents_url, str):
            webbrowser.open(contents_url)

    def showGithub(self) -> None:
        """Open local webbrowser with GitHub URL."""
        github_url = QtWidgets.QApplication.instance().property("githubUrl")
        if isinstance(github_url, str):
            webbrowser.open(github_url)

    def showAboutQt(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    def showAbout(self) -> None:
        version = QtWidgets.QApplication.applicationVersion()
        QtWidgets.QMessageBox.about(self, "About", f"<h1>{APP_TITLE}</h1><p>Version {version}</p><p>{APP_DECRIPTION}</p><p>{APP_COPY}</p><p>{APP_LICENSE}</p>")

    def showMessage(self, message: str) -> None:
        """Show status message."""
        self.messageLabel.setText(message)
        self.messageLabel.setVisible(len(message) > 0)

    def hideMessage(self) -> None:
        """Hide status message."""
        self.messageLabel.clear()
        self.messageLabel.hide()

    def showProgress(self, value: int, maximum: int) -> None:
        """Show progress bar."""
        self.progressBar.setRange(0, maximum)
        self.progressBar.setValue(value)
        self.progressBar.setVisible(value != maximum)

    def hideProgress(self) -> None:
        """Hide progress bar."""
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)
        self.progressBar.hide()

    def showException(self, exception: Exception, tb=None) -> None:
        """Raise message box showing exception information."""
        ui.show_exception(exception, tb)
        self.showMessage("Error")
        self.hideProgress()

    def pages(self) -> list:
        widgets = []
        for index in range(self.dashboard.tabWidget.count()):
            widgets.append(self.dashboard.tabWidget.widget(index))
        return widgets

    def addPage(self, widget: QtWidgets.QWidget, label: str) -> None:
        self.dashboard.tabWidget.addTab(widget, label)

    def removePage(self, widget: QtWidgets.QWidget) -> None:
        index = self.dashboard.tabWidget.indexOf(widget)
        self.dashboard.tabWidget.removeTab(index)

    def closeEvent(self, event: QtCore.QEvent) -> None:
        result = QtWidgets.QMessageBox.question(self, "", "Quit application?")
        if result == QtWidgets.QMessageBox.Yes:
            if self.processes:
                dialog = QtWidgets.QProgressDialog(self)
                dialog.setRange(0, 0)
                dialog.setCancelButton(None)
                dialog.setLabelText("Stopping active threads...")
                def shutdown():
                    self.processes.stop()
                    self.processes.join()
                    dialog.close()
                QtCore.QTimer.singleShot(250, shutdown)
                dialog.exec()
            event.accept()
        else:
            event.ignore()

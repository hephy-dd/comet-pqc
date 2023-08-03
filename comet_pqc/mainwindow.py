import json
import logging
import os
import traceback
import webbrowser

from PyQt5 import QtCore, QtGui, QtWidgets

from comet import ProcessMixin

from .components import MessageBox
from .dashboard import Dashboard, SampleTreeItem
from .preferences import PreferencesDialog
from .plugins import PluginManager
from .plugins.status import StatusPlugin
from .plugins.logger import LoggerPlugin
from .plugins.webapi import WebAPIPlugin
from .plugins.notification import NotificationPlugin
from .plugins.summary import SummaryPlugin
from .processes import (
    ContactQualityProcess,
)
from .sequence import (
    SampleTreeItem,
    ContactTreeItem,
    MeasurementTreeItem,
)
from .utils import make_path
from .settings import settings as config  # TODO

__all__ = ["MainWindow"]

APP_TITLE = "PQC"
APP_COPY = "Copyright &copy; 2020-2023 HEPHY"
APP_LICENSE = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION = """Process Quality Control (PQC) for CMS Tracker."""


class MainWindow(QtWidgets.QMainWindow, ProcessMixin):

    config_version = 1

    def __init__(self, station, parent=None):
        super().__init__(parent)

        self.station = station

        self.setProperty("directory", os.path.expanduser("~"))

        # Actions

        self.importSequenceAction = QtWidgets.QAction(self)
        self.importSequenceAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_import.svg")))
        self.importSequenceAction.setText("Import Sequence...")
        self.importSequenceAction.setStatusTip("Import sequence from JSON file.")
        self.importSequenceAction.triggered.connect(self.importSequence)

        self.exportSequenceAction = QtWidgets.QAction(self)
        self.exportSequenceAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_export.svg")))
        self.exportSequenceAction.setText("Export Sequence...")
        self.exportSequenceAction.setStatusTip("Export sequence to JSON file.")
        self.exportSequenceAction.triggered.connect(self.exportSequence)

        self.quitAction = QtWidgets.QAction(self)
        self.quitAction.setText("&Quit")
        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.triggered.connect(self.close)

        self.preferencesAction = QtWidgets.QAction(self)
        self.preferencesAction.setText("Prefere&nces")
        self.preferencesAction.triggered.connect(self.showPreferences)

        self.startAllAction = QtWidgets.QAction(self)
        self.startAllAction.setText("&All Samples")

        self.startSampleAction = QtWidgets.QAction(self)
        self.startSampleAction.setText("&Sample")

        self.startContactAction = QtWidgets.QAction(self)
        self.startContactAction.setText("&Contact")

        self.startMeasurementAction = QtWidgets.QAction(self)
        self.startMeasurementAction.setText("&Measurement")

        self.stopAction = QtWidgets.QAction(self)
        self.stopAction.setText("Sto&p")

        self.resetAction = QtWidgets.QAction(self)
        self.resetAction.setText("Reset")

        self.editAction = QtWidgets.QAction(self)
        self.editAction.setText("Edit")

        self.reloadConfigAction = QtWidgets.QAction(self)
        self.reloadConfigAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadConfigAction.setText("Reload")
        self.reloadConfigAction.setStatusTip("Reload sequence configurations from file.")

        self.addSampleAction = QtWidgets.QAction(self)
        self.addSampleAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addSampleAction.setText("Add Sample")
        self.addSampleAction.setStatusTip("Add new sample to sequence.")

        self.removeSampleAction = QtWidgets.QAction(self)
        self.removeSampleAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeSampleAction.setText("Remove Sample")
        self.removeSampleAction.setToolTip("Remove current sample sequence.")

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
        self.fileMenu.addAction(self.importSequenceAction)
        self.fileMenu.addAction(self.exportSequenceAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)

        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.preferencesAction)

        self.startMenu = QtWidgets.QMenu()
        self.startMenu.setTitle("&Start")
        self.startMenu.addAction(self.startAllAction)
        self.startMenu.addAction(self.startSampleAction)
        self.startMenu.addAction(self.startContactAction)
        self.startMenu.addAction(self.startMeasurementAction)

        self.sequenceMenu = self.menuBar().addMenu("&Sequence")
        self.sequenceMenu.addMenu(self.startMenu)
        self.sequenceMenu.addAction(self.stopAction)
        self.sequenceMenu.addSeparator()
        self.sequenceMenu.addAction(self.resetAction)
        self.sequenceMenu.addAction(self.editAction)
        self.sequenceMenu.addAction(self.reloadConfigAction)
        self.sequenceMenu.addAction(self.addSampleAction)
        self.sequenceMenu.addAction(self.removeSampleAction)

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

        self.hideMessage()
        self.hideProgress()

        self.processes.add("contact_quality", ContactQualityProcess())

        self.plugins = PluginManager()
        self.plugins.register_plugin(StatusPlugin(self))
        self.plugins.register_plugin(LoggerPlugin(self))
        self.plugins.register_plugin(WebAPIPlugin(self))
        self.plugins.register_plugin(SummaryPlugin(self))
        self.plugins.register_plugin(NotificationPlugin(self))

        self.dashboard = Dashboard(self.station, self.plugins, self)
        self.dashboard.messageChanged.connect(self.showMessage)
        self.dashboard.progressChanged.connect(self.showProgress)
        self.dashboard.failed.connect(self.showException)

        self.setCentralWidget(self.dashboard)

        self.dashboard.sequenceControlWidget.startButton.setMenu(self.startMenu)
        self.dashboard.sequenceControlWidget.stopButton.clicked.connect(self.stopAction.trigger)
        self.dashboard.sequenceControlWidget.resetButton.clicked.connect(self.resetAction.trigger)
        self.dashboard.sequenceControlWidget.editButton.clicked.connect(self.editAction.trigger)
        self.dashboard.sequenceControlWidget.reloadConfigButton.setDefaultAction(self.reloadConfigAction)
        self.dashboard.sequenceControlWidget.addSampleButton.setDefaultAction(self.addSampleAction)
        self.dashboard.sequenceControlWidget.removeSampleButton.setDefaultAction(self.removeSampleAction)
        self.dashboard.sequenceControlWidget.importButton.setDefaultAction(self.importSequenceAction)
        self.dashboard.sequenceControlWidget.exportButton.setDefaultAction(self.exportSequenceAction)

        self.startAllAction.triggered.connect(self.dashboard.on_start_all)
        self.startSampleAction.triggered.connect(self.dashboard.on_start)
        self.startContactAction.triggered.connect(self.dashboard.on_start)
        self.startMeasurementAction.triggered.connect(self.dashboard.on_start)
        self.stopAction.triggered.connect(self.dashboard.on_stop)
        self.resetAction.triggered.connect(self.dashboard.on_reset_sequence_state)
        self.editAction.triggered.connect(self.dashboard.on_edit_sequence)
        self.reloadConfigAction.triggered.connect(self.dashboard.sequenceControlWidget.reloadConfig)
        self.addSampleAction.triggered.connect(self.dashboard.sequenceControlWidget.addSampleItem)
        self.removeSampleAction.triggered.connect(self.dashboard.sequenceControlWidget.removeCurrentSampleItem)

        def updateSequenceActions(current, previous):
            self.startSampleAction.setEnabled(isinstance(current, SampleTreeItem))
            self.startContactAction.setEnabled(isinstance(current, ContactTreeItem))
            self.startMeasurementAction.setEnabled(isinstance(current, MeasurementTreeItem))

        self.dashboard.sequenceTreeWidget.currentItemChanged.connect(updateSequenceActions)

        self.dashboard.setNoticeVisible(config.table_temporary_z_limit)  # TODO

        # Sync environment controls
        if self.dashboard.isEnvironmentEnabled():
            self.station.environ_process.start()
            self.dashboard.sync_environment_controls()

        if self.dashboard.isTableEnabled():
            self.station.table_process.start()
            self.dashboard.syncTableControls()
            self.station.table_process.enable_joystick(False)

        # State machine

        self.idleState = QtCore.QState()
        self.idleState.entered.connect(self.enterIdle)

        self.runningState = QtCore.QState()
        self.runningState.entered.connect(self.enterRunning)

        self.abortingState = QtCore.QState()
        self.abortingState.entered.connect(self.enterAborting)

        self.idleState.addTransition(self.dashboard.started, self.runningState)

        self.runningState.addTransition(self.dashboard.aborting, self.abortingState)
        self.runningState.addTransition(self.dashboard.finished, self.idleState)

        self.abortingState.addTransition(self.dashboard.finished, self.idleState)

        self.stateMachine = QtCore.QStateMachine(self)
        self.stateMachine.addState(self.idleState)
        self.stateMachine.addState(self.runningState)
        self.stateMachine.addState(self.abortingState)
        self.stateMachine.setInitialState(self.idleState)
        self.stateMachine.start()

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        geometry = settings.value("geometry", None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("state", None)
        if state is not None:
            self.restoreState(state)
        self.setProperty("directory", settings.value("directory", os.path.expanduser("~"), str))
        settings.endGroup()
        settings.beginGroup("preferences")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not geometry.isEmpty():
            self.preferencesDialog.restoreGeometry(geometry)
        settings.endGroup()
        self.dashboard.readSettings()

    def writeSettings(self):
        self.dashboard.writeSettings()
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.setValue("directory", self.property("directory"))
        settings.endGroup()
        settings.beginGroup("preferences")
        settings.setValue("geometry", self.preferencesDialog.saveGeometry())
        settings.endGroup()

    def showPreferences(self) -> None:
        """Show modal preferences dialog."""
        self.preferencesDialog.readSettings()
        self.preferencesDialog.exec()
        if self.preferencesDialog.result() == QtWidgets.QDialog.Accepted:
            self.preferencesDialog.writeSettings()
            self.dashboard.setNoticeVisible(config.table_temporary_z_limit)  # TODO

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

    def showException(self, exc: Exception, tb=None) -> None:
        """Raise message box showing exception information."""
        msgbox = MessageBox(self)
        if not tb:
            tb = traceback.format_exc()
        msgbox.setIcon(msgbox.Critical)
        msgbox.setWindowTitle("An exception occured")
        msgbox.setText(format(exc))
        msgbox.setDetailedText(tb)
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

    def importSequence(self) -> None:
        """Import sequence from JSON file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Sequence", self.property("directory"), "JSON (*.json)")
        if filename:
            self.setProperty("directory", os.path.dirname(filename))

            progress = QtWidgets.QProgressDialog(self)
            progress.setLabelText("Reading sequence from JSON...")
            progress.setCancelButton(None)

            def callback(filename=filename):
                try:
                    with open(filename) as fp:
                        logging.info("Reading sequence... %r", filename)
                        data = json.load(fp)
                        logging.info("Reading sequence... done.")
                    self.setProperty("directory", os.path.dirname(filename))
                    version = data.get("version")
                    if version is None:
                        raise RuntimeError(f"Missing version information in sequence: {filename}")
                    elif isinstance(version, int):
                        if version != self.config_version:
                            raise RuntimeError(f"Invalid version in sequence: {filename}")
                    else:
                        raise RuntimeError(f"Invalid version information in sequence: {filename}")
                    samples = data.get("sequence") or []
                    self.dashboard.clearSequence()
                    progress.setMaximum(len(samples))
                    for kwargs in samples:
                        progress.setValue(progress.value() + 1)
                        item = SampleTreeItem()
                        try:
                            item.from_settings(**kwargs)
                        except Exception as exc:
                            logging.error(exc)
                        self.dashboard.addSequenceItem(item)
                        item.setExpanded(False)
                    if self.dashboard.sequenceTreeWidget.topLevelItemCount():
                        self.dashboard.sequenceTreeWidget.setCurrentItem(self.dashboard.sequenceTreeWidget.topLevelItem(0))
                    self.dashboard.sequenceTreeWidget.resizeColumns()
                finally:
                    progress.close()

            QtCore.QTimer.singleShot(200, callback)
            progress.exec()

    def exportSequence(self) -> None:
        """Export sequence to JSON file."""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Sequence", self.property("directory"), "JSON (*.json)")
        if filename:
            self.setProperty("directory", os.path.dirname(filename))

            progress = QtWidgets.QProgressDialog(self)
            progress.setLabelText("Writing sequence to JSON...")
            progress.setMaximum(len(self.dashboard.sequenceItems()))
            progress.setCancelButton(None)

            def callback(filename=filename):
                try:
                    samples = []
                    for item in self.dashboard.sequenceItems():
                        progress.setValue(progress.value() + 1)
                        samples.append(item.to_settings())
                    data = {
                        "version": self.config_version,
                        "sequence": samples
                    }
                    # Auto filename extension
                    if os.path.splitext(filename)[-1] not in [".json"]:
                        filename = f"{filename}.json"
                        if os.path.exists(filename):
                            result = QtWidgets.QMessageBox.question(self, "", f"Do you want to overwrite existing file {filename}?")
                            if result != QtWidgets.QMessageBox.Yes:
                                return
                    with open(filename, "w") as fp:
                        logging.info("Writing sequence... %r", filename)
                        json.dump(data, fp)
                        logging.info("Writing sequence... done.")
                finally:
                    progress.close()

            QtCore.QTimer.singleShot(200, callback)
            progress.exec()

    def shutdown(self) -> None:
        self.dashboard.shutdown()
        self.processes.stop()
        self.processes.join()
        self.station.shutdown()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        result = QtWidgets.QMessageBox.question(self, "Quit", "Quit application?")
        if result == QtWidgets.QMessageBox.Yes:
            self.stateMachine.stop()

            progress = QtWidgets.QProgressDialog(self)
            progress.setLabelText("Stopping active threads...")
            progress.setRange(0, 0)
            progress.setCancelButton(None)

            def callback():
                self.shutdown()
                progress.close()

            QtCore.QTimer.singleShot(200, callback)
            progress.exec()

            event.accept()
        else:
            event.ignore()

    def enterIdle(self) -> None:
        self.preferencesAction.setEnabled(True)
        self.startMenu.setEnabled(True)
        self.stopAction.setEnabled(False)
        self.resetAction.setEnabled(True)
        self.editAction.setEnabled(True)
        self.reloadConfigAction.setEnabled(True)
        self.addSampleAction.setEnabled(True)
        self.removeSampleAction.setEnabled(True)
        self.importSequenceAction.setEnabled(True)
        self.exportSequenceAction.setEnabled(True)
        self.dashboard.setControlsLocked(False)

    def enterRunning(self) -> None:
        self.preferencesAction.setEnabled(False)
        self.startMenu.setEnabled(False)
        self.stopAction.setEnabled(True)
        self.resetAction.setEnabled(False)
        self.editAction.setEnabled(False)
        self.reloadConfigAction.setEnabled(False)
        self.addSampleAction.setEnabled(False)
        self.removeSampleAction.setEnabled(False)
        self.importSequenceAction.setEnabled(False)
        self.exportSequenceAction.setEnabled(False)
        self.dashboard.setControlsLocked(True)

    def enterAborting(self) -> None:
        self.stopAction.setEnabled(False)

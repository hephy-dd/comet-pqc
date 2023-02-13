import logging
import os
import threading
import webbrowser

from PyQt5 import QtCore, QtGui, QtWidgets

from ..settings import settings as _settings
from ..utils import make_path
from .components import ExceptionDialog, showException, showQuestion
from .dashboard import Dashboard
from .preferences import PreferencesDialog
from .sequencemanager import SequenceManagerDialog
from .sequencetreewidget import SampleTreeItem, ContactTreeItem, MeasurementTreeItem
from .worker import Worker

__all__ = ["MainWindow"]

APP_TITLE = "PQC"
APP_COPY = "Copyright &copy; 2020-2023 HEPHY"
APP_LICENSE = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION = """Process Quality Control (PQC) for CMS Tracker."""

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context

        # Hooks

        self.beforePreferences = []
        self.afterPreferences = []

        # Actions

        self.importSequenceAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.importSequenceAction.setText("Import Sequence...")
        self.importSequenceAction.setStatusTip("Import sequence from JSON file.")
        self.importSequenceAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_open.svg")))
        self.importSequenceAction.triggered.connect(self.importSequence)

        self.exportSequenceAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.exportSequenceAction.setText("Export Sequence...")
        self.exportSequenceAction.setStatusTip("Export sequence to JSON file.")
        self.exportSequenceAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_save.svg")))
        self.exportSequenceAction.triggered.connect(self.exportSequence)

        self.quitAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.quitAction.setText("&Quit")
        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.triggered.connect(self.close)

        self.sequenceManagerAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.sequenceManagerAction.setText("&Sequences...")
        self.sequenceManagerAction.triggered.connect(self.showSequenceManager)

        self.preferencesAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.preferencesAction.setText("Prefere&nces")
        self.preferencesAction.triggered.connect(self.showPreferences)

        self.startAllAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startAllAction.setText("&All Samples")

        self.startSampleAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startSampleAction.setText("&Sample")
        self.startSampleAction.setEnabled(False)

        self.startContactAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startContactAction.setText("&Contact")
        self.startContactAction.setEnabled(False)

        self.startMeasurementAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startMeasurementAction.setText("&Measurement")
        self.startMeasurementAction.setEnabled(False)

        self.abortAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.abortAction.setText("&Stop")
        self.abortAction.setEnabled(False)

        self.alignmentAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.alignmentAction.setIcon(QtGui.QIcon(make_path("assets", "icons", "alignment.svg")))
        self.alignmentAction.setText("&Alignment...")
        self.alignmentAction.triggered.connect(self.showAlignment)

        self.contentsAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.contentsAction.setText("&Contents")
        self.contentsAction.setShortcut("F1")
        self.contentsAction.triggered.connect(self.showContents)

        self.githubAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.githubAction.setText("&GitHub")
        self.githubAction.triggered.connect(self.showGithub)

        self.aboutQtAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.aboutQtAction.setText("About Qt")
        self.aboutQtAction.triggered.connect(self.showAboutQt)

        self.aboutAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.aboutAction.setText("&About")
        self.aboutAction.triggered.connect(self.showAbout)

        # Menus

        self.fileMenu: QtWidgets.QMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.importSequenceAction)
        self.fileMenu.addAction(self.exportSequenceAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)

        self.editMenu: QtWidgets.QMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.sequenceManagerAction)
        self.editMenu.addAction(self.preferencesAction)

        self.startMenu: QtWidgets.QMenu = QtWidgets.QMenu("&Start")
        self.startMenu.addAction(self.startAllAction)
        self.startMenu.addAction(self.startSampleAction)
        self.startMenu.addAction(self.startContactAction)
        self.startMenu.addAction(self.startMeasurementAction)

        self.sequenceMenu: QtWidgets.QMenu = self.menuBar().addMenu("&Sequence")
        self.sequenceMenu.addMenu(self.startMenu)
        self.sequenceMenu.addAction(self.abortAction)
        self.sequenceMenu.addSeparator()
        self.sequenceMenu.addAction(self.alignmentAction)

        self.helpMenu: QtWidgets.QMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.contentsAction)
        self.helpMenu.addAction(self.githubAction)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.aboutQtAction)
        self.helpMenu.addAction(self.aboutAction)

        # Dashboard

        self.dashboard: Dashboard = Dashboard(self.context)
        self.dashboard.lockedStateChanged.connect(self.setLocked)
        self.context.environ_process.pc_data_updated = self.dashboard.setEnvironmentData
        self.setCentralWidget(self.dashboard)

        def updateActions(item):
            self.startAllAction.setEnabled(True)
            self.startSampleAction.setEnabled(isinstance(item, SampleTreeItem))
            self.startContactAction.setEnabled(isinstance(item, ContactTreeItem))
            self.startMeasurementAction.setEnabled(isinstance(item, MeasurementTreeItem))

        self.dashboard.currentItemChanged.connect(updateActions)
        self.dashboard.itemTriggered.connect(self.dashboard.startCurrent)

        self.dashboard.sequence_widget.startButton.setMenu(self.startMenu)
        self.dashboard.sequence_widget.stopButton.clicked.connect(self.abortAction.trigger)

        self.startAllAction.triggered.connect(self.dashboard.startAll)
        self.startSampleAction.triggered.connect(self.dashboard.startCurrent)
        self.startContactAction.triggered.connect(self.dashboard.startCurrent)
        self.startMeasurementAction.triggered.connect(self.dashboard.startCurrent)

        # Status bar

        self.messageLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.statusBar().addPermanentWidget(self.messageLabel)

        self.progressBar:QtWidgets.QProgressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setFixedWidth(600)
        self.statusBar().addPermanentWidget(self.progressBar)

        # State Machine

        self.idleState: QtCore.QState = QtCore.QState()
        self.idleState.entered.connect(self.enterIdleState)

        self.runningState: QtCore.QState = QtCore.QState()
        self.runningState.entered.connect(self.enterRunningState)

        self.abortingState: QtCore.QState = QtCore.QState()
        self.abortingState.entered.connect(self.enterAbortingState)

        self.idleState.addTransition(self.dashboard.sequenceStarted, self.runningState)

        self.runningState.addTransition(self.dashboard.finished, self.idleState)
        self.runningState.addTransition(self.abortAction.triggered, self.abortingState)

        self.abortingState.addTransition(self.dashboard.finished, self.idleState)

        self.stateMachine: QtCore.QStateMachine = QtCore.QStateMachine(self)
        self.stateMachine.addState(self.idleState)
        self.stateMachine.addState(self.runningState)
        self.stateMachine.addState(self.abortingState)
        self.stateMachine.setInitialState(self.idleState)
        self.stateMachine.start()

    def readSettings(self) -> None:
        self.dashboard.setNoticeVisible(_settings.table_temporary_z_limit())
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        state = settings.value("state", QtCore.QByteArray(), QtCore.QByteArray)
        settings.endGroup()
        if not self.restoreGeometry(geometry):
            self.resize(800, 600)
        self.restoreState(state)
        self.dashboard.readSettings()

    def writeSettings(self) -> None:
        geometry = self.saveGeometry()
        state = self.saveState()
        settings = QtCore.QSettings()
        settings.beginGroup("mainwindow")
        settings.setValue("geometry", geometry)
        settings.setValue("state", state)
        settings.endGroup()
        self.dashboard.writeSettings()

    def setLocked(self, state: bool) -> None:
        self.importSequenceAction.setEnabled(not state)
        self.exportSequenceAction.setEnabled(not state)
        self.sequenceManagerAction.setEnabled(not state)
        self.preferencesAction.setEnabled(not state)
        self.alignmentAction.setEnabled(not state)

    @QtCore.pyqtSlot()
    def enterIdleState(self) -> None:
        logging.warning("ENTER IDLE")
        self.setLocked(False)
        self.dashboard.setLocked(False)
        self.dashboard.measurementWidget.setLocked(False)
        self.dashboard.sequence_widget.stopButton.setEnabled(False)
        self.startMenu.setEnabled(True)
        self.abortAction.setEnabled(False)

    @QtCore.pyqtSlot()
    def enterRunningState(self) -> None:
        logging.warning("ENTER RUNNING")
        self.setLocked(True)
        self.dashboard.setLocked(True)
        self.dashboard.measurementWidget.setLocked(True)
        self.dashboard.sequence_widget.stopButton.setEnabled(True)
        self.startMenu.setEnabled(False)
        self.abortAction.setEnabled(True)

    @QtCore.pyqtSlot()
    def enterAbortingState(self) -> None:
        logging.warning("ENTER ABORT")
        self.dashboard.sequence_widget.stopButton.setEnabled(False)
        self.abortAction.setEnabled(False)
        self.dashboard.stopSequence()

    @QtCore.pyqtSlot()
    def showSequenceManager(self) -> None:
        dialog = SequenceManagerDialog(self)
        dialog.readSettings()
        dialog.readSequences()
        if dialog.exec() == dialog.Accepted:
            dialog.writeSequences()
        dialog.writeSettings()

    @QtCore.pyqtSlot()
    def showPreferences(self) -> None:
        """Show modal preferences dialog."""
        dialog = PreferencesDialog(self)
        dialog.readSettings()
        for callback in self.beforePreferences:
            callback(dialog)
        dialog.exec()
        for callback in self.afterPreferences:
            callback(dialog)
        dialog.writeSettings()

        # Update state
        self.dashboard.setNoticeVisible(_settings.table_temporary_z_limit())

    @QtCore.pyqtSlot()
    def showAlignment(self) -> None:
        self.dashboard.showAlignmentDialog()

    @QtCore.pyqtSlot()
    def showContents(self) -> None:
        """Open local webbrowser with contents URL."""
        instance = QtWidgets.QApplication.instance()  # TODO
        if isinstance(instance, QtWidgets.QApplication):
            contents_url = instance.property("contentsUrl")
            if isinstance(contents_url, str):
                webbrowser.open(contents_url)

    @QtCore.pyqtSlot()
    def showGithub(self) -> None:
        """Open local webbrowser with GitHub URL."""
        instance = QtWidgets.QApplication.instance()  # TODO
        if isinstance(instance, QtWidgets.QApplication):
            github_url = instance.property("githubUrl")
            if isinstance(github_url, str):
                webbrowser.open(github_url)

    @QtCore.pyqtSlot()
    def showAboutQt(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    @QtCore.pyqtSlot()
    def showAbout(self) -> None:
        version = QtWidgets.QApplication.applicationVersion()
        QtWidgets.QMessageBox.about(self, "About", f"<h1>{APP_TITLE}</h1><p>Version {version}</p><p>{APP_DECRIPTION}</p><p>{APP_COPY}</p><p>{APP_LICENSE}</p>")

    @QtCore.pyqtSlot(str)
    def showMessage(self, message: str) -> None:
        """Show status message."""
        self.messageLabel.setText(message)
        self.messageLabel.show()

    @QtCore.pyqtSlot()
    def hideMessage(self) -> None:
        """Hide status message."""
        self.messageLabel.clear()
        self.messageLabel.hide()

    @QtCore.pyqtSlot(int, int)
    def showProgress(self, value: int, maximum: int) -> None:
        """Show progress bar."""
        self.progressBar.setRange(0, maximum)
        self.progressBar.setValue(value)
        self.progressBar.show()

    @QtCore.pyqtSlot()
    def hideProgress(self) -> None:
        """Hide progress bar."""
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)
        self.progressBar.hide()

    def showException(self, exc: Exception, tb=None) -> None:
        """Raise message box showing exception information."""
        self.showMessage("Error")
        self.hideProgress()
        showException(exc)

    def shutdown(self) -> None:
        self.stateMachine.stop()
        dialog = QtWidgets.QProgressDialog(self)
        dialog.setRange(0, 0)
        dialog.setValue(0)
        dialog.setCancelButton(None)
        dialog.setLabelText("Stopping active threads...")
        worker = Worker(self.context.shutdown)
        worker.finished.connect(dialog.close)
        thread = threading.Timer(.250, worker)
        thread.start()
        dialog.exec()
        thread.join()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        if showQuestion(text="Quit application?"):
            self.shutdown()
            event.accept()
        else:
            event.ignore()

    # Slots

    @QtCore.pyqtSlot()
    def importSequence(self) -> None:
        try:
            directory = _settings.value("sequence_default_path", os.path.expanduser("~"), str)
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                parent=self,
                caption="Import Sequence",
                directory=directory,
                filter="JSON (*.json)",
            )
            if filename:
                _settings.setValue("sequence_default_path", os.path.dirname(filename))
                self.dashboard.readSequence(filename)
        except Exception as exc:
            logger.exception(exc)
            showException(exc)

    @QtCore.pyqtSlot()
    def exportSequence(self) -> None:
        try:
            directory = _settings.value("sequence_default_path", os.path.expanduser("~"), str)
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption="Export Sequence",
                directory=directory,
                filter="JSON (*.json)",
            )
            if filename:
                _settings.setValue("sequence_default_path", os.path.dirname(filename))
                if not filename.endswith(".json"):
                    filename = f"{filename}.json"
                self.dashboard.writeSequence(filename)
        except Exception as exc:
            logger.exception(exc)
            showException(exc)

import json
import logging
import math
import os
import time
import webbrowser
from typing import List, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets

import comet
from comet.process import ProcessMixin
from comet.settings import SettingsMixin

from .components import (
    CalibrationWidget,
    OperatorWidget,
    PositionWidget,
    ToggleButton,
    WorkingDirectoryWidget,
)
from .core import config
from .core.position import Position
from .core.formatter import CSVFormatter
from .core.utils import make_path, user_home
from .sequence import (
    ContactTreeItem,
    EditSamplesDialog,
    MeasurementTreeItem,
    SamplesItem,
    SampleTreeItem,
    SequenceTree,
    StartSequenceDialog,
    load_all_sequences,
)
from .settings import settings
from .tablecontrol import TableControlDialog, safe_z_position
from .tabs.measurement import MeasurementWidget
from .tabs.environment import EnvironmentWidget
from .tabs.summary import SummaryWidget
from .tabs.loggingwidget import LoggingWidget
from .tabs.status import StatusWidget
from .utils import caldone_valid, handle_exception

logger = logging.getLogger(__name__)

SUMMARY_FILENAME = "summary.csv"


class SequenceWidget(QtWidgets.QGroupBox, SettingsMixin):

    ConfigVersion: int = 1

    treeSelected: QtCore.pyqtSignal = QtCore.pyqtSignal(object)
    treeDoubleClicked: QtCore.pyqtSignal = QtCore.pyqtSignal(object, int)
    startAllClicked: QtCore.pyqtSignal = QtCore.pyqtSignal()
    startClicked: QtCore.pyqtSignal = QtCore.pyqtSignal()
    stopClicked: QtCore.pyqtSignal = QtCore.pyqtSignal()
    resetSequenceState: QtCore.pyqtSignal = QtCore.pyqtSignal()
    editSequenceClicked: QtCore.pyqtSignal = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setProperty("currentPath", user_home())
        self.setTitle("Sequence")

        self._sequence_tree = SequenceTree(
            selected=self.treeSelected.emit,
            double_clicked=self.handleDoubleClick
        )
        self._sequence_tree.qt.setMinimumWidth(360)

        self.startAllAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startAllAction.setText("&All Samples")
        self.startAllAction.triggered.connect(self.startAllClicked.emit)

        self.startSampleAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startSampleAction.setText("&Sample")
        self.startSampleAction.setEnabled(False)
        self.startSampleAction.triggered.connect(self.startClicked.emit)

        self.startContactAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startContactAction.setText("&Contact")
        self.startContactAction.setEnabled(False)
        self.startContactAction.triggered.connect(self.startClicked.emit)

        self.startMeasurementAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startMeasurementAction.setText("&Measurement")
        self.startMeasurementAction.setEnabled(False)
        self.startMeasurementAction.triggered.connect(self.startClicked.emit)

        self.startMenu: QtWidgets.QMenu = QtWidgets.QMenu(self)
        self.startMenu.addAction(self.startAllAction)
        self.startMenu.addAction(self.startSampleAction)
        self.startMenu.addAction(self.startContactAction)
        self.startMenu.addAction(self.startMeasurementAction)

        self.startButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setStatusTip("Start measurement sequence.")
        self.startButton.setStyleSheet("QPushButton:enabled{color:green;font-weight:bold;}")
        self.startButton.setMenu(self.startMenu)

        self.stopButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("Stop")
        self.stopButton.setStatusTip("Stop measurement sequence.")
        self.stopButton.setEnabled(False)
        self.stopButton.setStyleSheet("QPushButton:enabled{color:red;font-weight:bold;}")
        self.stopButton.clicked.connect(self.stopClicked.emit)

        self.resetButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("Reset")
        self.resetButton.setStatusTip("Reset measurement sequence state.")
        self.resetButton.clicked.connect(self.resetSequenceState.emit)

        self.editButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editButton.setText("Edit")
        self.editButton.setStatusTip("Quick edit properties of sequence items.")
        self.editButton.clicked.connect(self.editSequenceClicked.emit)

        self.reloadConfigButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadConfigButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadConfigButton.setStatusTip("Reload sequence configurations from file.")
        self.reloadConfigButton.clicked.connect(self.on_reload_config_clicked)

        self.addSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.addSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addSampleButton.setStatusTip("Add new sample sequence.")
        self.addSampleButton.clicked.connect(self.on_add_sample_clicked)

        self.removeSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.removeSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeSampleButton.setStatusTip("Remove current sample sequence.")
        self.removeSampleButton.clicked.connect(self.on_remove_sample_clicked)

        self.openButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.openButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_open.svg")))
        self.openButton.setStatusTip("Open sequence tree from file.")
        self.openButton.clicked.connect(self.on_open_clicked)

        self.saveButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.saveButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_save.svg")))
        self.saveButton.setStatusTip("Save sequence tree to file.")
        self.saveButton.clicked.connect(self.on_save_clicked)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addWidget(self.startButton)
        bottomLayout.addWidget(self.stopButton)
        bottomLayout.addWidget(self.resetButton)
        bottomLayout.addWidget(self.editButton)
        bottomLayout.addWidget(self.reloadConfigButton)
        bottomLayout.addWidget(self.addSampleButton)
        bottomLayout.addWidget(self.removeSampleButton)
        bottomLayout.addWidget(self.openButton)
        bottomLayout.addWidget(self.saveButton)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._sequence_tree.qt)
        layout.addLayout(bottomLayout)

    def readSettings(self) -> None:
        samples = self.settings.get("sequence_samples") or []
        self._sequence_tree.clear()
        for kwargs in samples:
            item = SampleTreeItem()
            self._sequence_tree.append(item)
            item.expanded = False # do not expand
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logger.error(exc)
        if len(self._sequence_tree):
            self._sequence_tree.current = self._sequence_tree[0]
        self._sequence_tree.fit()
        self.setProperty("currentPath", self.settings.get("sequence_default_path") or user_home())

    def writeSettings(self) -> None:
        sequence_samples = [sample.to_settings() for sample in self._sequence_tree]
        self.settings["sequence_samples"] = sequence_samples
        self.settings["sequence_default_path"] = self.property("currentPath")

    def handleDoubleClick(self, item, column):
        if not self.property("locked"):
            self.treeDoubleClicked.emit(item, column)

    def lock(self):
        self.setProperty("locked", True)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.resetButton.setEnabled(False)
        self.editButton.setEnabled(False)
        self.reloadConfigButton.setEnabled(False)
        self.addSampleButton.setEnabled(False)
        self.removeSampleButton.setEnabled(False)
        self.saveButton.setEnabled(False)
        self.openButton.setEnabled(False)
        self._sequence_tree.setLocked(True)

    def unlock(self):
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.resetButton.setEnabled(True)
        self.editButton.setEnabled(True)
        self.reloadConfigButton.setEnabled(True)
        self.addSampleButton.setEnabled(True)
        self.removeSampleButton.setEnabled(True)
        self.saveButton.setEnabled(True)
        self.openButton.setEnabled(True)
        self._sequence_tree.setLocked(False)
        self.setProperty("locked", False)

    def stop(self):
        self.stopButton.setEnabled(False)

    @handle_exception
    def on_reload_config_clicked(self, state):
        result = QtWidgets.QMessageBox.question(
            self,
            "Reload Configuration",
            "Do you want to reload sequence configurations from file?"
        )
        if result == QtWidgets.QMessageBox.Yes:
            for sample_item in self._sequence_tree:
                if sample_item.sequence:
                    filename = sample_item.sequence.filename
                    sequence = config.load_sequence(filename)
                    sample_item.load_sequence(sequence)

    @handle_exception
    def on_add_sample_clicked(self, state):
        item = SampleTreeItem(
            name_prefix="",
            name_infix="Unnamed",
            name_suffix="",
            sample_type="",
            enabled=False
        )
        self._sequence_tree.append(item)
        self._sequence_tree.fit()
        self._sequence_tree.current = item

    @handle_exception
    def on_remove_sample_clicked(self, state):
        item = self._sequence_tree.current
        if item in self._sequence_tree:
            result = QtWidgets.QMessageBox.question(
                self,
                "Remove Sample",
                f"Do you want to remove {item.name!r}?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                self._sequence_tree.remove(item)

    @handle_exception
    def on_open_clicked(self, state):
        filename, result = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption="Open JSON",
            directory=self.property("currentPath"),
            filter="JSON (*.json)"
        )
        if result:
            with open(filename) as f:
                logger.info("Reading sequence... %s", filename)
                data = json.load(f)
                logger.info("Reading sequence... done.")
            self.setProperty("currentPath", os.path.dirname(filename))
            version = data.get("version")
            if version is None:
                raise RuntimeError(f"Missing version information in sequence: {filename}")
            elif isinstance(version, int):
                if version != type(self).ConfigVersion:
                    raise RuntimeError(f"Invalid version in sequence: {filename}")
            else:
                raise RuntimeError(f"Invalid version information in sequence: {filename}")
            samples = data.get("sequence") or []
            self._sequence_tree.clear()
            for kwargs in samples:
                item = SampleTreeItem()
                self._sequence_tree.append(item)
                item.expanded = False # do not expand
                try:
                    item.from_settings(**kwargs)
                except Exception as exc:
                    logger.error(exc)
            if len(self._sequence_tree):
                self._sequence_tree.current = self._sequence_tree[0]
            self._sequence_tree.fit()

    @handle_exception
    def on_save_clicked(self, state):
        filename, result = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Save JSON",
            directory=self.property("currentPath"),
            filter="JSON (*.json)"
        )
        if filename:
            samples = [sample.to_settings() for sample in self._sequence_tree]
            data = {
                "version": type(self).ConfigVersion,
                "sequence": samples
            }
            # Auto filename extension
            if os.path.splitext(filename)[-1] not in [".json"]:
                filename = f"{filename}.json"
            with open(filename, "w") as f:
                logger.info("Writing sequence... %s", filename)
                json.dump(data, f)
                logger.info("Writing sequence... done.")
            self.setProperty("currentPath", os.path.dirname(filename))


class TableControlWidget(QtWidgets.QGroupBox, comet.SettingsMixin):

    joystickToggled = QtCore.pyqtSignal(bool)
    controlClicked = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._joystick_limits: Tuple[float, float, float] = (0, 0, 0)
        self._calibration_valid: bool = False

        self.setTitle("Table")
        self.setCheckable(True)

        self.joystickButton = ToggleButton("Joystick", self)
        self.joystickButton.setStatusTip("Toggle table joystick")
        self.joystickButton.toggled.connect(self.joystickToggled.emit)

        self.positionWidget: PositionWidget = PositionWidget(self)

        self.calibrationWidget: CalibrationWidget = CalibrationWidget(self)

        self.controlButton = QtWidgets.QPushButton(self)
        self.controlButton.setText("Control...")
        self.controlButton.setStatusTip("Toggle table joystick")
        self.controlButton.clicked.connect(self.controlClicked.emit)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionWidget, 0, 0, 4, 1)
        layout.addWidget(self.calibrationWidget, 0, 1, 4, 1)
        layout.addWidget(self.controlButton, 1, 3)
        layout.addWidget(self.joystickButton, 2, 3)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(3, 1)

    def isCalibrationValid(self) -> bool:
        return self._calibration_valid

    def setJoystickState(self, state: bool) -> None:
        with QtCore.QSignalBlocker(self.joystickButton):
            self.joystickButton.setChecked(state)

    def updatePosition(self, position: Position) -> None:
        self.positionWidget.updatePosition(position)
        limits = self._joystick_limits
        enabled = position.x <= limits[0] and position.y <= limits[1] and position.z <= limits[2]
        self.joystickButton.setEnabled(enabled and self.isCalibrationValid())

    def update_calibration(self, position) -> None:
        self.calibrationWidget.updateCalibration(position)
        self._calibration_valid = caldone_valid(position)

    def readSettings(self) -> None:
        use_table = self.settings.get("use_table") or False
        self.setChecked(use_table)
        self._joystick_limits = settings.tableJoystickMaximumLimits()


class EnvironGroupBox(QtWidgets.QGroupBox):

    laserSensorToggled = QtCore.pyqtSignal(bool)
    boxLightToggled = QtCore.pyqtSignal(bool)
    microscopeLightToggled = QtCore.pyqtSignal(bool)
    microscopeCameraToggled = QtCore.pyqtSignal(bool)
    microscopeControlToggled = QtCore.pyqtSignal(bool)
    probecardLightToggled = QtCore.pyqtSignal(bool)
    probecard_camera_toggled = QtCore.pyqtSignal(bool)
    pidControlToggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setTitle("Environment Box")
        self.setCheckable(True)

        self.laserSensorButton = ToggleButton("Laser", self)
        self.laserSensorButton.setStatusTip("Toggle laser")
        self.laserSensorButton.toggled.connect(self.laserSensorToggled.emit)

        self.boxLightButton = ToggleButton("Box Light", self)
        self.boxLightButton.setStatusTip("Toggle box light")
        self.boxLightButton.toggled.connect(self.boxLightToggled.emit)

        self.microscopeLightButton = ToggleButton("Mic Light", self)
        self.microscopeLightButton.setStatusTip("Toggle microscope light")
        self.microscopeLightButton.toggled.connect(self.microscopeLightToggled.emit)

        self.microscopeCameraButton = ToggleButton("Mic Cam", self)
        self.microscopeCameraButton.setStatusTip("Toggle microscope camera power")
        self.microscopeCameraButton.toggled.connect(self.microscopeCameraToggled.emit)

        self.microscopeControlButton = ToggleButton("Mic Ctrl", self)
        self.microscopeControlButton.setStatusTip("Toggle microscope control")
        self.microscopeControlButton.toggled.connect(self.microscopeControlToggled.emit)

        self.probecardLightButton = ToggleButton("PC Light", self)
        self.probecardLightButton.setStatusTip("Toggle probe card light")
        self.probecardLightButton.toggled.connect(self.probecardLightToggled.emit)

        self.probecardCameraButton = ToggleButton("PC Cam", self)
        self.probecardCameraButton.setStatusTip("Toggle probe card camera power")
        self.probecardCameraButton.toggled.connect(self.probecard_camera_toggled.emit)

        self.pidControlButton = ToggleButton("PID Control", self)
        self.pidControlButton.setStatusTip("Toggle PID control")
        self.pidControlButton.toggled.connect(self.pidControlToggled.emit)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.laserSensorButton, 0, 0)
        layout.addWidget(self.microscopeCameraButton, 1, 0)
        layout.addWidget(self.boxLightButton, 0, 1)
        layout.addWidget(self.probecardCameraButton, 1, 1)
        layout.addWidget(self.microscopeLightButton, 0, 2)
        layout.addWidget(self.microscopeControlButton, 1, 2)
        layout.addWidget(self.probecardLightButton, 0, 3)
        layout.addWidget(self.pidControlButton, 1, 3)

    def setLaserSensorState(self, state: bool) -> None:
        self.laserSensorButton.setChecked(state)

    def setBoxLightState(self, state: bool) -> None:
        self.boxLightButton.setChecked(state)

    def setMicroscopeLightState(self, state: bool) -> None:
        self.microscopeLightButton.setChecked(state)

    def setMicroscopeCameraState(self, state: bool) -> None:
        self.microscopeCameraButton.setChecked(state)

    def setMicroscopeControlState(self, state: bool) -> None:
        self.microscopeControlButton.setChecked(state)

    def setProbecardLightState(self, state: bool) -> None:
        self.probecardLightButton.setChecked(state)

    def setProbecardCameraState(self, state: bool) -> None:
        self.probecardCameraButton.setChecked(state)

    def setPidControlState(self, state: bool) -> None:
        self.pidControlButton.setChecked(state)


class Dashboard(QtWidgets.QWidget, ProcessMixin, SettingsMixin):

    sample_count = 4

    messageChanged = QtCore.pyqtSignal(str)
    progressChanged = QtCore.pyqtSignal(int, int)

    started: QtCore.pyqtSignal = QtCore.pyqtSignal()
    stopping: QtCore.pyqtSignal = QtCore.pyqtSignal()
    finished: QtCore.pyqtSignal = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        # Layout
        self.sequence_widget = SequenceWidget(self)
        self.sequence_widget.treeSelected.connect(self.on_tree_selected)
        self.sequence_widget.treeDoubleClicked.connect(self.on_tree_double_clicked)
        self.sequence_widget.startAllClicked.connect(self.on_start_all)
        self.sequence_widget.startClicked.connect(self.on_start)
        self.sequence_widget.stopClicked.connect(self.on_stop)
        self.sequence_widget.resetSequenceState.connect(self.on_reset_sequence_state)
        self.sequence_widget.editSequenceClicked.connect(self.on_edit_sequence)

        self.sequence_tree = self.sequence_widget._sequence_tree
        self.startSampleAction = self.sequence_widget.startSampleAction
        self.startContactAction = self.sequence_widget.startContactAction
        self.startMeasurementAction = self.sequence_widget.startMeasurementAction

        # Environment Controls

        self.environGroupBox = EnvironGroupBox(self)
        self.environGroupBox.toggled.connect(self.on_environment_groupbox_toggled)
        self.environGroupBox.laserSensorToggled.connect(self.on_laser_sensor_toggled)
        self.environGroupBox.boxLightToggled.connect(self.on_box_light_toggled)
        self.environGroupBox.microscopeLightToggled.connect(self.on_microscope_light_toggled)
        self.environGroupBox.microscopeCameraToggled.connect(self.on_microscope_camera_toggled)
        self.environGroupBox.microscopeControlToggled.connect(self.on_microscope_control_toggled)
        self.environGroupBox.probecardLightToggled.connect(self.on_probecard_light_toggled)
        self.environGroupBox.probecard_camera_toggled.connect(self.on_probecard_camera_toggled)
        self.environGroupBox.pidControlToggled.connect(self.on_pid_control_toggled)

        # Table controls

        self.tableControlWidget = TableControlWidget(self)
        self.tableControlWidget.toggled.connect(self.on_table_groupbox_toggled)
        self.tableControlWidget.joystickToggled.connect(self.on_table_joystick_toggled)
        self.tableControlWidget.controlClicked.connect(self.on_table_control_clicked)

        # Operator

        self.operator_widget = OperatorWidget()
        self.operator_widget.readSettings()

        self.operatorGroupBox = QtWidgets.QGroupBox(self)
        self.operatorGroupBox.setTitle("Operator")

        operatorLayout = QtWidgets.QVBoxLayout(self.operatorGroupBox)
        operatorLayout.addWidget(self.operator_widget.qt)

        # Working directory

        self.output_widget = WorkingDirectoryWidget()

        self.outputGroupBox = QtWidgets.QGroupBox(self)
        self.outputGroupBox.setTitle("Output Directory")

        outputLayout = QtWidgets.QVBoxLayout(self.outputGroupBox)
        outputLayout.addWidget(self.output_widget.qt)

        # Controls

        self.controlWidget = QtWidgets.QWidget(self)

        # Tabs

        self.measurementWidget = MeasurementWidget(self)
        self.measurementWidget.restore.connect(self.on_measure_restore)

        self.environmentWidget = EnvironmentWidget(self)

        self.statusWidget = StatusWidget(self)
        self.statusWidget.reload.connect(self.on_status_start)

        self.summaryWidget = SummaryWidget(self)

        self.panels = self.measurementWidget.panels
        self.panels.sampleChanged.connect(self.on_sample_changed)

        # Logging

        self.loggingWidget = LoggingWidget(self)
        self.loggingWidget.addLogger(logging.getLogger())

        # Tabs

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.measurementWidget, "Measurement")
        self.tabWidget.addTab(self.environmentWidget, "Environment")
        self.tabWidget.addTab(self.statusWidget, "Status")
        self.tabWidget.addTab(self.loggingWidget, "Logging")
        self.tabWidget.addTab(self.summaryWidget, "Summary")

        # Layout

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.controlWidget)
        self.splitter.addWidget(self.tabWidget)
        self.splitter.setSizes([4, 9])

        controlBottomLayout = QtWidgets.QHBoxLayout()
        controlBottomLayout.addWidget(self.operatorGroupBox, 3)
        controlBottomLayout.addWidget(self.outputGroupBox, 7)

        controlLayout = QtWidgets.QVBoxLayout(self.controlWidget)
        controlLayout.setContentsMargins(0, 0, 8, 0)
        controlLayout.addWidget(self.sequence_widget, 1)
        controlLayout.addWidget(self.tableControlWidget)
        controlLayout.addWidget(self.environGroupBox)
        controlLayout.addLayout(controlBottomLayout)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.splitter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Setup process callbacks

        self.environ_process = self.processes.get("environ")
        self.environ_process.pc_data_updated = self.on_pc_data_updated

        self.status_process = self.processes.get("status")
        self.status_process.finished = self.on_status_finished

        self.table_process = self.processes.get("table")
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed

        self.measure_process = self.processes.get("measure")
        self.measure_process.finished = self.on_finished
        self.measure_process.measurement_state = self.on_measurement_state
        self.measure_process.measurement_reset = self.on_measurement_reset
        self.measure_process.save_to_image = self.saveToImage

        self.contact_quality_process = self.processes.get("contact_quality")

    def readSettings(self):
        sizes = self.settings.get("dashboard_sizes") or (300, 500)
        self.splitter.setSizes(sizes)
        self.sequence_widget.readSettings()
        use_environ = self.settings.get("use_environ", False)
        self.environGroupBox.setChecked(use_environ)
        self.tableControlWidget.readSettings()
        self.operator_widget.readSettings()
        self.output_widget.readSettings()

    def writeSettings(self):
        self.settings["dashboard_sizes"] = self.splitter.sizes()
        self.sequence_widget.writeSettings()
        self.settings["use_environ"] = self.use_environment()
        self.settings["use_table"] = self.use_table()
        self.operator_widget.writeSettings()
        self.output_widget.writeSettings()

    def sample_name(self):
        """Return sample name."""
        item = self.sequence_tree.current
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.name
        if isinstance(item, ContactTreeItem):
            return item.sample.name
        if isinstance(item, SampleTreeItem):
            return item.name
        return ""

    def sample_type(self):
        """Return sample type."""
        item = self.sequence_tree.current
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.sample_type
        if isinstance(item, ContactTreeItem):
            return item.sample.sample_type
        if isinstance(item, SampleTreeItem):
            return item.sample_type
        return ""

    def table_position(self):
        """Return table position in millimeters as tuple. If table not available
        return (0., 0., 0.).
        """
        if self.use_table():
            return self.table_process.get_cached_position()
        return Position()

    def use_environment(self):
        """Return True if environment box enabled."""
        return self.environGroupBox.isChecked()

    def use_table(self):
        """Return True if table control enabled."""
        return self.tableControlWidget.isChecked()

    def operator(self):
        """Return current operator."""
        return self.operator_widget.operator_combo_box.qt.currentText().strip()

    def output_dir(self):
        """Return output base path."""
        return os.path.realpath(self.output_widget.currentLocation())

    def create_output_dir(self):
        """Create output directory for sample if not exists, return directory
        path.
        """
        output_dir = self.output_dir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    # Callbacks

    def lock_controls(self):
        """Lock dashboard controls."""
        self.environGroupBox.setEnabled(False)
        self.tableControlWidget.setEnabled(False)
        self.sequence_widget.lock()
        self.outputGroupBox.setEnabled(False)
        self.operatorGroupBox.setEnabled(False)
        self.measurementWidget.setLocked(True)
        self.statusWidget.setLocked(True)

    def unlock_controls(self):
        """Unlock dashboard controls."""
        self.environGroupBox.setEnabled(True)
        self.tableControlWidget.setEnabled(True)
        self.sequence_widget.unlock()
        self.outputGroupBox.setEnabled(True)
        self.operatorGroupBox.setEnabled(True)
        self.measurementWidget.setLocked(False)
        self.statusWidget.setLocked(False)

    # Sequence control

    def on_tree_selected(self, item):
        self.panels.store()
        self.panels.unmount()
        self.panels.clearReadings()
        self.panels.hide()
        self.measurementWidget.controlsLayout.setVisible(False)
        self.startSampleAction.setEnabled(False)
        self.startContactAction.setEnabled(False)
        self.startMeasurementAction.setEnabled(False)
        if isinstance(item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.setVisible(True)
            panel.mount(item)
            self.startSampleAction.setEnabled(True)
        if isinstance(item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.setVisible(True)
            panel.moveRequested.connect(self.on_table_contact)
            panel.contactRequested.connect(self.on_table_move)
            panel.mount(item)
            self.startContactAction.setEnabled(True)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            if panel:
                panel.setVisible(True)
                panel.mount(item)
                self.measurementWidget.controlsLayout.setVisible(True)
                self.startMeasurementAction.setEnabled(True)
        # Show measurement tab
        index = self.tabWidget.indexOf(self.measurementWidget)
        self.tabWidget.setCurrentIndex(index)

    def on_tree_double_clicked(self, item, column):
        self.on_start()

    def on_sample_changed(self, item):
        self.sequence_tree.fit()

    # Contcat table controls

    @handle_exception
    def on_table_move(self, contact):
        if self.use_table():
            self.lock_controls()
            x, y, z = contact.position
            self.table_process.message_changed = lambda message: self.messageChanged.emit(message)
            self.table_process.progress_changed = lambda a, b: self.progressChanged.emit(a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def on_table_contact(self, contact):
        if self.use_table():
            self.lock_controls()
            x, y, z = contact.position
            z = safe_z_position(z)
            self.table_process.message_changed = lambda message: self.messageChanged.emit(message)
            self.table_process.progress_changed = lambda a, b: self.progressChanged.emit(a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    def on_table_finished(self):
        self.table_process.absolute_move_finished = None
        current_item = self.sequence_tree.current
        if isinstance(current_item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.setVisible(True)
            panel.mount(current_item)
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.setVisible(True)
            panel.mount(current_item)
        self.unlock_controls()

    @handle_exception
    def on_start_all(self):
        sample_items = SamplesItem(self.sequence_tree)
        dialog = StartSequenceDialog(
            context=sample_items,
            table_enabled=self.use_table()
        )
        self.operator_widget.writeSettings()
        self.output_widget.writeSettings()
        dialog.readSettings()
        dialog.exec()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            dialog.writeSettings()
            self.operator_widget.readSettings()
            self.output_widget.readSettings()
            self._on_start(
                sample_items,
                move_to_contact=dialog.isMoveToContact(),
                move_to_after_position=dialog.isMoveToPosition()
            )

    @handle_exception
    def on_start(self):
        # Store settings
        self.writeSettings()
        current_item = self.sequence_tree.current
        if isinstance(current_item, MeasurementTreeItem):
            contact_item = current_item.contact
            result = QtWidgets.QMessageBox.question(
                self,
                "Run Measurement",
                f"Are you sure to run measurement {current_item.name!r} for {contact_item.name!r}?"
            )
            if result != QtWidgets.QMessageBox.Yes:
                return
            self._on_start(current_item)
        elif isinstance(current_item, ContactTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.use_table()
            )
            self.operator_widget.writeSettings()
            self.output_widget.writeSettings()
            dialog.readSettings()
            dialog.exec()
            if dialog.result() == QtWidgets.QDialog.Accepted:
                dialog.writeSettings()
                self.operator_widget.readSettings()
                self.output_widget.readSettings()
                self._on_start(
                    current_item,
                    move_to_contact=dialog.isMoveToContact(),
                    move_to_after_position=dialog.isMoveToPosition()
                )
        elif isinstance(current_item, SampleTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.use_table()
            )
            self.operator_widget.writeSettings()
            self.output_widget.writeSettings()
            dialog.readSettings()
            dialog.exec()
            if dialog.result() == QtWidgets.QDialog.Accepted:
                dialog.writeSettings()
                self.operator_widget.readSettings()
                self.output_widget.readSettings()
                self._on_start(
                    current_item,
                    move_to_contact=dialog.isMoveToContact(),
                    move_to_after_position=dialog.isMoveToPosition()
                )

    def _on_start(self, context, move_to_contact=False, move_to_after_position=None):
        # Create output directory
        self.panels.store()
        self.panels.unmount()
        self.panels.clearReadings()
        self.create_output_dir()
        self.switch_off_lights()
        self.sync_environment_controls()
        self.lock_controls()
        measure = self.measure_process
        measure.context = context
        measure.set("table_position", self.table_position())
        measure.set("operator", self.operator())
        measure.set("output_dir", self.output_dir())
        measure.set("write_logfiles", settings.isWriteLogfiles())
        measure.set("use_environ", self.use_environment())
        measure.set("use_table", self.use_table())
        measure.set("serialize_json", settings.isExportJson())
        measure.set("serialize_txt", settings.isExportTxt())
        measure.set("move_to_contact", move_to_contact)
        measure.set("move_to_after_position", move_to_after_position)
        measure.set("contact_delay", settings.tableContactDelay())
        measure.set("retry_contact_overdrive", settings.retryContactOverdrive())
        def show_measurement(item):
            item.selectable = True
            item.series.clear()
            item[0].color = "blue"
            self.sequence_tree.scroll_to(item)
            self.panels.unmount()
            self.panels.hide()
            self.panels.clearReadings()
            panel = self.panels.get(item.type)
            panel.setVisible(True)
            panel.mount(item)
            measure.reading = panel.append_reading
            measure.update = panel.updateReadings
            measure.append_analysis = panel.append_analysis
            measure.state = panel.updateState
        def hide_measurement(item):
            item.selectable = False
            item[0].color = None
        measure.show_measurement = show_measurement
        measure.hide_measurement = hide_measurement
        measure.push_summary = self.on_push_summary
        measure.start()
        self.started.emit()

    def on_measurement_state(self, item, state=None):
        item.state = state
        self.sequence_tree.fit()

    def on_measurement_reset(self, item):
        item.reset()
        self.sequence_tree.fit()

    def saveToImage(self, item: MeasurementTreeItem, filename: str) -> None:
        """Save item plots to image file if enabled in properties."""
        panel = self.panels.get(item.type)
        if panel and settings.isPngPlots():
            panel.saveToImage(filename)

    def on_stop(self):
        self.sequence_widget.stop()
        self.measure_process.stop()
        self.stopping.emit()

    def on_finished(self):
        self.sync_environment_controls()
        self.unlock_controls()
        self.finished.emit()

    @handle_exception
    def on_reset_sequence_state(self):
        result = QtWidgets.QMessageBox.question(
            self,
            "Reset State",
            "Do you want to reset all sequence states?"
        )
        if result == QtWidgets.QMessageBox.Yes:
            current_item = self.sequence_tree.current
            self.panels.unmount()
            self.panels.clearReadings()
            self.panels.hide()
            for sample_item in self.sequence_tree:
                sample_item.reset()
            if current_item is not None:
                panel = self.panels.get(current_item.type)
                panel.setVisible(True)
                panel.mount(current_item)

    @handle_exception
    def on_edit_sequence(self):
        sequences = load_all_sequences(self.settings)
        dialog = EditSamplesDialog(self.sequence_tree, sequences)
        dialog.run()
        self.on_tree_selected(self.sequence_tree.current)

    # Measurement control

    def on_measure_restore(self):
        result = QtWidgets.QMessageBox.question(
            self,
            "Restore Defaults",
            "Do you want to restore to default parameters?"
        )
        if result == QtWidgets.QMessageBox.Yes:
            measurement = self.sequence_tree.current
            panel = self.panels.get(measurement.type)
            panel.restore()

    def on_status_start(self):
        self.lock_controls()
        self.statusWidget.reset()
        self.status_process.set("use_environ", self.use_environment())
        self.status_process.set("use_table", self.use_table())
        self.status_process.start()
        # Fix: stay in status tab
        index = self.tabWidget.indexOf(self.statusWidget)
        self.tabWidget.setCurrentIndex(index)

    def on_status_finished(self):
        self.unlock_controls()
        self.statusWidget.updateStatus(self.status_process)

    # Table calibration

    @handle_exception
    def on_table_joystick_toggled(self, state: bool) -> None:
        self.table_process.enable_joystick(state)

    def on_table_joystick_changed(self, state: bool) -> None:
        self.tableControlWidget.setJoystickState(state)

    def on_table_position_changed(self, position):
        self.tableControlWidget.updatePosition(position)

    def on_table_calibration_changed(self, position):
        self.tableControlWidget.update_calibration(position)
        panel = self.panels.get("contact")
        if panel:
            panel.updateUseTable(self.use_table() and self.tableControlWidget.isCalibrationValid())

    @handle_exception
    def on_table_control_clicked(self):
        self.table_process.enable_joystick(False)
        dialog = TableControlDialog(self.table_process, self.contact_quality_process)
        dialog.readSettings()
        dialog.loadSamples(list(self.sequence_tree)) # HACK
        if self.use_environment():
            # TODO !!!
            with self.environ_process as environ:
                pc_data = environ.pc_data()
                dialog.update_safety(laser_sensor=pc_data.relay_states.laser_sensor)
                dialog.update_probecard_light(pc_data.relay_states.probecard_light)
                dialog.update_microscope_light(pc_data.relay_states.microscope_light)
                dialog.update_box_light(pc_data.relay_states.box_light)
            dialog.update_lights_enabled(True)
            dialog.probecardLightToggled.connect(self.on_probecard_light_toggled)
            dialog.microscopeLightToggled.connect(self.on_microscope_light_toggled)
            dialog.boxLightToggled.connect(self.on_box_light_toggled)
        dialog.exec()
        self.contact_quality_process.stop()
        self.contact_quality_process.join()
        dialog.writeSettings()
        dialog.updateSamples()
        # Prevent glitch
        current_item = self.sequence_tree.current
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.mount(current_item)
        # Restore events...
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed
        self.sync_table_controls()
        # Store settings
        self.writeSettings()

    @handle_exception
    def on_laser_sensor_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_toggled(self, state: bool) -> None:
        with self.environ_process as environment:
            environment.set_pid_control(state)

    @handle_exception
    def switch_off_lights(self):
        if self.use_environment():
            with self.environ_process as environment:
                if environment.has_lights():
                    environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.use_environment():
            with self.environ_process as environment:
                environment.request_pc_data()

        else:
            self.environmentWidget.setEnabled(False)

    def on_pc_data_updated(self, pc_data):
        self.environGroupBox.setLaserSensorState(pc_data.relay_states.laser_sensor)
        self.environGroupBox.setBoxLightState(pc_data.relay_states.box_light)
        self.environGroupBox.setMicroscopeLightState(pc_data.relay_states.microscope_light)
        self.environGroupBox.setMicroscopeCameraState(pc_data.relay_states.microscope_camera)
        self.environGroupBox.setMicroscopeControlState(pc_data.relay_states.microscope_control)
        self.environGroupBox.setProbecardLightState(pc_data.relay_states.probecard_light)
        self.environGroupBox.setProbecardCameraState(pc_data.relay_states.probecard_camera)
        self.environGroupBox.setPidControlState(pc_data.pid_status)
        self.environmentWidget.setEnabled(True)
        t = time.time()
        # Note: occasional crashes due to `NaN` timestamp.
        if not math.isfinite(t):
            logger.error("invalid timestamp: %s", t)
            t = 0
        self.environmentWidget.appendData(t, pc_data)

    @handle_exception
    def sync_table_controls(self):
        """Syncronize table controls."""
        enabled = self.use_table()
        self.table_process.enabled = enabled
        self.on_table_position_changed(Position())
        self.on_table_calibration_changed(Position())
        if enabled:
            self.table_process.status()

    def on_environment_groupbox_toggled(self, state: bool) -> None:
        if state:
            self.environ_process.start()
            self.sync_environment_controls()
        else:
            self.environ_process.stop()

    def on_table_groupbox_toggled(self, state: bool) -> None:
        if state:
            self.table_process.start()
            self.table_process.enable_joystick(False)
        else:
            self.table_process.stop()
        self.sync_table_controls()

    @handle_exception
    def on_push_summary(self, *args):
        """Push result to summary and write to summary file (experimantal)."""
        data = self.summaryWidget.appendResult(*args)
        output_path = self.output_widget.currentLocation()
        if output_path and os.path.exists(output_path):
            filename = os.path.join(output_path, SUMMARY_FILENAME)
            has_header = os.path.exists(filename)
            with open(filename, "a") as fp:
                header = self.summaryWidget.Header
                fmt = CSVFormatter(fp)
                for key in data.keys():
                    fmt.add_column(key)
                if not has_header:
                    fmt.write_header()
                fmt.write_row(data)

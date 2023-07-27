import json
import logging
import math
import os
import time
import webbrowser
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

import comet
from comet.process import ProcessMixin
from comet import ui

from .components import (
    CalibrationWidget,
    OperatorWidget,
    PositionWidget,
    ToggleButton,
    WorkingDirectoryWidget,
)
from .core import config
from .core.position import Position
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
from .alignment import AlignmentDialog, safe_z_position
from .environmentwidget import EnvironmentWidget
from .measurementwidget import MeasurementWidget
from .utils import caldone_valid, handle_exception, create_icon

logger = logging.getLogger(__name__)


class SequenceWidget(QtWidgets.QGroupBox):

    config_version = 1

    def __init__(self, *, tree_selected, tree_double_clicked, start_all, start,
                 stop, reset_sequence_state, edit_sequence):
        super().__init__()

        self.current_path = user_home()
        self.setTitle("Sequence")
        self.tree_double_clicked = tree_double_clicked

        self._sequence_tree = SequenceTree(
            selected=tree_selected,
            double_clicked=self.tree_double_clicked
        )
        self._sequence_tree.qt.setMinimumWidth(360)

        self.startAllAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startAllAction.setText("&All Samples")
        self.startAllAction.triggered.connect(start_all)

        self.startSampleAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startSampleAction.setText("&Sample")
        self.startSampleAction.setEnabled(False)
        self.startSampleAction.triggered.connect(start)

        self.startContactAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startContactAction.setText("&Contact")
        self.startContactAction.setEnabled(False)
        self.startContactAction.triggered.connect(start)

        self.startMeasurementAction: QtWidgets.QAction = QtWidgets.QAction(self)
        self.startMeasurementAction.setText("&Measurement")
        self.startMeasurementAction.setEnabled(False)
        self.startMeasurementAction.triggered.connect(start)

        self.startMenu: QtWidgets.QMenu = QtWidgets.QMenu()
        self.startMenu.addAction(self.startAllAction)
        self.startMenu.addAction(self.startSampleAction)
        self.startMenu.addAction(self.startContactAction)
        self.startMenu.addAction(self.startMeasurementAction)

        self.startButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setToolTip("Start measurement sequence.")
        self.startButton.setStyleSheet("QPushButton:enabled{color:green;font-weight:bold;}")
        self.startButton.setMenu(self.startMenu)

        self.stopButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("Stop")
        self.stopButton.setToolTip("Stop measurement sequence.")
        self.stopButton.setEnabled(False)
        self.stopButton.setStyleSheet("QPushButton:enabled{color:red;font-weight:bold;}")
        self.stopButton.clicked.connect(stop)

        self.resetButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("Reset")
        self.resetButton.setToolTip("Reset measurement sequence state.")
        self.resetButton.clicked.connect(reset_sequence_state)

        self.editButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editButton.setText("Edit")
        self.editButton.setToolTip("Quick edit properties of sequence items.",)
        self.editButton.clicked.connect(edit_sequence)

        self.reloadConfigButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadConfigButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadConfigButton.setToolTip("Reload sequence configurations from file.")
        self.reloadConfigButton.clicked.connect(self.on_reload_config_clicked)

        self.addSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.addSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addSampleButton.setToolTip("Add new sample sequence.")
        self.addSampleButton.clicked.connect(self.on_add_sample_clicked)

        self.removeSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.removeSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeSampleButton.setToolTip("Remove current sample sequence.")
        self.removeSampleButton.clicked.connect(self.on_remove_sample_clicked)

        self.openButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.openButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_open.svg")))
        self.openButton.setToolTip("Open sequence tree from file.")
        self.openButton.clicked.connect(self.on_open_clicked)

        self.saveButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.saveButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "document_save.svg")))
        self.saveButton.setToolTip("Save sequence tree to file.")
        self.saveButton.clicked.connect(self.on_save_clicked)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.addWidget(self.startButton)
        self.buttonLayout.addWidget(self.stopButton)
        self.buttonLayout.addWidget(self.resetButton)
        self.buttonLayout.addWidget(self.editButton)
        self.buttonLayout.addWidget(self.reloadConfigButton)
        self.buttonLayout.addWidget(self.addSampleButton)
        self.buttonLayout.addWidget(self.removeSampleButton)
        self.buttonLayout.addWidget(self.openButton)
        self.buttonLayout.addWidget(self.saveButton)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._sequence_tree.qt)
        layout.addLayout(self.buttonLayout)

    def readSettings(self):
        samples = settings.settings.get("sequence_samples") or []
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
        self.current_path = settings.settings.get("sequence_default_path") or user_home()

    def writeSettings(self):
        sequence_samples = [sample.to_settings() for sample in self._sequence_tree]
        settings.settings["sequence_samples"] = sequence_samples
        settings.settings["sequence_default_path"] = self.current_path

    def setLocked(self, locked: bool) -> None:
        self._sequence_tree.double_clicked = None if locked else self.tree_double_clicked
        self.startButton.setEnabled(not locked)
        self.stopButton.setEnabled(locked)
        self.resetButton.setEnabled(not locked)
        self.editButton.setEnabled(not locked)
        self.reloadConfigButton.setEnabled(not locked)
        self.addSampleButton.setEnabled(not locked)
        self.removeSampleButton.setEnabled(not locked)
        self.saveButton.setEnabled(not locked)
        self.openButton.setEnabled(not locked)
        self._sequence_tree.setLocked(locked)

    def stop(self):
        self.stopButton.setEnabled(False)

    @handle_exception
    def on_reload_config_clicked(self, state):
        result = QtWidgets.QMessageBox.question(self, "Reload Configuration", "Do you want to reload sequence configurations from file?")
        if result != QtWidgets.QMessageBox.Yes:
            return
        sample_items = self._sequence_tree
        dialog = QtWidgets.QProgressDialog()
        dialog.setWindowModality(QtCore.Qt.WindowModal)
        dialog.setLabelText("Reloading sequences...")
        dialog.setCancelButton(None)
        dialog.setMaximum(len(sample_items))
        @handle_exception
        def callback():
            for sample_item in sample_items:
                dialog.setValue(dialog.value() + 1)
                if sample_item.sequence:
                    filename = sample_item.sequence.filename
                    sequence = config.load_sequence(filename)
                    sample_item.load_sequence(sequence)
            dialog.close()
        QtCore.QTimer.singleShot(100, callback)
        dialog.exec()

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
            result = QtWidgets.QMessageBox.question(self, "Remove Sample", f"Do you want to remove {item.name!r}?")
            if result == QtWidgets.QMessageBox.Yes:
                self._sequence_tree.remove(item)

    @handle_exception
    def on_open_clicked(self, state):
        filename = ui.filename_open(path=self.current_path, filter="JSON (*.json)")
        if filename:
            with open(filename) as f:
                logger.info("Reading sequence... %s", filename)
                data = json.load(f)
                logger.info("Reading sequence... done.")
            self.current_path = os.path.dirname(filename)
            version = data.get("version")
            if version is None:
                raise RuntimeError(f"Missing version information in sequence: {filename}")
            elif isinstance(version, int):
                if version != self.config_version:
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
        filename = ui.filename_save(path=self.current_path, filter="JSON (*.json)")
        if filename:
            samples = [sample.to_settings() for sample in self._sequence_tree]
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
            with open(filename, "w") as f:
                logger.info("Writing sequence... %s", filename)
                json.dump(data, f)
                logger.info("Writing sequence... done.")
            self.current_path = os.path.dirname(filename)


class TableControlWidget(QtWidgets.QGroupBox):

    joystickToggled = QtCore.pyqtSignal(bool)
    controlClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Table")
        self.setCheckable(True)

        self.joystickButton = ToggleButton().qt
        self.joystickButton.setText("Joystick")
        self.joystickButton.setToolTip("Toggle table joystick")
        self.joystickButton.setCheckable(True)
        self.joystickButton.toggled.connect(self.joystickToggled.emit)

        self.positionWidget = PositionWidget()

        self.calibrationWidget = CalibrationWidget()

        self.alignmentButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.alignmentButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "alignment.svg")))
        self.alignmentButton.setText("Alignment...")
        self.alignmentButton.setToolTip("Open table controls dialog.")
        self.alignmentButton.clicked.connect(self.controlClicked.emit)

        # Layout

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionWidget, 0, 0, 4, 1)
        layout.addWidget(self.calibrationWidget, 0, 1, 4, 1)
        layout.addWidget(self.alignmentButton, 1, 3)
        layout.addWidget(self.joystickButton, 2, 3)
        layout.setColumnStretch(2, 1)

        # Callbacks
        self._joystick_limits = [0, 0, 0]
        self._calibration_valid: bool = False

    def isCalibrationValid(self) -> bool:
        return self._calibration_valid

    def setJoystickEnabled(self, enabled: bool) -> None:
        self.joystickButton.setChecked(enabled)

    def setPosition(self, position: Position) -> None:
        self.positionWidget.setPosition(position)
        limits = self._joystick_limits
        enabled = position.x <= limits[0] and position.y <= limits[1] and position.z <= limits[2]
        self.joystickButton.setEnabled(enabled and self._calibration_valid)

    def setCalibration(self, position: Position) -> None:
        self.calibrationWidget.setCalibration(position)
        self._calibration_valid = caldone_valid(position)

    def readSettings(self) -> None:
        use_table = settings.settings.get("use_table") or False
        self.setChecked(use_table)
        self._joystick_limits = settings.table_joystick_maximum_limits


class EnvironmentControlWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Environment Box")
        self.setCheckable(True)

        self.laserSensorButton = self.createButton()
        self.laserSensorButton.setText("Laser")
        self.laserSensorButton.setToolTip("Toggle laser")

        self.boxLightButton = self.createButton()
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setToolTip("Toggle box light")

        self.microscopeLightButton = self.createButton()
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setToolTip("Toggle microscope light")

        self.microscopeCameraButton = self.createButton()
        self.microscopeCameraButton.setText("Mic Cam")
        self.microscopeCameraButton.setToolTip("Toggle microscope camera power")

        self.microscopeControlButton = self.createButton()
        self.microscopeControlButton.setText("Mic Ctrl")
        self.microscopeControlButton.setToolTip("Toggle microscope control")

        self.probecardLightButton = self.createButton()
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setToolTip("Toggle probe card light")

        self.probecardCameraButton = self.createButton()
        self.probecardCameraButton.setText("PC Cam")
        self.probecardCameraButton.setToolTip("Toggle probe card camera power")

        self.pidControlButton = self.createButton()
        self.pidControlButton.setText("PID Control")
        self.pidControlButton.setToolTip("Toggle PID control")

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.laserSensorButton, 0, 0)
        layout.addWidget(self.microscopeCameraButton, 1, 0)
        layout.addWidget(self.boxLightButton, 0, 1)
        layout.addWidget(self.probecardCameraButton, 1, 1)
        layout.addWidget(self.microscopeLightButton, 0, 2)
        layout.addWidget(self.microscopeControlButton, 1, 2)
        layout.addWidget(self.probecardLightButton, 0, 3)
        layout.addWidget(self.pidControlButton, 1, 3)

    def createButton(self) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(self)
        button.setCheckable(True)
        button.setChecked(False)
        button.setProperty("checkedIcon", create_icon(12, "green").qt)
        button.setProperty("uncheckedIcon", create_icon(12, "grey").qt)
        def updateIcon(state):
            button.setIcon(button.property("checkedIcon") if state else button.property("uncheckedIcon"))
        updateIcon(False)
        button.toggled.connect(updateIcon)
        return button

    def updateLaserSensorState(self, state: bool) -> None:
        self.laserSensorButton.setChecked(state)

    def updateBoxLightState(self, state: bool) -> None:
        self.boxLightButton.setChecked(state)

    def updateMicroscopeLightState(self, state: bool) -> None:
        self.microscopeLightButton.setChecked(state)

    def updateMicroscopeCameraState(self, state: bool) -> None:
        self.microscopeCameraButton.setChecked(state)

    def updateMicroscopeControlState(self, state: bool) -> None:
        self.microscopeControlButton.setChecked(state)

    def updateProbecardLightState(self, state: bool) -> None:
        self.probecardLightButton.setChecked(state)

    def updateProbecardCameraState(self, state: bool) -> None:
        self.probecardCameraButton.setChecked(state)

    def updatePidControlState(self, state: bool) -> None:
        self.pidControlButton.setChecked(state)


class Dashboard(QtWidgets.QWidget, ProcessMixin):

    sample_count = 4

    messageChanged = QtCore.pyqtSignal(str)
    progressChanged = QtCore.pyqtSignal(int, int)
    started = QtCore.pyqtSignal()
    aborting = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(Exception, object)

    def __init__(self, plugins, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.plugins = plugins

        self.noticeLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.noticeLabel.setText("Temporary Probecard Z-Limit applied. Revert after finishing current measurements.")
        self.noticeLabel.setStyleSheet("QLabel{color: black; background-color: yellow; padding: 4px; border-radius: 4px;}")
        self.noticeLabel.setVisible(False)

        self.sequenceWidget: SequenceWidget = SequenceWidget(
            tree_selected=self.on_tree_selected,
            tree_double_clicked=self.on_tree_double_clicked,
            start_all=self.on_start_all,
            start=self.on_start,
            stop=self.on_stop,
            reset_sequence_state=self.on_reset_sequence_state,
            edit_sequence=self.on_edit_sequence
        )
        self.sequence_tree = self.sequenceWidget._sequence_tree
        self.startAllAction = self.sequenceWidget.startAllAction
        self.startSampleAction = self.sequenceWidget.startSampleAction
        self.startContactAction = self.sequenceWidget.startContactAction
        self.startMeasurementAction = self.sequenceWidget.startMeasurementAction

        # Environment Controls

        self.environmentControlWidget = EnvironmentControlWidget(self)
        self.environmentControlWidget.toggled.connect(self.on_environment_groupbox_toggled)
        self.environmentControlWidget.laserSensorButton.toggled.connect(self.on_laser_sensor_toggled)
        self.environmentControlWidget.boxLightButton.toggled.connect(self.on_box_light_toggled)
        self.environmentControlWidget.microscopeLightButton.toggled.connect(self.on_microscope_light_toggled)
        self.environmentControlWidget.microscopeCameraButton.toggled.connect(self.on_microscope_camera_toggled)
        self.environmentControlWidget.microscopeControlButton.toggled.connect(self.on_microscope_control_toggled)
        self.environmentControlWidget.probecardLightButton.toggled.connect(self.on_probecard_light_toggled)
        self.environmentControlWidget.probecardCameraButton.toggled.connect(self.on_probecard_camera_toggled)
        self.environmentControlWidget.pidControlButton.toggled.connect(self.on_pid_control_toggled)

        # Table controls

        self.table_control_widget: TableControlWidget = TableControlWidget(self)
        self.table_control_widget.toggled.connect(self.on_table_groupbox_toggled)
        self.table_control_widget.joystickToggled.connect(self.on_table_joystick_toggled)
        self.table_control_widget.controlClicked.connect(self.on_table_control_clicked)

        # Operator

        self.operator_widget = OperatorWidget()
        self.operator_widget.readSettings()

        self.operatorGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.operatorGroupBox.setTitle("Operator")

        operatorGroupBoxLayout = QtWidgets.QVBoxLayout(self.operatorGroupBox)
        operatorGroupBoxLayout.addWidget(self.operator_widget.qt)

        # Working directory

        self.output_widget = WorkingDirectoryWidget()

        self.outputGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.outputGroupBox.setTitle("Working Directory")

        outputGroupBoxLayout = QtWidgets.QVBoxLayout(self.outputGroupBox)
        outputGroupBoxLayout.addWidget(self.output_widget.qt)

        # Controls

        self.controlWidget = QtWidgets.QWidget(self)

        controlWidgetLayout = QtWidgets.QGridLayout(self.controlWidget)
        controlWidgetLayout.setContentsMargins(0, 0, 0, 0)
        controlWidgetLayout.addWidget(self.sequenceWidget, 0, 0, 1, 2)
        controlWidgetLayout.addWidget(self.table_control_widget, 1, 0, 1, 2)
        controlWidgetLayout.addWidget(self.environmentControlWidget, 2, 0, 1, 2)
        controlWidgetLayout.addWidget(self.operatorGroupBox, 3, 0, 1, 1)
        controlWidgetLayout.addWidget(self.outputGroupBox, 3, 1, 1, 1)
        controlWidgetLayout.setRowStretch(0, 1)
        controlWidgetLayout.setColumnStretch(0, 3)
        controlWidgetLayout.setColumnStretch(1, 7)

        # Tabs

        self.measurementWidget = MeasurementWidget()
        self.measurementWidget.restoreDefaults.connect(self.restoreDefaults)

        self.environmentWidget = EnvironmentWidget()

        self.panels = self.measurementWidget.panels
        self.panels.sampleChanged.connect(lambda _: self.sequence_tree.fit())

        # Tabs

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.measurementWidget, "Measurement")
        self.tabWidget.addTab(self.environmentWidget, "Environment")

        # Layout

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.controlWidget)
        self.splitter.addWidget(self.tabWidget)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 9)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.noticeLabel, 0)
        layout.addWidget(self.splitter, 1)

        # Setup process callbacks

        self.environ_process = self.processes.get("environ")
        self.environ_process.pc_data_updated = self.on_pc_data_updated
        self.environ_process.failed = self.failed.emit

        self.table_process = self.processes.get("table")
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed
        self.table_process.failed = self.failed.emit

        self.measure_process = self.processes.get("measure")
        self.measure_process.finished = self.on_finished
        self.measure_process.measurement_state = self.on_measurement_state
        self.measure_process.measurement_reset = self.on_measurement_reset
        self.measure_process.save_to_image = self.on_save_to_image
        self.measure_process.failed = self.failed.emit
        self.measure_process.message = self.messageChanged.emit
        self.measure_process.progress = self.progressChanged.emit

        self.contact_quality_process = self.processes.get("contact_quality")
        self.contact_quality_process.failed = self.failed.emit

    @handle_exception
    def readSettings(self):
        settings_ = QtCore.QSettings()
        settings_.beginGroup("dashboard")
        self.splitter.restoreState(settings_.value("splitterState", QtCore.QByteArray(), QtCore.QByteArray))
        settings_.endGroup()

        self.sequenceWidget.readSettings()
        use_environ = settings.settings.get("use_environ", False)
        self.environmentControlWidget.setChecked(use_environ)
        self.table_control_widget.readSettings()
        self.operator_widget.readSettings()
        self.output_widget.readSettings()

    @handle_exception
    def writeSettings(self):
        settings_ = QtCore.QSettings()
        settings_.beginGroup("dashboard")
        settings_.setValue("splitterState", self.splitter.saveState())
        settings_.endGroup()

        self.sequenceWidget.writeSettings()
        settings.settings["use_environ"] = self.isEnvironmentEnabled()
        settings.settings["use_table"] = self.isTableEnabled()
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
        if self.isTableEnabled():
            return self.table_process.get_cached_position()
        return Position()

    def isEnvironmentEnabled(self) -> bool:
        """Return True if environment box enabled."""
        return self.environmentControlWidget.isChecked()

    def isTableEnabled(self) -> bool:
        """Return True if table control enabled."""
        return self.table_control_widget.isChecked()

    def operator(self):
        """Return current operator."""
        return self.operator_widget.operator_combo_box.qt.currentText().strip()

    def output_dir(self):
        """Return output base path."""
        return os.path.realpath(self.output_widget.current_location)

    def create_output_dir(self):
        """Create output directory for sample if not exists, return directory
        path.
        """
        output_dir = self.output_dir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def write_logfiles(self):
        return bool(settings.settings.get("write_logfiles", True))

    def export_json(self):
        return bool(settings.settings.get("export_json", True))

    def export_txt(self):
        return bool(settings.settings.get("export_txt", True))

    # Callbacks

    def setControlsLocked(self, locked: bool) -> None:
        """Lock or unlock dashboard controls."""
        self.environmentControlWidget.setEnabled(not locked)
        self.table_control_widget.setEnabled(not locked)
        self.sequenceWidget.setLocked(locked)
        self.outputGroupBox.setEnabled(not locked)
        self.operatorGroupBox.setEnabled(not locked)
        self.measurementWidget.setLocked(locked)
        self.plugins.handle("lock_controls", locked)

    def setNoticeVisible(self, visible: bool) -> None:
        self.noticeLabel.setVisible(visible)

    # Sequence control

    def on_tree_selected(self, item):
        self.panels.store()
        self.panels.unmount()
        self.panels.clear()
        self.panels.hide()
        self.measurementWidget.setControlsVisible(False)
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
            panel.tableMoveRequested.connect(self.moveTable)
            panel.tableContactRequested.connect(self.contactTable)
            panel.mount(item)
            self.startContactAction.setEnabled(True)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            if panel:
                panel.setVisible(True)
                panel.mount(item)
                self.measurementWidget.setControlsVisible(True)
                self.startMeasurementAction.setEnabled(True)
        # Show measurement tab
        self.tabWidget.setCurrentWidget(self.measurementWidget)

    def on_tree_double_clicked(self, item, index):
        self.on_start()

    # Contcat table controls

    @handle_exception
    def moveTable(self, contact) -> None:
        if self.isTableEnabled():
            self.setControlsLocked(True)
            x, y, z = contact.position
            self.table_process.message_changed = lambda message: self.messageChanged.emit(message)
            self.table_process.progress_changed = lambda a, b: self.progressChanged.emit(a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def contactTable(self, contact) -> None:
        if self.isTableEnabled():
            self.setControlsLocked(True)
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
        self.setControlsLocked(False)

    @handle_exception
    def on_start_all(self, state=None):
        sample_items = SamplesItem(self.sequence_tree)
        dialog = StartSequenceDialog(
            context=sample_items,
            table_enabled=self.isTableEnabled()
        )
        self.operator_widget.writeSettings()
        self.output_widget.writeSettings()
        dialog.readSettings()
        if not dialog.run():
            return
        dialog.writeSettings()
        self.operator_widget.readSettings()
        self.output_widget.readSettings()
        self._on_start(
            sample_items,
            move_to_contact=dialog.move_to_contact(),
            move_to_after_position=dialog.move_to_position()
        )

    @handle_exception
    def on_start(self, state=None):
        # Store settings
        self.writeSettings()
        current_item = self.sequence_tree.current
        if isinstance(current_item, MeasurementTreeItem):
            contact_item = current_item.contact
            message = f"Are you sure to run measurement {current_item.name!r} for {contact_item.name!r}?"
            result = QtWidgets.QMessageBox.question(self, "Run Measurement", message)
            if result == QtWidgets.QMessageBox.Yes:
                self._on_start(current_item)
            return
        elif isinstance(current_item, ContactTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.isTableEnabled()
            )
            self.operator_widget.writeSettings()
            self.output_widget.writeSettings()
            dialog.readSettings()
            if not dialog.run():
                return
            dialog.writeSettings()
            self.operator_widget.readSettings()
            self.output_widget.readSettings()
            self._on_start(
                current_item,
                move_to_contact=dialog.move_to_contact(),
                move_to_after_position=dialog.move_to_position()
            )
        elif isinstance(current_item, SampleTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.isTableEnabled()
            )
            self.operator_widget.writeSettings()
            self.output_widget.writeSettings()
            dialog.readSettings()
            if not dialog.run():
                return
            dialog.writeSettings()
            self.operator_widget.readSettings()
            self.output_widget.readSettings()
            move_to_after_position = dialog.move_to_position()
            self._on_start(
                current_item,
                move_to_contact=dialog.move_to_contact(),
                move_to_after_position=dialog.move_to_position()
            )

    def _on_start(self, context, move_to_contact=False, move_to_after_position=None):
        self.started.emit()
        # Create output directory
        self.panels.store()
        self.panels.unmount()
        self.panels.clear()
        self.create_output_dir()
        self.switch_off_lights()
        self.sync_environment_controls()
        measure = self.measure_process
        measure.context = context
        measure.set("table_position", self.table_position())
        measure.set("operator", self.operator())
        measure.set("output_dir", self.output_dir())
        measure.set("write_logfiles", self.write_logfiles())
        measure.set("use_environ", self.isEnvironmentEnabled())
        measure.set("use_table", self.isTableEnabled())
        measure.set("serialize_json", self.export_json())
        measure.set("serialize_txt", self.export_txt())
        measure.set("move_to_contact", move_to_contact)
        measure.set("move_to_after_position", move_to_after_position)
        measure.set("contact_delay", settings.settings.get("table_contact_delay") or 0)
        measure.set("retry_contact_overdrive", settings.retry_contact_overdrive)
        def show_measurement(item):
            item.selectable = True
            item.series.clear()
            item[0].color = "blue"
            self.sequence_tree.scroll_to(item)
            self.panels.unmount()
            self.panels.hide()
            self.panels.clear()
            panel = self.panels.get(item.type)
            panel.setVisible(True)
            panel.mount(item)
            measure.reading = panel.append_reading
            measure.update = panel.update_readings
            measure.append_analysis = panel.append_analysis
            measure.state = panel.state
        def hide_measurement(item):
            item.selectable = False
            item[0].color = None
        measure.show_measurement = show_measurement
        measure.hide_measurement = hide_measurement
        measure.push_summary = self.on_push_summary
        measure.measurements_finished = self.on_measurements_finished
        measure.start()

    def on_measurement_state(self, item, state=None):
        item.state = state
        self.sequence_tree.fit()

    def on_measurement_reset(self, item):
        item.reset()
        self.sequence_tree.fit()

    def on_save_to_image(self, item, filename):
        plot_png = settings.settings.get("png_plots") or False
        panel = self.panels.get(item.type)
        if panel and plot_png:
            panel.save_to_image(filename)

    def on_stop(self):
        self.sequenceWidget.stop()
        self.measure_process.stop()
        self.aborting.emit()

    def on_finished(self):
        self.sync_environment_controls()
        self.finished.emit()

    @handle_exception
    def on_reset_sequence_state(self, state=None):
        result = QtWidgets.QMessageBox.question(self, "Reset State", "Do you want to reset all sequence states?")
        if result == QtWidgets.QMessageBox.Yes:
            current_item = self.sequence_tree.current
            self.panels.unmount()
            self.panels.clear()
            self.panels.hide()
            for sample_item in self.sequence_tree:
                sample_item.reset()
            if current_item is not None:
                panel = self.panels.get(current_item.type)
                panel.setVisible(True)
                panel.mount(current_item)

    @handle_exception
    def on_edit_sequence(self, state=None):
        sequences = load_all_sequences(settings.settings)
        dialog = EditSamplesDialog(self.sequence_tree, sequences)
        dialog.run()
        self.on_tree_selected(self.sequence_tree.current)

    # Measurement control

    def restoreDefaults(self) -> None:
        result = QtWidgets.QMessageBox.question(self, "Restore Defaults", "Do you want to restore to default parameters?")
        if result == QtWidgets.QMessageBox.Yes:
            measurement = self.sequence_tree.current
            panel = self.panels.get(measurement.type)
            panel.restore()

    # Table calibration

    @handle_exception
    def on_table_joystick_toggled(self, state: bool) -> None:
        self.table_process.enable_joystick(state)

    def on_table_joystick_changed(self, state):
        self.table_control_widget.setJoystickEnabled(state)

    def on_table_position_changed(self, position):
        self.table_control_widget.setPosition(position)

    def on_table_calibration_changed(self, position):
        self.table_control_widget.setCalibration(position)
        panel = self.panels.get("contact")
        if panel:
            enabled = self.isTableEnabled() and self.table_control_widget.isCalibrationValid()
            panel.setTableEnabled(enabled)

    @handle_exception
    def on_table_control_clicked(self) -> None:
        self.table_process.enable_joystick(False)
        dialog = AlignmentDialog(self.table_process, self.contact_quality_process)
        dialog.readSettings()
        dialog.loadSamples(list(self.sequence_tree)) # HACK
        if self.isEnvironmentEnabled():
            # TODO !!!
            with self.environ_process as environ:
                pc_data = environ.pc_data()
                dialog.updateSafety(pc_data.relay_states.laser_sensor)
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
    def on_laser_sensor_toggled(self, state):
        with self.environ_process as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_toggled(self, state):
        with self.environ_process as environment:
            environment.set_pid_control(state)

    @handle_exception
    def switch_off_lights(self):
        if self.isEnvironmentEnabled():
            with self.environ_process as environment:
                if environment.has_lights():
                    environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.isEnvironmentEnabled():
            with self.environ_process as environment:
                environment.request_pc_data()

        else:
            self.environmentWidget.setEnabled(False)

    def on_pc_data_updated(self, pc_data):
        self.environmentControlWidget.updateLaserSensorState(pc_data.relay_states.laser_sensor)
        self.environmentControlWidget.updateBoxLightState(pc_data.relay_states.box_light)
        self.environmentControlWidget.updateMicroscopeLightState(pc_data.relay_states.microscope_light)
        self.environmentControlWidget.updateMicroscopeCameraState(pc_data.relay_states.microscope_camera)
        self.environmentControlWidget.updateMicroscopeControlState(pc_data.relay_states.microscope_control)
        self.environmentControlWidget.updateProbecardLightState(pc_data.relay_states.probecard_light)
        self.environmentControlWidget.updateProbecardCameraState(pc_data.relay_states.probecard_camera)
        self.environmentControlWidget.updatePidControlState(pc_data.pid_status)
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
        enabled = self.isTableEnabled()
        self.table_process.enabled = enabled
        self.on_table_position_changed(Position())
        self.on_table_calibration_changed(Position())
        if enabled:
            self.table_process.status()

    def on_environment_groupbox_toggled(self, state):
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
    def on_push_summary(self, data: dict) -> None:
        self.plugins.handle("summary", data=data)

    @handle_exception
    def on_measurements_finished(self) -> None:
        message = "PQC measurements finished!"
        self.plugins.handle("notification", message=message)

import json
import logging
import math
import os
import time
import threading
import webbrowser
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

import comet
from comet.process import ProcessMixin
from ..workers.measure import MeasureWorker
from .components import (
    CalibrationWidget,
    OperatorWidget,
    PositionWidget,
    ToggleButton,
    WorkingDirectoryWidget,
)
from ..core import config
from ..core.position import Position
from ..core.utils import make_path
from .sequence import (
    ContactTreeItem,
    EditSamplesDialog,
    MeasurementTreeItem,
    SequenceRootTreeItem,
    SampleTreeItem,
    SequenceTreeWidget,
    StartSequenceDialog,
    load_all_sequences,
)
from ..settings import settings
from .alignment import AlignmentDialog, safe_z_position
from .environmentwidget import EnvironmentWidget
from .measurementwidget import MeasurementWidget
from ..utils import caldone_valid

logger = logging.getLogger(__name__)


class SequenceWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Sequence")
        self.sequenceTreeWidget = SequenceTreeWidget(self)
        self.sequenceTreeWidget.setMinimumWidth(360)

        self.startButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setToolTip("Start measurement sequence.")
        self.startButton.setStyleSheet("QPushButton:enabled{color:green;font-weight:bold;}")

        self.stopButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("Stop")
        self.stopButton.setToolTip("Stop measurement sequence.")
        self.stopButton.setEnabled(False)
        self.stopButton.setStyleSheet("QPushButton:enabled{color:red;font-weight:bold;}")

        self.resetButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("Reset")
        self.resetButton.setToolTip("Reset measurement sequence state.")

        self.editButton = QtWidgets.QPushButton(self)
        self.editButton.setText("Edit")
        self.editButton.setToolTip("Quick edit properties of sequence items.",)

        self.reloadConfigButton = QtWidgets.QToolButton(self)

        self.addSampleButton = QtWidgets.QToolButton(self)

        self.removeSampleButton = QtWidgets.QToolButton(self)

        self.importButton = QtWidgets.QToolButton(self)

        self.exportButton = QtWidgets.QToolButton(self)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.addWidget(self.startButton)
        self.buttonLayout.addWidget(self.stopButton)
        self.buttonLayout.addWidget(self.resetButton)
        self.buttonLayout.addWidget(self.editButton)
        self.buttonLayout.addWidget(self.reloadConfigButton)
        self.buttonLayout.addWidget(self.addSampleButton)
        self.buttonLayout.addWidget(self.removeSampleButton)
        self.buttonLayout.addWidget(self.importButton)
        self.buttonLayout.addWidget(self.exportButton)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.sequenceTreeWidget)
        layout.addLayout(self.buttonLayout)

    def readSettings(self):
        samples = settings.settings.get("sequence_samples") or []
        self.sequenceTreeWidget.clear()
        for kwargs in samples:
            item = SampleTreeItem()
            self.sequenceTreeWidget.addTopLevelItem(item)
            item.setExpanded(False)
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logger.error(exc)
        if self.sequenceTreeWidget.topLevelItemCount():
            self.sequenceTreeWidget.setCurrentItem(self.sequenceTreeWidget.topLevelItem(0))
        self.sequenceTreeWidget.resizeColumns()

    def writeSettings(self):
        sequence_samples = [sample.to_settings() for sample in self.sequenceTreeWidget.sampleItems()]
        settings.settings["sequence_samples"] = sequence_samples

    def setLocked(self, locked: bool) -> None:
        self.startButton.setEnabled(not locked)
        self.stopButton.setEnabled(locked)
        self.resetButton.setEnabled(not locked)
        self.editButton.setEnabled(not locked)
        self.reloadConfigButton.setEnabled(not locked)
        self.addSampleButton.setEnabled(not locked)
        self.removeSampleButton.setEnabled(not locked)
        self.importButton.setEnabled(not locked)
        self.exportButton.setEnabled(not locked)
        self.sequenceTreeWidget.setLocked(locked)

    def stop(self):
        self.stopButton.setEnabled(False)

    def reloadConfig(self) -> None:
        result = QtWidgets.QMessageBox.question(self, "Reload Configuration", "Do you want to reload sequence configurations from file?")
        if result == QtWidgets.QMessageBox.Yes:
            progress = QtWidgets.QProgressDialog(self)
            progress.setLabelText("Reloading sequences...")
            progress.setMaximum(len(self.sequenceTreeWidget.sampleItems()))
            progress.setCancelButton(None)

            def callback():
                try:
                    for sample_item in self.sequenceTreeWidget.sampleItems():
                        progress.setValue(progress.value() + 1)
                        if sample_item.sequence:
                            filename = sample_item.sequence.filename
                            sequence = config.load_sequence(filename)
                            sample_item.load_sequence(sequence)
                finally:
                    progress.close()

            QtCore.QTimer.singleShot(200, callback)
            progress.exec()

    def addSampleItem(self) -> None:
        item = SampleTreeItem()
        item.setNameInfix("Unnamed")
        item.setEnabled(False)
        self.sequenceTreeWidget.addSampleItem(item)
        self.sequenceTreeWidget.setCurrentItem(item)
        self.sequenceTreeWidget.resizeColumns()

    def removeCurrentSampleItem(self) -> None:
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SampleTreeItem):
            result = QtWidgets.QMessageBox.question(self, "Remove Sample", f"Do you want to remove {item.name()!r}?")
            if result == QtWidgets.QMessageBox.Yes:
                index = self.sequenceTreeWidget.indexOfTopLevelItem(item)
                self.sequenceTreeWidget.takeTopLevelItem(index)


class TableControlWidget(QtWidgets.QGroupBox):

    joystickToggled = QtCore.pyqtSignal(bool)
    controlClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Table")
        self.setCheckable(True)

        self.joystickButton: ToggleButton = ToggleButton(self)
        self.joystickButton.setText("Joystick")
        self.joystickButton.setToolTip("Toggle table joystick")
        self.joystickButton.toggled.connect(self.joystickToggled.emit)

        self.positionWidget = PositionWidget()

        self.calibrationWidget = CalibrationWidget()

        self.alignmentButton = QtWidgets.QPushButton(self)
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

        self.laserSensorButton: ToggleButton = ToggleButton(self)
        self.laserSensorButton.setText("Laser")
        self.laserSensorButton.setToolTip("Toggle laser")

        self.boxLightButton: ToggleButton = ToggleButton(self)
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setToolTip("Toggle box light")

        self.microscopeLightButton: ToggleButton = ToggleButton(self)
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setToolTip("Toggle microscope light")

        self.microscopeCameraButton: ToggleButton = ToggleButton(self)
        self.microscopeCameraButton.setText("Mic Cam")
        self.microscopeCameraButton.setToolTip("Toggle microscope camera power")

        self.microscopeControlButton: ToggleButton = ToggleButton(self)
        self.microscopeControlButton.setText("Mic Ctrl")
        self.microscopeControlButton.setToolTip("Toggle microscope control")

        self.probecardLightButton: ToggleButton = ToggleButton(self)
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setToolTip("Toggle probe card light")

        self.probecardCameraButton: ToggleButton = ToggleButton(self)
        self.probecardCameraButton.setText("PC Cam")
        self.probecardCameraButton.setToolTip("Toggle probe card camera power")

        self.pidControlButton: ToggleButton = ToggleButton(self)
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


class AnimatedLabel(QtWidgets.QLabel):

    def __init__(self, parent):
        super().__init__(parent)
        self.animation = QtCore.QVariantAnimation()
        self.animation.setStartValue(QtGui.QColor('yellow'))
        self.animation.setKeyValueAt(0.5, QtGui.QColor('orange'))
        self.animation.setEndValue(QtGui.QColor('yellow'))
        self.animation.setDuration(4000)
        self.animation.valueChanged.connect(self.updateColor)
        self.animation.setLoopCount(-1)
        self.animation.start()

    def updateColor(self, color):
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QtGui.QColor(color))
        self.setPalette(palette)
        self.setAutoFillBackground(True)


class Dashboard(QtWidgets.QWidget, ProcessMixin):

    sample_count = 4

    messageChanged = QtCore.pyqtSignal(str)
    progressChanged = QtCore.pyqtSignal(int, int)
    started = QtCore.pyqtSignal()
    aborting = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(Exception, object)

    def __init__(self, station, plugins, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.station = station
        self.plugins = plugins

        self.measure_thread = None

        self.noticeLabel = AnimatedLabel(self)
        self.noticeLabel.setText("Temporary Probecard Z-Limit applied. Revert after finishing current measurements.")
        # self.noticeLabel.setStyleSheet("QLabel{color: black; background-color: yellow; padding: 8px; border-radius: 0;}")
        self.noticeLabel.setStyleSheet("QLabel{color: black; padding: 8px; border-radius: 0;}")
        self.noticeLabel.setVisible(False)
        self.noticeLabel.animation.start()

        self.sequenceControlWidget = SequenceWidget(self)

        self.sequenceTreeWidget = self.sequenceControlWidget.sequenceTreeWidget
        self.sequenceTreeWidget.currentItemChanged.connect(self.on_tree_selected)
        self.sequenceTreeWidget.itemDoubleClicked.connect(self.on_tree_double_clicked)

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

        self.tableControlWidget = TableControlWidget(self)
        self.tableControlWidget.toggled.connect(self.on_table_groupbox_toggled)
        self.tableControlWidget.joystickToggled.connect(self.on_table_joystick_toggled)
        self.tableControlWidget.controlClicked.connect(self.on_table_control_clicked)

        # Operator

        self.operatorWidget = OperatorWidget(self)

        # Working directory

        self.outputWidget = WorkingDirectoryWidget(self)
        self.outputWidget.setTitle("Working Directory")

        # Controls

        self.controlWidget = QtWidgets.QWidget(self)

        controlWidgetLayout = QtWidgets.QGridLayout(self.controlWidget)
        controlWidgetLayout.setContentsMargins(0, 0, 0, 0)
        controlWidgetLayout.addWidget(self.sequenceControlWidget, 0, 0, 1, 2)
        controlWidgetLayout.addWidget(self.tableControlWidget, 1, 0, 1, 2)
        controlWidgetLayout.addWidget(self.environmentControlWidget, 2, 0, 1, 2)
        controlWidgetLayout.addWidget(self.operatorWidget, 3, 0, 1, 1)
        controlWidgetLayout.addWidget(self.outputWidget, 3, 1, 1, 1)
        controlWidgetLayout.setRowStretch(0, 1)
        controlWidgetLayout.setColumnStretch(0, 3)
        controlWidgetLayout.setColumnStretch(1, 7)

        # Tabs

        self.measurementWidget = MeasurementWidget()
        self.measurementWidget.restoreDefaults.connect(self.restoreDefaults)

        self.environmentWidget = EnvironmentWidget()

        self.panels = self.measurementWidget.panels
        self.panels.sampleChanged.connect(lambda _: self.sequenceTreeWidget.resizeColumns())

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.noticeLabel, 0)
        self.splitterWrapper = QtWidgets.QWidget()
        layout.addWidget(self.splitterWrapper, 1)
        wrapperLayout = QtWidgets.QVBoxLayout(self.splitterWrapper)
        wrapperLayout.addWidget(self.splitter)

        # Setup process callbacks

        self.environ_process = self.station.environ_process
        self.environ_process.pc_data_updated = self.setPCData
        self.environ_process.failed = self.failed.emit

        self.table_process = self.station.table_process
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed
        self.table_process.failed = self.failed.emit

        self.contact_quality_process = self.processes.get("contact_quality")
        self.contact_quality_process.failed = self.failed.emit

    def readSettings(self):
        settings_ = QtCore.QSettings()
        settings_.beginGroup("dashboard")
        self.splitter.restoreState(settings_.value("splitterState", QtCore.QByteArray(), QtCore.QByteArray))
        settings_.endGroup()

        self.sequenceControlWidget.readSettings()
        use_environ = settings.settings.get("use_environ", False)
        self.environmentControlWidget.setChecked(use_environ)
        self.tableControlWidget.readSettings()
        self.operatorWidget.readSettings()
        self.outputWidget.readSettings()

    def writeSettings(self):
        settings_ = QtCore.QSettings()
        settings_.beginGroup("dashboard")
        settings_.setValue("splitterState", self.splitter.saveState())
        settings_.endGroup()

        self.sequenceControlWidget.writeSettings()
        settings.settings["use_environ"] = self.isEnvironmentEnabled()
        settings.settings["use_table"] = self.isTableEnabled()
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()

    def sequenceItems(self) -> list:
        items = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            items.append(item)
        return items

    def clearSequence(self) -> None:
        self.sequenceTreeWidget.clear()

    def addSequenceItem(self, item: SampleTreeItem) -> None:
        self.sequenceTreeWidget.addTopLevelItem(item)

    def sample_name(self):
        """Return sample name."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.name()
        if isinstance(item, ContactTreeItem):
            return item.sample.name()
        if isinstance(item, SampleTreeItem):
            return item.name()
        return ""

    def sampleType(self) -> str:
        """Return current sample type."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.sampleType()
        if isinstance(item, ContactTreeItem):
            return item.sample.sampleType()
        if isinstance(item, SampleTreeItem):
            return item.sampleType()
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
        return self.tableControlWidget.isChecked()

    def currentOperator(self) -> str:
        """Return current operator."""
        return self.operatorWidget.currentOperator()

    def outputDir(self) -> str:
        """Return output base path."""
        return os.path.realpath(self.outputWidget.currentLocation())

    def create_output_dir(self):
        """Create output directory for sample if not exists, return directory
        path.
        """
        output_dir = self.outputDir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def write_logfiles(self):
        return bool(settings.settings.get("write_logfiles", True))

    # Callbacks

    def setControlsLocked(self, locked: bool) -> None:
        """Lock or unlock dashboard controls."""
        self.environmentControlWidget.setEnabled(not locked)
        self.tableControlWidget.setEnabled(not locked)
        self.sequenceControlWidget.setLocked(locked)
        self.outputWidget.setEnabled(not locked)
        self.operatorWidget.setEnabled(not locked)
        self.measurementWidget.setLocked(locked)
        self.plugins.handle("lock_controls", locked)

    def setNoticeVisible(self, visible: bool) -> None:
        self.noticeLabel.setVisible(visible)
        if visible:
            self.noticeLabel.animation.start()
        else:
            self.noticeLabel.animation.stop()

    # Sequence control

    def on_tree_selected(self, item, previous) -> None:
        if not self.operatorWidget.isEnabled():
            return  # TODO
        self.panels.store()
        self.panels.unmount()
        self.panels.clear()
        self.panels.hide()
        self.measurementWidget.setControlsVisible(False)
        if isinstance(item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.setVisible(True)
            panel.mount(item)
        if isinstance(item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.setVisible(True)
            panel.mount(item)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            if panel:
                panel.setVisible(True)
                panel.mount(item)
                self.measurementWidget.setControlsVisible(True)
        # Show measurement tab
        self.tabWidget.setCurrentWidget(self.measurementWidget)

    def on_tree_double_clicked(self, item, index):
        if self.operatorWidget.isEnabled(): # TODO
            self.on_start()

    # Contcat table controls

    def moveTable(self, contact) -> None:
        if self.isTableEnabled():
            self.setControlsLocked(True)
            x, y, z = contact.position
            self.table_process.message_changed = lambda message: self.messageChanged.emit(message)
            self.table_process.progress_changed = lambda a, b: self.progressChanged.emit(a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

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
        current_item = self.sequenceTreeWidget.currentItem()
        if isinstance(current_item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.setVisible(True)
            panel.mount(current_item)
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.setVisible(True)
            panel.mount(current_item)
        self.setControlsLocked(False)

    def on_start_all(self):
        sample_items = SequenceRootTreeItem(self.sequenceTreeWidget.sampleItems())
        dialog = StartSequenceDialog(self)
        dialog.setMessage("<b>Are you sure to start all enabled sequences for all enabled samples?</b>")
        dialog.setTableEnabled(self.isTableEnabled())
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()
        dialog.readSettings()
        if dialog.exec() == dialog.Accepted:
            dialog.writeSettings()
            self.operatorWidget.readSettings()
            self.outputWidget.readSettings()
            self._on_start(
                sample_items,
                move_to_contact=dialog.isMoveToContact(),
                move_to_after_position=dialog.isMoveToPosition()
            )

    def startMeasurement(self, item: MeasurementTreeItem) -> None:
        contact_item = item.contact
        message = f"Are you sure to run measurement {item.name()!r} for {contact_item.name()!r}?"
        result = QtWidgets.QMessageBox.question(self, "Run Measurement", message)
        if result == QtWidgets.QMessageBox.Yes:
            self._on_start(item)

    def startContact(self, item: ContactTreeItem) -> None:
        dialog = StartSequenceDialog(self)
        dialog.setMessage(f"<b>Are you sure to start sequence {item.name()!r}?</b>")
        dialog.setTableEnabled(self.isTableEnabled())
        # TODO
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()
        dialog.readSettings()
        if dialog.exec() == dialog.Accepted:
            dialog.writeSettings()
            self.operatorWidget.readSettings()
            self.outputWidget.readSettings()
            self._on_start(
                item,
                move_to_contact=dialog.isMoveToContact(),
                move_to_after_position=dialog.isMoveToPosition()
            )

    def startSample(self, item: SampleTreeItem) -> None:
        dialog = StartSequenceDialog(self)
        dialog.setMessage(f"<b>Are you sure to start all enabled sequences for {item.name()!r}?</b>")
        dialog.setTableEnabled(self.isTableEnabled())
        # TODO
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()
        dialog.readSettings()
        if dialog.exec() == dialog.Accepted:
            dialog.writeSettings()
            self.operatorWidget.readSettings()
            self.outputWidget.readSettings()
            self._on_start(
                item,
                move_to_contact=dialog.isMoveToContact(),
                move_to_after_position=dialog.isMoveToPosition()
            )

    def on_start(self) -> None:
        # Store settings
        self.writeSettings()
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, MeasurementTreeItem):
            self.startMeasurement(item)
        elif isinstance(item, ContactTreeItem):
            self.startContact(item)
        elif isinstance(item, SampleTreeItem):
            self.startSample(item)

    def _on_start(self, item, move_to_contact=False, move_to_after_position=None):
        self.started.emit()
        # Create output directory
        self.panels.store()
        self.panels.unmount()
        self.panels.clear()
        self.create_output_dir()
        self.switch_off_lights()
        self.sync_environment_controls()

        config = {
            "table_position": self.table_position(),  # TODO state
            "table_contact_delay": settings.settings.get("table_contact_delay", 0),  # TODO
            "retry_contact_overdrive": settings.retry_contact_overdrive,
            "write_logfiles": self.write_logfiles(),
            "serialize_json": settings.export_json,
            "serialize_txt": settings.export_txt,
            "use_environ": self.isEnvironmentEnabled(),
            "use_table": self.isTableEnabled(),
            "move_to_contact": move_to_contact,
            "move_to_after_position": move_to_after_position,
            "operator": self.currentOperator(),
            "output_dir": self.outputDir(),
        }

        worker = MeasureWorker(self.station, config, item)
        worker.failed.connect(lambda exc: self.failed.emit(exc, None))
        worker.finished.connect(self.on_finished)
        worker.message_changed.connect(self.messageChanged.emit)
        worker.progress_changed.connect(self.progressChanged.emit)
        worker.item_state_changed.connect(self.setItemState)
        worker.item_recontact_changed.connect(self.setItemRecontact)
        worker.item_remeasure_changed.connect(self.setItemRemeasure)
        worker.item_reset.connect(self.resetItem)
        worker.item_visible.connect(self.showItem)
        worker.item_hidden.connect(self.hideItem)
        worker.save_to_image.connect(self.safeToImage)
        worker.summary_pushed.connect(self.pushSummary)
        worker.finished.connect(self.sequenceFinished)
        worker.reading_appended.connect(self.appendReading)
        worker.readings_updated.connect(self.updateReadings)
        worker.analysis_appended.connect(self.appendAnalysis)
        worker.state_changed.connect(self.updateState)
        self.aborting.connect(worker.abort)

        self.measure_thread = threading.Thread(target=worker)
        self.measure_thread.start()

    def appendReading(self, name, x, y):
        if self._panel:
            self._panel.appendReading(name, x, y)

    def updateReadings(self):
        if self._panel:
            self._panel.updateReadings()

    def appendAnalysis(self, key, value):
        if self._panel:
            self._panel.appendAnalysis(key, value)

    def updateState(self, *args):
        if self._panel:
            self._panel.updateState(*args)

    def setItemState(self, item, state) -> None:
        item.setState(state)
        item.setExpanded(True)
        self.sequenceTreeWidget.resizeColumns()

    def setItemRecontact(self, item, count) -> None:
        item.setRecontact(count)
        item.setExpanded(True)
        self.sequenceTreeWidget.resizeColumns()

    def setItemRemeasure(self, item, count) -> None:
        item.setRemeasure(count)
        item.setExpanded(True)
        self.sequenceTreeWidget.resizeColumns()

    def resetItem(self, item) -> None:
        item.reset()
        self.sequenceTreeWidget.resizeColumns()

    def showItem(self, item) -> None:
        item.setSelectable(True)
        item.series.clear()
        item.setForeground(0, QtGui.QBrush(QtGui.QColor("blue")))
        self.sequenceTreeWidget.scrollToItem(item)
        self.panels.unmount()
        self.panels.hide()
        self.panels.clear()
        panel = self.panels.get(item.type)
        panel.setVisible(True)
        panel.mount(item)
        self._panel = panel

    def hideItem(self, item) -> None:
        item.setSelectable(False)
        item.setForeground(0, QtGui.QBrush())

    def safeToImage(self, item, filename) -> None:
        plot_png = settings.settings.get("png_plots") or False
        panel = self.panels.get(item.type)
        if panel and plot_png:
            panel.saveToImage(filename)

    def on_stop(self):
        self.sequenceControlWidget.stop()
        self.aborting.emit()

    def on_finished(self):
        self.sync_environment_controls()
        self.finished.emit()
        self.measure_thread = None

    def on_reset_sequence_state(self):
        result = QtWidgets.QMessageBox.question(self, "Reset State", "Do you want to reset all sequence states?")
        if result == QtWidgets.QMessageBox.Yes:
            current_item = self.sequenceTreeWidget.currentItem()
            self._panel = None
            self.panels.unmount()
            self.panels.clear()
            self.panels.hide()
            for sample_item in self.sequenceTreeWidget.sampleItems():
                sample_item.reset()
            if current_item is not None:
                panel = self.panels.get(current_item.type)
                panel.setVisible(True)
                panel.mount(current_item)

    def on_edit_sequence(self):
        sequences = load_all_sequences(settings.settings)
        dialog = EditSamplesDialog(self.sequenceTreeWidget.sampleItems(), sequences)
        dialog.run()
        self.on_tree_selected(self.sequenceTreeWidget.currentItem(), None)

    # Measurement control

    def restoreDefaults(self) -> None:
        result = QtWidgets.QMessageBox.question(self, "Restore Defaults", "Do you want to restore to default parameters?")
        if result == QtWidgets.QMessageBox.Yes:
            item = self.sequenceTreeWidget.currentItem()
            if isinstance(item, MeasurementTreeItem):
                panel = self.panels.get(item.type)
                panel.restore()

    # Table calibration

    def on_table_joystick_toggled(self, state: bool) -> None:
        self.table_process.enable_joystick(state)

    def on_table_joystick_changed(self, state):
        self.tableControlWidget.setJoystickEnabled(state)

    def on_table_position_changed(self, position):
        self.tableControlWidget.setPosition(position)

    def on_table_calibration_changed(self, position):
        self.tableControlWidget.setCalibration(position)
        panel = self.panels.get("contact")
        if panel:
            enabled = self.isTableEnabled() and self.tableControlWidget.isCalibrationValid()
            panel.setTableEnabled(enabled)

    def on_table_control_clicked(self) -> None:
        self.table_process.enable_joystick(False)
        dialog = AlignmentDialog(self.table_process, self.contact_quality_process)
        dialog.readSettings()
        dialog.loadSamples(self.sequenceTreeWidget.sampleItems())
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
        current_item = self.sequenceTreeWidget.currentItem()
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.mount(current_item)
        # Restore events...
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed
        self.syncTableControls()
        # Store settings
        self.writeSettings()

    def on_laser_sensor_toggled(self, state):
        with self.environ_process as environment:
            environment.set_laser_sensor(state)

    def on_box_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_box_light(state)

    def on_microscope_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_light(state)

    def on_microscope_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_camera(state)

    def on_microscope_control_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_control(state)

    def on_probecard_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_light(state)

    def on_probecard_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_camera(state)

    def on_pid_control_toggled(self, state):
        with self.environ_process as environment:
            environment.set_pid_control(state)

    def switch_off_lights(self):
        if self.isEnvironmentEnabled():
            with self.environ_process as environment:
                if environment.has_lights():
                    environment.dim_lights()

    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.isEnvironmentEnabled():
            with self.environ_process as environment:
                environment.request_pc_data()

        else:
            self.environmentWidget.setEnabled(False)

    def setPCData(self, pc_data):
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

    def syncTableControls(self):
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
        self.syncTableControls()

    def pushSummary(self, data: dict) -> None:
        self.plugins.handle("summary", data=data)

    def sequenceFinished(self) -> None:
        message = "PQC measurements finished!"
        self.plugins.handle("notification", message=message)

    def shutdown(self):
        if self.measure_thread:
            self.on_stop()
            self.measure_thread.join()

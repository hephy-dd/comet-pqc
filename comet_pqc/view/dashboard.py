import json
import logging
import math
import os
import time
import webbrowser
from typing import Dict, List, Optional

import comet
from PyQt5 import QtCore, QtGui, QtWidgets

from ..core import config
from ..core.position import Position
from ..core.utils import make_path
from ..settings import settings
from ..utils import caldone_valid, create_dir
from .components import (CalibrationWidget, OperatorWidget, PositionWidget,
                         ToggleButton, WorkingDirectoryWidget,
                         handle_exception, showQuestion, showException)
from .environmentwidget import EnvironmentWidget
from .measurementwidget import MeasurementWidget
from .sequencedialogs import SequenceStartDialog
from .sequencetreewidget import (ContactTreeItem, MeasurementTreeItem,
                                  SamplesItem, SampleTreeItem,
                                  SequenceTreeWidget, dump_sequence_tree,
                                  load_sequence_tree)
from .statuswidget import StatusWidget
from .alignmentdialog import AlignmentDialog, safe_z_position

logger = logging.getLogger(__name__)


class SequenceGroupBox(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Sequence")

        self.sequenceTreeWidget: SequenceTreeWidget = SequenceTreeWidget(self)
        self.sequenceTreeWidget.setMinimumWidth(360)

        self.startButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setStatusTip("Start measurement sequence.")
        self.startButton.setStyleSheet("QPushButton:enabled{color:green;font-weight:bold;}")

        self.stopButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("Stop")
        self.stopButton.setStatusTip("Stop measurement sequence.")
        self.stopButton.setStyleSheet("QPushButton:enabled{color:red;font-weight:bold;}")

        self.resetButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("Reset")
        self.resetButton.setStatusTip("Reset measurement sequence state.")

        self.reloadConfigButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadConfigButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadConfigButton.setStatusTip("Reload sequence configurations from file.")
        self.reloadConfigButton.clicked.connect(self.reloadConfig)

        self.addSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.addSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addSampleButton.setStatusTip("Add new sample sequence.")
        self.addSampleButton.clicked.connect(self.addSample)

        self.removeSampleButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.removeSampleButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeSampleButton.setStatusTip("Remove current sample sequence.")
        self.removeSampleButton.clicked.connect(self.removeSample)

        self.bottomLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self.bottomLayout.addWidget(self.startButton)
        self.bottomLayout.addWidget(self.stopButton)
        self.bottomLayout.addWidget(self.resetButton)
        self.bottomLayout.addWidget(self.reloadConfigButton)
        self.bottomLayout.addWidget(self.addSampleButton)
        self.bottomLayout.addWidget(self.removeSampleButton)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.sequenceTreeWidget)
        layout.addLayout(self.bottomLayout)

    def sampleItems(self) -> List[SampleTreeItem]:
        """Return list of sample items from sequence."""
        return self.sequenceTreeWidget.sampleItems()

    def removeSampleItem(self, item: SampleTreeItem) -> None:
        """Remove sample item from sequence."""
        index: int = self.sequenceTreeWidget.indexOfTopLevelItem(item)
        self.sequenceTreeWidget.takeTopLevelItem(index)

    def readSettings(self) -> None:
        samples = settings.value("sequence_samples", [], list)
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

    def writeSettings(self) -> None:
        sequence_samples: List[Dict] = []
        for item in self.sequenceTreeWidget.sampleItems():
            sequence_samples.append(item.to_settings())
        settings.setValue("sequence_samples", sequence_samples)

    def setLocked(self, locked: bool) -> None:
        self.startButton.setEnabled(not locked)
        self.stopButton.setEnabled(locked)
        self.resetButton.setEnabled(not locked)
        self.reloadConfigButton.setEnabled(not locked)
        self.addSampleButton.setEnabled(not locked)
        self.removeSampleButton.setEnabled(not locked)
        self.sequenceTreeWidget.setLocked(locked)

    def stop(self):
        self.stopButton.setEnabled(False)

    @handle_exception
    def reloadConfig(self, checked) -> None:
        if showQuestion(
            title="Reload Configuration",
            text="Do you want to reload sequence configurations from file?",
        ):
            for item in self.sampleItems():
                if item.sequence:
                    filename = item.sequence.filename
                    sequence = config.load_sequence(filename)
                    item.load_sequence(sequence)

    @handle_exception
    def addSample(self, checked) -> None:
        item: SampleTreeItem = SampleTreeItem(
            name_prefix="",
            name_infix="Unnamed",
            name_suffix="",
            sample_type="",
            enabled=False
        )
        self.sequenceTreeWidget.addTopLevelItem(item)
        self.sequenceTreeWidget.setCurrentItem(item)
        self.sequenceTreeWidget.resizeColumns()

    @handle_exception
    def removeSample(self, checked) -> None:
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SampleTreeItem):
            if showQuestion(
                title="Remove Sample",
                text=f"Do you want to remove {item.name!r}?",
            ):
                self.removeSampleItem(item)


class TableGroupBox(QtWidgets.QGroupBox):

    joystickToggled = QtCore.pyqtSignal(bool)
    alignmentClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Table")
        self.setCheckable(True)

        self.joystickMaximumLimits: List = [0, 0, 0]
        self.isCalibrationValid: bool = False

        self.joystickButton: ToggleButton = ToggleButton(self)
        self.joystickButton.setText("Joystick")
        self.joystickButton.setToolTip("Toggle table joystick")
        self.joystickButton.toggled.connect(self.joystickToggled.emit)

        self.positionWidget: PositionWidget = PositionWidget(self)

        self.calibrationWidget: CalibrationWidget = CalibrationWidget(self)

        self.controlButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.controlButton.setIcon(QtGui.QIcon(make_path("assets", "icons","alignment.svg")))
        self.controlButton.setText("Alignment")
        self.controlButton.setToolTip("Open sequence alignment dialog")
        self.controlButton.clicked.connect(self.alignmentClicked.emit)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionWidget, 0, 0, 4, 1)
        layout.addWidget(self.calibrationWidget, 0, 1, 4, 1)
        layout.addWidget(self.controlButton, 1, 3)
        layout.addWidget(self.joystickButton, 2, 3)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(3, 1)

    def setJoystickEnabled(self, state: bool) -> None:
        with QtCore.QSignalBlocker(self.joystickButton):
            self.joystickButton.setChecked(state)
            self.joystickButton.toggleIcon(state)  # TODO

    def setPosition(self, position) -> None:
        self.positionWidget.setPosition(position)
        limits = self.joystickMaximumLimits
        enabled = position.x <= limits[0] and position.y <= limits[1] and position.z <= limits[2]
        self.joystickButton.setEnabled(enabled and self.isCalibrationValid)

    def setCalibration(self, position) -> None:
        self.calibrationWidget.setCalibration(position)
        self.isCalibrationValid = caldone_valid(position)

    def readSettings(self) -> None:
        enabled = settings.use_table()
        self.setChecked(enabled)
        self.joystickMaximumLimits = settings.table_joystick_maximum_limits


class EnvironmentGroupBox(QtWidgets.QGroupBox):

    laser_sensor_toggled = QtCore.pyqtSignal(bool)
    box_light_toggled = QtCore.pyqtSignal(bool)
    microscope_light_toggled = QtCore.pyqtSignal(bool)
    microscope_camera_toggled = QtCore.pyqtSignal(bool)
    microscope_control_toggled = QtCore.pyqtSignal(bool)
    probecard_light_toggled = QtCore.pyqtSignal(bool)
    probecard_camera_toggled = QtCore.pyqtSignal(bool)
    pid_control_toggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Environment Box")
        self.setCheckable(True)

        self.laserSensorButton: ToggleButton = ToggleButton(self)
        self.laserSensorButton.setText("Laser")
        self.laserSensorButton.setStatusTip("Toggle laser")
        self.laserSensorButton.toggled.connect(self.laser_sensor_toggled.emit)

        self.boxLightButton: ToggleButton = ToggleButton(self)
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setStatusTip("Toggle box light")
        self.boxLightButton.toggled.connect(self.box_light_toggled.emit)

        self.microscopeLightButton: ToggleButton = ToggleButton(self)
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setStatusTip("Toggle microscope light")
        self.microscopeLightButton.toggled.connect(self.microscope_light_toggled.emit)

        self.microscopeCameraButton: ToggleButton = ToggleButton(self)
        self.microscopeCameraButton.setText("Mic Cam")
        self.microscopeCameraButton.setStatusTip("Toggle microscope camera power")
        self.microscopeCameraButton.toggled.connect(self.microscope_camera_toggled.emit)

        self.microscopeControlButton: ToggleButton = ToggleButton(self)
        self.microscopeControlButton.setText("Mic Ctrl")
        self.microscopeControlButton.setStatusTip("Toggle microscope control")
        self.microscopeControlButton.toggled.connect(self.microscope_control_toggled.emit)

        self.probecardLightButton: ToggleButton = ToggleButton(self)
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setStatusTip("Toggle probe card light")
        self.probecardLightButton.toggled.connect(self.probecard_light_toggled.emit)

        self.probecardCameraButton: ToggleButton = ToggleButton(self)
        self.probecardCameraButton.setText("PC Cam")
        self.probecardCameraButton.setStatusTip("Toggle probe card camera power")
        self.probecardCameraButton.toggled.connect(self.probecard_camera_toggled.emit)

        self.pidControlButton: ToggleButton = ToggleButton(self)
        self.pidControlButton.setText("PID Control")
        self.pidControlButton.setStatusTip("Toggle PID control")
        self.pidControlButton.toggled.connect(self.pid_control_toggled.emit)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.laserSensorButton, 0, 0)
        layout.addWidget(self.microscopeCameraButton, 1, 0)
        layout.addWidget(self.boxLightButton, 0, 1)
        layout.addWidget(self.probecardCameraButton, 1, 1)
        layout.addWidget(self.microscopeLightButton, 0, 2)
        layout.addWidget(self.microscopeControlButton, 1, 2)
        layout.addWidget(self.probecardLightButton, 0, 3)
        layout.addWidget(self.pidControlButton, 1, 3)

    def setLaserSensorEnabled(self, enabled: bool) -> None:
        self.laserSensorButton.setChecked(enabled)

    def setBoxLightEnabled(self, enabled: bool) -> None:
        self.boxLightButton.setChecked(enabled)

    def setMicroscopeLightEnabled(self, enabled: bool) -> None:
        self.microscopeLightButton.setChecked(enabled)

    def setMicroscopeCameraEnabled(self, enabled: bool) -> None:
        self.microscopeCameraButton.setChecked(enabled)

    def setMicroscopeControlEnabled(self, enabled: bool) -> None:
        self.microscopeControlButton.setChecked(enabled)

    def setProbecardLightEnabled(self, enabled: bool) -> None:
        self.probecardLightButton.setChecked(enabled)

    def setProbecardCameraEnabled(self, enabled: bool) -> None:
        self.probecardCameraButton.setChecked(enabled)

    def setPidControlEnabled(self, enabled: bool) -> None:
        self.pidControlButton.setChecked(enabled)


class Dashboard(QtWidgets.QWidget):

    lockedStateChanged = QtCore.pyqtSignal(bool)
    summary = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()

    currentItemChanged = QtCore.pyqtSignal(object)
    itemTriggered = QtCore.pyqtSignal(object)
    sequenceStarted = QtCore.pyqtSignal()

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context

        # Layout

        self.noticeLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.noticeLabel.setText(
            "Temporary Probecard Z-Limit applied. "
            "Revert after finishing current measurements."
        )
        self.noticeLabel.setStyleSheet("QLabel{color: black; background-color: yellow; padding: 4px; border-radius: 4px;}")
        self.noticeLabel.setVisible(False)

        self.sequence_widget: SequenceGroupBox = SequenceGroupBox(self)
        self.sequence_widget.sequenceTreeWidget.currentItemChanged.connect(self.showCurrentItem)
        self.sequence_widget.sequenceTreeWidget.currentItemChanged.connect(lambda current, _: self.currentItemChanged.emit(current))
        self.sequence_widget.sequenceTreeWidget.itemDoubleClicked.connect(lambda item, _: self.itemTriggered.emit(item))
        self.sequence_widget.resetButton.clicked.connect(self.resetSequenceState)

        self.sequenceTreeWidget = self.sequence_widget.sequenceTreeWidget

        # Environment Controls

        self.environmentGroupBox = EnvironmentGroupBox(self)
        self.environmentGroupBox.toggled.connect(self.setEnvironmentEnabled)
        self.environmentGroupBox.laser_sensor_toggled.connect(self.on_laser_sensor_toggled)
        self.environmentGroupBox.box_light_toggled.connect(self.on_box_light_toggled)
        self.environmentGroupBox.microscope_light_toggled.connect(self.on_microscope_light_toggled)
        self.environmentGroupBox.microscope_camera_toggled.connect(self.on_microscope_camera_toggled)
        self.environmentGroupBox.microscope_control_toggled.connect(self.on_microscope_control_toggled)
        self.environmentGroupBox.probecard_light_toggled.connect(self.on_probecard_light_toggled)
        self.environmentGroupBox.probecard_camera_toggled.connect(self.on_probecard_camera_toggled)
        self.environmentGroupBox.pid_control_toggled.connect(self.on_pid_control_toggled)

        # Table controls

        self.tableGroupBox: TableGroupBox = TableGroupBox(self)
        self.tableGroupBox.toggled.connect(self.setTableEnabled)
        self.tableGroupBox.joystickToggled.connect(self.setJoystickEnabled)
        self.tableGroupBox.alignmentClicked.connect(self.showAlignmentDialog)

        # Operator

        self.operatorWidget: OperatorWidget = OperatorWidget(self)

        # Working directory

        self.outputWidget: WorkingDirectoryWidget = WorkingDirectoryWidget(self)

        # Controls

        self.controlWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        controlLayout = QtWidgets.QGridLayout(self.controlWidget)
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.sequence_widget, 0, 0, 1, 2)
        controlLayout.addWidget(self.tableGroupBox, 1, 0, 1, 2)
        controlLayout.addWidget(self.environmentGroupBox, 2, 0, 1, 2)
        controlLayout.addWidget(self.operatorWidget, 3, 0)
        controlLayout.addWidget(self.outputWidget, 3, 1)
        controlLayout.setRowStretch(0, 1)
        controlLayout.setColumnStretch(0, 3)
        controlLayout.setColumnStretch(1, 7)

        # Tabs

        self.measurementWidget: MeasurementWidget = MeasurementWidget(self)
        self.measurementWidget.restoreClicked.connect(self.restoreDefaults)

        self.environmentWidget: EnvironmentWidget = EnvironmentWidget(self)

        self.statusWidget: StatusWidget = StatusWidget(self)
        self.statusWidget.reloadClicked.connect(self.on_status_start)

        self.panels = self.measurementWidget.panels

        self.measurementWidget.moveRequested.connect(self.on_table_move)
        self.measurementWidget.contactRequested.connect(self.on_table_contact)
        self.measurementWidget.sampleChanged.connect(self.sampleChanged)

        self.tabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.measurementWidget, "Measurement")
        self.tabWidget.addTab(self.environmentWidget, "Environment")
        self.tabWidget.addTab(self.statusWidget, "Status")

        self.splitter: QtWidgets.QSplitter = QtWidgets.QSplitter(self)
        self.splitter.addWidget(self.controlWidget)
        self.splitter.addWidget(self.tabWidget)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 9)
        self.splitter.setChildrenCollapsible(False)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.noticeLabel)
        layout.addWidget(self.splitter)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)

        # Setup process callbacks

        self.context.status_process.finished = self.on_status_finished

        self.context.table_process.joystick_changed.connect(self.on_table_joystick_changed)
        self.context.table_process.position_changed.connect(self.on_table_position_changed)
        self.context.table_process.caldone_changed.connect(self.on_table_calibration_changed)
        self.context.table_process.relative_move_finished.connect(self.on_table_finished)
        self.context.table_process.absolute_move_finished.connect(self.on_table_finished)

        self.context.measure_process.finished = self.finishSequence
        self.context.measure_process.measurement_state = self.on_measurement_state
        self.context.measure_process.measurement_reset = self.on_measurement_reset
        self.context.measure_process.save_to_image = self.on_save_to_image

    @handle_exception
    def readSettings(self):
        self.sequence_widget.readSettings()
        self.environmentGroupBox.setChecked(settings.use_environ())
        settings_ = QtCore.QSettings()
        state = settings_.value("dashboard/splitter/state", QtCore.QByteArray(), QtCore.QByteArray)
        self.splitter.restoreState(state)
        self.tableGroupBox.readSettings()
        self.operatorWidget.readSettings()
        self.outputWidget.readSettings()

    @handle_exception
    def writeSettings(self):
        self.sequence_widget.writeSettings()
        settings.set_use_environ(self.isEnvironmentEnabled())
        settings.set_use_table(self.isTableEnabled())
        settings_ = QtCore.QSettings()
        state = self.splitter.saveState()
        settings_.setValue("dashboard/splitter/state", state)
        settings_.setValue("dashboard/useEnvironment", self.isEnvironmentEnabled())
        settings_.setValue("dashboard/useTable", self.isTableEnabled())
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()

    def addTabWidget(self, widget, title: str) -> None:
        self.tabWidget.addTab(widget, title)

    def removeTabWidget(self, widget) -> None:
        index: int = self.tabWidget.indexOf(widget)
        self.tabWidget.removeTab(index)

    def sampleItems(self) -> List[SampleTreeItem]:
        """Return list of sample items from sequence."""
        return self.sequenceTreeWidget.sampleItems()

    def sample_name(self):
        """Return sample name."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.name
        if isinstance(item, ContactTreeItem):
            return item.sample.name
        if isinstance(item, SampleTreeItem):
            return item.name
        return ""

    def sample_type(self):
        """Return sample type."""
        item = self.sequenceTreeWidget.currentItem()
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
            return self.context.table_process.get_cached_position()
        return Position()

    def isEnvironmentEnabled(self) -> bool:
        """Return True if environment box enabled."""
        return self.environmentGroupBox.isChecked()

    def isTableEnabled(self) -> bool:
        """Return True if table control enabled."""
        return self.tableGroupBox.isChecked()

    def operator(self):
        """Return current operator."""
        return self.operatorWidget.operator()

    def outputDir(self) -> str:
        """Return output base path."""
        return os.path.realpath(self.outputWidget.currentLocation())

    # Callbacks

    def setLocked(self, locked: bool) -> None:
        self.environmentGroupBox.setEnabled(not locked)
        self.tableGroupBox.setEnabled(not locked)
        self.sequence_widget.setLocked(locked)
        self.outputWidget.setEnabled(not locked)
        self.operatorWidget.setEnabled(not locked)
        self.measurementWidget.setLocked(locked)
        self.statusWidget.setLocked(locked)
        self.lockedStateChanged.emit(locked)

    def setNoticeVisible(self, state: bool) -> None:
        self.noticeLabel.setVisible(state)

    # Sequence control

    def showCurrentItem(self, item, previous):
        self.panels.store()
        self.panels.unmount()
        self.panels.clearReadings()
        self.panels.setCurrentIndex(0)
        self.measurementWidget.setControlsVisible(False)
        if isinstance(item, SampleTreeItem):
            panel = self.panels.findPanel("sample")
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(item)
        if isinstance(item, ContactTreeItem):
            panel = self.panels.findPanel("contact")
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(item)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.findPanel(item.type)
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(item)
                self.measurementWidget.setControlsVisible(True)
        # Show measurement tab
        self.tabWidget.setCurrentWidget(self.measurementWidget)


    def sampleChanged(self, item):
        self.sequenceTreeWidget.resizeColumns()

    # Contcat table controls

    @handle_exception
    def on_table_move(self, contact):
        if self.isTableEnabled():
            self.setLocked(True)
            self.measurementWidget.setLocked(True)
            x, y, z = contact.position()
            z = safe_z_position(z)
            self.context.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def on_table_contact(self, contact):
        if self.isTableEnabled():
            self.setLocked(True)
            self.measurementWidget.setLocked(True)
            x, y, z = contact.position()
            self.context.table_process.safe_absolute_move(x, y, z)

    def on_table_finished(self):
        current_item = self.sequenceTreeWidget.currentItem()
        if isinstance(current_item, SampleTreeItem):
            panel = self.panels.findPanel("sample")
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(current_item)
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.findPanel("contact")
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(current_item)

    @QtCore.pyqtSlot()
    def startAll(self) -> None:
        try:
            sample_items = SamplesItem(self.sampleItems())
            dialog = SequenceStartDialog(
                "<b>Are you sure to start all enabled sequences for all enabled samples?</b>",
            )
            dialog.setTableEnabled(self.isTableEnabled())
            self.operatorWidget.writeSettings()
            self.outputWidget.writeSettings()
            dialog.readSettings()
            if dialog.exec() != dialog.Accepted:
                return
            dialog.writeSettings()
            self.operatorWidget.readSettings()
            self.outputWidget.readSettings()
            self.startSequence(
                sample_items,
                move_to_contact=dialog.isMoveToContact(),
                move_to_after_position=dialog.moveToPosition()
            )
        except Exception as exc:
            logger.exception(exc)
            showException(exc)

    @QtCore.pyqtSlot()
    def startCurrent(self) -> None:
        try:
            # Store settings
            self.writeSettings()
            current_item = self.sequenceTreeWidget.currentItem()
            if isinstance(current_item, MeasurementTreeItem):
                contact_item = current_item.contact
                if not showQuestion(
                    title="Run Measurement",
                    text=f"Are you sure to run measurement {current_item.name!r} for {contact_item.name!r}?",
                ):
                    return
                self.startSequence(current_item)
            elif isinstance(current_item, ContactTreeItem):
                dialog = SequenceStartDialog(
                    f"<b>Are you sure to start sequence {current_item.name!r}?</b>",
                )
                dialog.setTableEnabled(self.isTableEnabled())
                self.operatorWidget.writeSettings()
                self.outputWidget.writeSettings()
                dialog.readSettings()
                if dialog.exec() != dialog.Accepted:
                    return
                dialog.writeSettings()
                self.operatorWidget.readSettings()
                self.outputWidget.readSettings()
                self.startSequence(
                    current_item,
                    move_to_contact=dialog.isMoveToContact(),
                    move_to_after_position=dialog.moveToPosition()
                )
            elif isinstance(current_item, SampleTreeItem):
                dialog = SequenceStartDialog(
                    f"<b>Are you sure to start all enabled sequences for {current_item.name!r}?</b>",
                )
                dialog.setTableEnabled(self.isTableEnabled())
                self.operatorWidget.writeSettings()
                self.outputWidget.writeSettings()
                dialog.readSettings()
                if dialog.exec() != dialog.Accepted:
                    return
                dialog.writeSettings()
                self.operatorWidget.readSettings()
                self.outputWidget.readSettings()
                self.startSequence(
                    current_item,
                    move_to_contact=dialog.isMoveToContact(),
                    move_to_after_position=dialog.moveToPosition()
                )
        except Exception as exc:
            logger.exception(exc)
            showException(exc)

    def startSequence(self, context, move_to_contact=False, move_to_after_position=None) -> None:
        # Create output directory
        self.panels.store()
        self.panels.unmount()
        self.panels.clearReadings()
        create_dir(self.outputDir())
        self.switch_off_lights()
        self.sync_environment_controls()
        measure = self.context.measure_process
        measure.context = context
        measure.set("table_position", self.table_position())
        measure.set("operator", self.operator())
        measure.set("output_dir", self.outputDir())
        measure.set("write_logfiles", settings.value("write_logfiles", True, bool))
        measure.set("use_environ", self.isEnvironmentEnabled())
        measure.set("use_table", self.isTableEnabled())
        measure.set("serialize_json", settings.value("export_json", True, bool))
        measure.set("serialize_txt", settings.value("export_txt", True, bool))
        measure.set("move_to_contact", move_to_contact)
        measure.set("move_to_after_position", move_to_after_position)
        measure.set("contact_delay", settings.value("table_contact_delay", 0, float))
        measure.set("retry_contact_count", settings.retry_contact_count())
        measure.set("retry_measurement_count", settings.retry_measurement_count())
        measure.set("retry_contact_overdrive", settings.retry_contact_overdrive())
        measure.set("matrix_instrument", settings.matrix_instrument)
        measure.set("vsrc_instrument", settings.vsrc_instrument)
        measure.set("hvsrc_instrument", settings.hvsrc_instrument)
        def show_measurement(item):
            item.setSelectable(True)
            item.series.clear()
            item.setForeground(0, QtGui.QColor("blue"))
            self.sequenceTreeWidget.scrollToItem(item)
            self.panels.unmount()
            self.panels.setCurrentIndex(0)
            self.panels.clearReadings()
            panel = self.panels.findPanel(item.type)
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(item)
                measure.reading = panel.append_reading
                measure.update = panel.update_readings
                measure.append_analysis = panel.append_analysis
                measure.state = panel.state
        def hide_measurement(item):
            item.setSelectable(False)
            item.setForeground(0, QtGui.QColor())
        measure.show_measurement = show_measurement
        measure.hide_measurement = hide_measurement
        measure.push_summary = self.summary.emit
        measure.start()
        self.sequenceStarted.emit()

    def on_measurement_state(self, item, state=None):
        item.state = state
        self.sequenceTreeWidget.resizeColumns()

    def on_measurement_reset(self, item):
        item.reset()
        self.sequenceTreeWidget.resizeColumns()

    def on_save_to_image(self, item, filename):
        plot_png = settings.value("png_plots", False, bool)
        panel = self.panels.findPanel(item.type)
        if panel and plot_png:
            panel.saveToImage(filename)

    def stopSequence(self):
        self.sequence_widget.stop()
        self.context.measure_process.stop()

    def finishSequence(self):
        self.sync_environment_controls()
        self.finished.emit()

    @handle_exception
    def resetSequenceState(self, state) -> None:
        if showQuestion(
            title="Reset State",
            text="Do you want to reset all sequence states?",
        ):
            current_item = self.sequenceTreeWidget.currentItem()
            self.panels.unmount()
            self.panels.clearReadings()
            self.panels.setCurrentIndex(0)
            for item in self.sampleItems():
                item.reset()
                for contact in item.children():
                    for measurement in contact.children():
                        measurement.setRemeasureCount(0)
                        measurement.setRecontactCount(0)
            if current_item is not None:
                panel = self.panels.findPanel(current_item.type)
                if panel:
                    self.panels.setCurrentWidget(panel)
                    panel.mount(current_item)

    # Measurement control

    def restoreDefaults(self):
        if showQuestion(
            title="Restore Defaults",
            text="Do you want to restore to default parameters?",
        ):
            measurement = self.sequenceTreeWidget.currentItem()
            panel = self.panels.findPanel(measurement.type)
            if panel:
                panel.restore()

    def on_status_start(self):
        self.panels.setLocked(True)
        self.statusWidget.reset()
        self.context.status_process.set("matrix_instrument", settings.matrix_instrument)
        self.context.status_process.set("use_environ", self.isEnvironmentEnabled())
        self.context.status_process.set("use_table", self.isTableEnabled())
        self.context.status_process.start()
        # Fix: stay in status tab
        self.tabWidget.setCurrentWidget(self.statusWidget)
        self.sequenceStarted.emit()

    def on_status_finished(self):
        self.statusWidget.updateStatus(self.context.status_process)
        self.finished.emit()

    # Table calibration

    @handle_exception
    def setJoystickEnabled(self, enabled: bool) -> None:
        self.context.table_process.enable_joystick(enabled)

    def on_table_joystick_changed(self, state: bool) -> None:
        self.tableGroupBox.setJoystickEnabled(state)

    def on_table_position_changed(self, position: Position) -> None:
        self.tableGroupBox.setPosition(position)

    def on_table_calibration_changed(self, position: Position) -> None:
        self.tableGroupBox.setCalibration(position)
        panel = self.panels.findPanel("contact")
        if panel:
            panel.setTableEnabled(self.isTableEnabled() and self.tableGroupBox.isCalibrationValid)

    @handle_exception
    def showAlignmentDialog(self) -> None:
        self.context.table_process.enable_joystick(False)
        dialog = AlignmentDialog(self.context.table_process, self.context.contact_quality_process)
        dialog.readSettings()
        dialog.load_samples(self.sampleItems())
        if self.isEnvironmentEnabled():
            # TODO !!!
            with self.context.environ_process as environ:
                pc_data = environ.pc_data()
                dialog.update_safety(laser_sensor=pc_data.relay_states.laser_sensor)
                dialog.setProbecardLightEnabled(pc_data.relay_states.probecard_light)
                dialog.setMicroscopeLightEnabled(pc_data.relay_states.microscope_light)
                dialog.setBoxLightEnabled(pc_data.relay_states.box_light)
            dialog.setLightsEnabled(True)
            dialog.probecardLightToggled.connect(self.on_probecard_light_toggled)
            dialog.microscopeLightToggled.connect(self.on_microscope_light_toggled)
            dialog.boxLightToggled.connect(self.on_box_light_toggled)
        dialog.exec()
        self.context.contact_quality_process.finished = None  # TODO
        self.context.contact_quality_process.failed = None
        self.context.contact_quality_process.reading = None
        self.context.contact_quality_process.stop()
        self.context.contact_quality_process.join()
        dialog.writeSettings()
        dialog.update_samples()  # updates loaded samples
        # Prevent glitch
        current_item = self.sequenceTreeWidget.currentItem()
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.findPanel("contact")
            if panel:
                self.panels.setCurrentWidget(panel)
                panel.mount(current_item)
        self.sync_table_controls()
        # Store settings
        self.writeSettings()

    @handle_exception
    def on_laser_sensor_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_toggled(self, state):
        with self.context.environ_process as environment:
            environment.set_pid_control(state)

    @handle_exception
    def switch_off_lights(self):
        if self.isEnvironmentEnabled():
            with self.context.environ_process as environment:
                if environment.has_lights():
                    environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.isEnvironmentEnabled():
            with self.context.environ_process as environment:
                environment.request_pc_data()
        else:
            self.environmentWidget.setEnabled(False)

    def setEnvironmentData(self, pc_data) -> None:
        self.environmentGroupBox.setLaserSensorEnabled(pc_data.relay_states.laser_sensor)
        self.environmentGroupBox.setBoxLightEnabled(pc_data.relay_states.box_light)
        self.environmentGroupBox.setMicroscopeLightEnabled(pc_data.relay_states.microscope_light)
        self.environmentGroupBox.setMicroscopeCameraEnabled(pc_data.relay_states.microscope_camera)
        self.environmentGroupBox.setMicroscopeControlEnabled(pc_data.relay_states.microscope_control)
        self.environmentGroupBox.setProbecardLightEnabled(pc_data.relay_states.probecard_light)
        self.environmentGroupBox.setProbecardCameraEnabled(pc_data.relay_states.probecard_camera)
        self.environmentGroupBox.setPidControlEnabled(pc_data.pid_status)
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
        self.context.table_process.enabled = enabled
        self.on_table_position_changed(Position())
        self.on_table_calibration_changed(Position())
        if enabled:
            self.context.table_process.status()

    def setEnvironmentEnabled(self, state: bool) -> None:
        if state:
            self.context.environ_process.start()
            self.sync_environment_controls()
        else:
            self.context.environ_process.stop()

    def setTableEnabled(self, state: bool) -> None:
        if state:
            self.context.table_process.start()
            self.context.table_process.enable_joystick(False)
        else:
            self.context.table_process.stop()
        self.sync_table_controls()

    def readSequence(self, filename: str) -> None:
        with open(filename, "rt") as fp:
            sequence = load_sequence_tree(fp)
        self.sequenceTreeWidget.clear()
        for kwargs in sequence:
            item: SampleTreeItem = SampleTreeItem()
            self.sequenceTreeWidget.addTopLevelItem(item)
            item.setExpanded(False)
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logger.error(exc)
        if self.sequenceTreeWidget.topLevelItemCount():
            self.sequenceTreeWidget.setCurrentItem(self.sequenceTreeWidget.topLevelItem(0))
        self.sequenceTreeWidget.resizeColumns()

    def writeSequence(self, filename: str) -> None:
        # Auto filename extension
        if os.path.splitext(filename)[-1] not in [".json"]:
            filename = f"{filename}.json"
            if os.path.exists(filename):
                if not showQuestion(
                    title="Overwrite?",
                    text=f"Do you want to overwrite existing file {filename}?",
                ):
                    return
        # Create sequence
        sequence = []
        for item in self.sampleItems():
            sequence.append(item.to_settings())
        with open(filename, "wt") as fp:
            dump_sequence_tree(sequence, fp)

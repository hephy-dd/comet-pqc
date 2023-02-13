from typing import Dict, List, Optional

from PyQt5 import QtCore, QtWidgets

from ..metricwidget import MetricWidget
from comet_pqc.utils import format_metric, format_switch

__all__ = [
    "MatrixMixin",
    "HVSourceMixin",
    "VSourceMixin",
    "ElectrometerMixin",
    "LCRMixin",
    "EnvironmentMixin"
]

NO_VALUE = "---"


def encode_list(channels: List[str]) -> str:
    return ", ".join(map(format, channels))


def decode_list(text: str) -> List[str]:
    return list(map(str.strip, text.split(",")))


class ListEdit(QtWidgets.QLineEdit):
    """Overloaded text input to handle matrix channel list."""

    def value(self) -> List[str]:
        return decode_list(self.text())

    def setValue(self, value: List[str]) -> None:
        self.setText(encode_list(value or []))


class MatrixMixin:
    """Base class for matrix switching panels."""

    def __init__(self, panel) -> None:
        self.enableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.enableCheckBox.setText("Enable Switching")
        self.enableCheckBox.setStatusTip("Enables switching matrix")

        self.channelsListEdit: ListEdit = ListEdit()
        self.channelsListEdit.setStatusTip("Matrix card switching channels, comma separated list")

        self.matrixGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.matrixGroupBox.setTitle("Matrix")

        matrixGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.matrixGroupBox)
        matrixGroupBoxLayout.addWidget(self.enableCheckBox)
        matrixGroupBoxLayout.addWidget(QtWidgets.QLabel("Channels"))
        matrixGroupBoxLayout.addWidget(self.channelsListEdit)
        matrixGroupBoxLayout.addStretch()

        self.matrixWidget: QtWidgets.QWidget = QtWidgets.QWidget()

        matrixWidgetLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.matrixWidget)
        matrixWidgetLayout.addWidget(self.matrixGroupBox)
        matrixWidgetLayout.addStretch()

        panel.controlTabWidget.addTab(self.matrixWidget, "Matrix")

        # Bindings

        panel.bind("matrix_enable", self.enableCheckBox, True)
        panel.bind("matrix_channels", self.channelsListEdit, [])


class HVSourceMixin:
    """Mixin class providing default controls and status for HV Source."""

    def __init__(self, panel) -> None:
        self.senseModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.senseModeComboBox.addItem("local", "local")
        self.senseModeComboBox.addItem("remote", "remote")

        self.routeTerminalComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.routeTerminalComboBox.addItem("front", "front")
        self.routeTerminalComboBox.addItem("rear", "rear")

        def toggle_hvsrc_filter(state: int) -> None:
            enabled: bool = state == QtCore.Qt.Checked
            self.filterCountSpinBox.setEnabled(enabled)
            self.filterCountLabel.setEnabled(enabled)
            self.filterTypeComboBox.setEnabled(enabled)
            self.filterTypeLabel.setEnabled(enabled)

        self.filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.stateChanged.connect(toggle_hvsrc_filter)

        self.filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel: QtWidgets.QLabel = QtWidgets.QLabel("Count")

        self.filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItem("repeat", "repeat")
        self.filterTypeComboBox.addItem("moving", "moving")

        self.filterTypeLabel: QtWidgets.QLabel = QtWidgets.QLabel("Type")

        def toggle_hvsrc_source_voltage_autorange(state: int) -> None:
            enabled: bool = state == QtCore.Qt.Checked
            self.hvsrcRangeSpinBox.setEnabled(not enabled)

        self.hvsrcAutorangeCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.hvsrcAutorangeCheckBox.setText("Autorange")
        self.hvsrcAutorangeCheckBox.stateChanged.connect(toggle_hvsrc_source_voltage_autorange)

        self.hvsrcRangeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.hvsrcRangeSpinBox.setRange(-2200, +2200)
        self.hvsrcRangeSpinBox.setDecimals(1)
        self.hvsrcRangeSpinBox.setSuffix(" V")

        toggle_hvsrc_filter(QtCore.Qt.Unchecked)
        toggle_hvsrc_source_voltage_autorange(QtCore.Qt.Unchecked)

        self.statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusVoltageLineEdit.setReadOnly(True)
        self.statusVoltageLineEdit.setText(NO_VALUE)

        self.statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusCurrentLineEdit.setReadOnly(True)
        self.statusCurrentLineEdit.setText(NO_VALUE)

        self.statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusOutputLineEdit.setReadOnly(True)
        self.statusOutputLineEdit.setText(NO_VALUE)

        self.hvsrcStatusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.hvsrcStatusGroupBox.setTitle("HV Source Status")

        hvsrcStatusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.hvsrcStatusGroupBox)
        hvsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        hvsrcStatusGroupBoxLayout.addWidget(self.statusVoltageLineEdit, 1, 0)
        hvsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        hvsrcStatusGroupBoxLayout.addWidget(self.statusCurrentLineEdit, 1, 1)
        hvsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        hvsrcStatusGroupBoxLayout.addWidget(self.statusOutputLineEdit, 1, 2)

        panel.statusWidget.layout().addWidget(self.hvsrcStatusGroupBox)

        self.filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        self.voltageRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.voltageRangeGroupBox.setTitle("Source Voltage Range")

        voltageRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.voltageRangeGroupBox)
        voltageRangeGroupBoxLayout.addWidget(self.hvsrcAutorangeCheckBox)
        voltageRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Range"))
        voltageRangeGroupBoxLayout.addWidget(self.hvsrcRangeSpinBox)
        voltageRangeGroupBoxLayout.addStretch()

        self.optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.senseModeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Route Terminal"))
        optionsGroupBoxLayout.addWidget(self.routeTerminalComboBox)
        optionsGroupBoxLayout.addStretch()

        self.hvsrcWidget: QtWidgets.QWidget = QtWidgets.QWidget()

        hvsrcWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.hvsrcWidget)
        hvsrcWidgetLayout.addWidget(self.filterGroupBox)
        hvsrcWidgetLayout.addWidget(self.voltageRangeGroupBox)
        hvsrcWidgetLayout.addWidget(self.optionsGroupBox)

        hvsrcWidgetLayout.setStretch(0, 1)
        hvsrcWidgetLayout.setStretch(1, 1)
        hvsrcWidgetLayout.setStretch(2, 1)

        panel.controlTabWidget.addTab(self.hvsrcWidget, "HV Source")

        panel.addStateHandler(self.updateState)

        # Bindings

        panel.bind("hvsrc_sense_mode", self.senseModeComboBox, "local")
        panel.bind("hvsrc_route_terminal", self.routeTerminalComboBox, "rear")
        panel.bind("hvsrc_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("hvsrc_filter_count", self.filterCountSpinBox, 10)
        panel.bind("hvsrc_filter_type", self.filterTypeComboBox, "repeat")
        panel.bind("hvsrc_source_voltage_autorange_enable", self.hvsrcAutorangeCheckBox, True)
        panel.bind("hvsrc_source_voltage_range", self.hvsrcRangeSpinBox, 20, unit="V")

        panel.bind("status_hvsrc_voltage", self.statusVoltageLineEdit, NO_VALUE)
        panel.bind("status_hvsrc_current", self.statusCurrentLineEdit, NO_VALUE)
        panel.bind("status_hvsrc_output", self.statusOutputLineEdit, NO_VALUE)

    def updateState(self, state: Dict) -> None:
        if "hvsrc_voltage" in state:
            value = state.get("hvsrc_voltage")
            self.statusVoltageLineEdit.setText(format_metric(value, "V"))
        if "hvsrc_current" in state:
            value = state.get("hvsrc_current")
            self.statusCurrentLineEdit.setText(format_metric(value, "A"))
        if "hvsrc_output" in state:
            value = state.get("hvsrc_output")
            self.statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))


class VSourceMixin:
    """Mixin class providing default controls and status for V Source."""

    def __init__(self, panel) -> None:
        self.senseModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.senseModeComboBox.addItem("local", "local")
        self.senseModeComboBox.addItem("remote", "remote")

        def toggle_vsrc_filter(state: int) -> None:
            enabled: bool = state == QtCore.Qt.Checked
            self.filterCountSpinBox.setEnabled(enabled)
            self.filterCountLabel.setEnabled(enabled)
            self.filterTypeComboBox.setEnabled(enabled)
            self.filterTypeLabel.setEnabled(enabled)

        self.filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.stateChanged.connect(toggle_vsrc_filter)

        self.filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel: QtWidgets.QLabel = QtWidgets.QLabel("Count")

        self.filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItem("repeat", "repeat")
        self.filterTypeComboBox.addItem("moving", "moving")

        self.filterTypeLabel: QtWidgets.QLabel = QtWidgets.QLabel("Type")

        toggle_vsrc_filter(QtCore.Qt.Unchecked)

        self.statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusVoltageLineEdit.setReadOnly(True)
        self.statusVoltageLineEdit.setText(NO_VALUE)

        self.statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusCurrentLineEdit.setReadOnly(True)
        self.statusCurrentLineEdit.setText(NO_VALUE)

        self.statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusOutputLineEdit.setReadOnly(True)
        self.statusOutputLineEdit.setText(NO_VALUE)

        self.vsrcStatusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.vsrcStatusGroupBox.setTitle("V Source Status")

        vsrcStatusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.vsrcStatusGroupBox)
        vsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        vsrcStatusGroupBoxLayout.addWidget(self.statusVoltageLineEdit, 1, 0)
        vsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        vsrcStatusGroupBoxLayout.addWidget(self.statusCurrentLineEdit, 1, 1)
        vsrcStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        vsrcStatusGroupBoxLayout.addWidget(self.statusOutputLineEdit, 1, 2)

        panel.statusWidget.layout().addWidget(self.vsrcStatusGroupBox)

        self.filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        self.optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.senseModeComboBox)
        optionsGroupBoxLayout.addStretch()

        self.vsrcWidget: QtWidgets.QWidget = QtWidgets.QWidget()

        vsrcWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.vsrcWidget)
        vsrcWidgetLayout.addWidget(self.filterGroupBox)
        vsrcWidgetLayout.addWidget(self.optionsGroupBox)
        vsrcWidgetLayout.addStretch()

        vsrcWidgetLayout.setStretch(0, 1)
        vsrcWidgetLayout.setStretch(1, 1)
        vsrcWidgetLayout.setStretch(2, 1)

        panel.controlTabWidget.addTab(self.vsrcWidget, "V Source")

        panel.addStateHandler(self.updateState)

        # Bindings

        panel.bind("vsrc_sense_mode", self.senseModeComboBox, "local")
        panel.bind("vsrc_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("vsrc_filter_count", self.filterCountSpinBox, 10)
        panel.bind("vsrc_filter_type", self.filterTypeComboBox, "repeat")

        panel.bind("status_vsrc_voltage", self.statusVoltageLineEdit, NO_VALUE)
        panel.bind("status_vsrc_current", self.statusCurrentLineEdit, NO_VALUE)
        panel.bind("status_vsrc_output", self.statusOutputLineEdit, NO_VALUE)

    def updateState(self, state: Dict) -> None:
        if "vsrc_voltage" in state:
            value = state.get("vsrc_voltage")
            self.statusVoltageLineEdit.setText(format_metric(value, "V"))
        if "vsrc_current" in state:
            value = state.get("vsrc_current")
            self.statusCurrentLineEdit.setText(format_metric(value, "A"))
        if "vsrc_output" in state:
            value = state.get("vsrc_output")
            self.statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))


class ElectrometerMixin:
    """Mixin class providing default controls and status for Electrometer."""

    def __init__(self, panel) -> None:
        def toggle_elm_filter(state: int) -> None:
            enabled: bool = state == QtCore.Qt.Checked
            self.filterCountSpinBox.setEnabled(enabled)
            self.filterCountLabel.setEnabled(enabled)
            self.filterTypeComboBox.setEnabled(enabled)
            self.filterTypeLabel.setEnabled(enabled)

        self.filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.stateChanged.connect(toggle_elm_filter)

        self.filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel: QtWidgets.QLabel = QtWidgets.QLabel("Count")

        self.filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItem("repeat", "repeat")
        self.filterTypeComboBox.addItem("moving", "moving")

        self.filterTypeLabel: QtWidgets.QLabel = QtWidgets.QLabel("Type")

        self.zeroCorrCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.zeroCorrCheckBox.setText("Zero Correction")

        self.integrationRateSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.integrationRateSpinBox.setRange(0, 100)
        self.integrationRateSpinBox.setDecimals(2)
        self.integrationRateSpinBox.setSuffix(" Hz")

        def toggle_elm_current_autorange(state: int) -> None:
            enabled: bool = state == QtCore.Qt.Checked
            self.currentRangeMetric.setEnabled(not enabled)
            self.currentAutorangeMinMetric.setEnabled(enabled)
            self.currentAutorangeMaxMetric.setEnabled(enabled)

        self.currentRangeMetric: MetricWidget = MetricWidget("A")
        self.currentRangeMetric.setMinimum(0)
        self.currentRangeMetric.setDecimals(3)
        self.currentRangeMetric.setPrefixes("munp")

        self.autorangeEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.autorangeEnableCheckBox.setText("Enable")
        self.autorangeEnableCheckBox.stateChanged.connect(toggle_elm_current_autorange)

        self.currentAutorangeMinMetric: MetricWidget = MetricWidget("A")
        self.currentAutorangeMinMetric.setMinimum(0)
        self.currentAutorangeMinMetric.setDecimals(3)
        self.currentAutorangeMinMetric.setPrefixes("munp")

        self.currentAutorangeMaxMetric: MetricWidget = MetricWidget("A")
        self.currentAutorangeMaxMetric.setMinimum(0)
        self.currentAutorangeMaxMetric.setDecimals(3)
        self.currentAutorangeMaxMetric.setPrefixes("munp")

        toggle_elm_filter(QtCore.Qt.Unchecked)
        toggle_elm_current_autorange(QtCore.Qt.Unchecked)

        self.statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusCurrentLineEdit.setReadOnly(True)
        self.statusCurrentLineEdit.setText(NO_VALUE)

        self.elmStatusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.elmStatusGroupBox.setTitle("Electrometer Status")

        elmStatusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.elmStatusGroupBox)
        elmStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        elmStatusGroupBoxLayout.addWidget(self.statusCurrentLineEdit, 1, 1)
        elmStatusGroupBoxLayout.setColumnStretch(1, 2)

        panel.statusWidget.layout().addWidget(self.elmStatusGroupBox)

        self.filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        self.rangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.rangeGroupBox.setTitle("Range")

        rangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.rangeGroupBox)
        rangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Range"))
        rangeGroupBoxLayout.addWidget(self.currentRangeMetric)

        self.autoRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.autoRangeGroupBox.setTitle("Auto Range")

        autoRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.autoRangeGroupBox)
        autoRangeGroupBoxLayout.addWidget(self.autorangeEnableCheckBox)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Minimum Current"))
        autoRangeGroupBoxLayout.addWidget(self.currentAutorangeMinMetric)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum Current"))
        autoRangeGroupBoxLayout.addWidget(self.currentAutorangeMaxMetric)
        autoRangeGroupBoxLayout.addStretch()

        self.optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(self.zeroCorrCheckBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Rate"))
        optionsGroupBoxLayout.addWidget(self.integrationRateSpinBox)
        optionsGroupBoxLayout.addStretch()

        self.elmWidget: QtWidgets.QWidget = QtWidgets.QWidget()

        elmWidgetLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.elmWidget)
        elmWidgetLayout.addWidget(self.filterGroupBox, 0, 0, 2, 1)
        elmWidgetLayout.addWidget(self.rangeGroupBox, 0, 1)
        elmWidgetLayout.addWidget(self.autoRangeGroupBox, 1, 1)
        elmWidgetLayout.addWidget(self.optionsGroupBox, 0, 2, 2, 1)

        elmWidgetLayout.setRowStretch(1, 1)
        elmWidgetLayout.setColumnStretch(0, 1)
        elmWidgetLayout.setColumnStretch(1, 1)
        elmWidgetLayout.setColumnStretch(2, 1)

        panel.controlTabWidget.addTab(self.elmWidget, "Electrometer")

        panel.addStateHandler(self.updateState)

        # Bindings

        panel.bind("elm_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("elm_filter_count", self.filterCountSpinBox, 10)
        panel.bind("elm_filter_type", self.filterTypeComboBox, "repeat")
        panel.bind("elm_zero_correction", self.zeroCorrCheckBox, False)
        panel.bind("elm_integration_rate", self.integrationRateSpinBox, 50.0)
        panel.bind("elm_current_range", self.currentRangeMetric, 20e-12, unit="A")
        panel.bind("elm_current_autorange_enable", self.autorangeEnableCheckBox, False)
        panel.bind("elm_current_autorange_minimum", self.currentAutorangeMinMetric, 2.0E-11, unit="A")
        panel.bind("elm_current_autorange_maximum", self.currentAutorangeMaxMetric, 2.0E-2, unit="A")

        panel.bind("status_elm_current", self.statusCurrentLineEdit, NO_VALUE)

    def updateState(self, state: Dict) -> None:
        if "elm_current" in state:
            value = state.get("elm_current")
            self.statusCurrentLineEdit.setText(format_metric(value, "A"))


class LCRMixin:
    """Mixin class providing default controls and status for LCR Meter."""

    def __init__(self, panel) -> None:
        def change_lcr_open_correction_mode(mode: str) -> None:
            self.openCorrChannelSpinBox.setEnabled(mode == "multi")

        self.integrationTimeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.integrationTimeComboBox.addItem("short", "short")
        self.integrationTimeComboBox.addItem("medium", "medium")
        self.integrationTimeComboBox.addItem("long", "long")

        self.averagingRateSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.averagingRateSpinBox.setRange(1, 256)

        self.autoLevelControlCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.autoLevelControlCheckBox.setText("Auto Level Control")

        self.softFilterCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.softFilterCheckBox.setText("Filter STD/mean < 0.005")

        self.openCorrModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.openCorrModeComboBox.addItem("single", "single")
        self.openCorrModeComboBox.addItem("multi", "multi")
        self.openCorrModeComboBox.currentTextChanged.connect(change_lcr_open_correction_mode)

        self.openCorrChannelSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.openCorrChannelSpinBox.setRange(0, 127)

        change_lcr_open_correction_mode(self.openCorrModeComboBox.currentText())

        self.statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusVoltageLineEdit.setReadOnly(True)
        self.statusVoltageLineEdit.setText(NO_VALUE)

        self.statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusCurrentLineEdit.setReadOnly(True)
        self.statusCurrentLineEdit.setText(NO_VALUE)

        self.statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.statusOutputLineEdit.setReadOnly(True)
        self.statusOutputLineEdit.setText(NO_VALUE)

        self.lcrStatusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.lcrStatusGroupBox.setTitle("LCR Status")

        lcrStatusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.lcrStatusGroupBox)
        lcrStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        lcrStatusGroupBoxLayout.addWidget(self.statusVoltageLineEdit, 1, 0)
        lcrStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        lcrStatusGroupBoxLayout.addWidget(self.statusCurrentLineEdit, 1, 1)
        lcrStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        lcrStatusGroupBoxLayout.addWidget(self.statusOutputLineEdit, 1, 2)

        panel.statusWidget.layout().addWidget(self.lcrStatusGroupBox)

        self.openCorrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.openCorrGroupBox.setTitle("Open Correction")

        openCorrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.openCorrGroupBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Method"))
        openCorrGroupBoxLayout.addWidget(self.openCorrModeComboBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Channel"))
        openCorrGroupBoxLayout.addWidget(self.openCorrChannelSpinBox)
        openCorrGroupBoxLayout.addStretch()

        self.optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Time"))
        optionsGroupBoxLayout.addWidget(self.integrationTimeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Averaging Rate"))
        optionsGroupBoxLayout.addWidget(self.averagingRateSpinBox)
        optionsGroupBoxLayout.addWidget(self.autoLevelControlCheckBox)
        optionsGroupBoxLayout.addWidget(self.softFilterCheckBox)
        optionsGroupBoxLayout.addStretch()

        self.lcrWidget: QtWidgets.QWidget = QtWidgets.QWidget()

        lcrWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.lcrWidget)
        lcrWidgetLayout.addWidget(self.openCorrGroupBox)
        lcrWidgetLayout.addWidget(self.optionsGroupBox)
        lcrWidgetLayout.addStretch()

        lcrWidgetLayout.setStretch(0, 1)
        lcrWidgetLayout.setStretch(1, 1)
        lcrWidgetLayout.setStretch(2, 1)


        panel.controlTabWidget.addTab(self.lcrWidget, "LCR")

        panel.addStateHandler(self.updateState)

        # Bindings

        panel.bind("lcr_integration_time", self.integrationTimeComboBox, "medium")
        panel.bind("lcr_averaging_rate", self.averagingRateSpinBox, 1)
        panel.bind("lcr_auto_level_control", self.autoLevelControlCheckBox, True)
        panel.bind("lcr_soft_filter", self.softFilterCheckBox, True)
        panel.bind("lcr_open_correction_mode", self.openCorrModeComboBox, "single")
        panel.bind("lcr_open_correction_channel", self.openCorrChannelSpinBox, 0)

        panel.bind("status_lcr_voltage", self.statusVoltageLineEdit, NO_VALUE)
        panel.bind("status_lcr_current", self.statusCurrentLineEdit, NO_VALUE)
        panel.bind("status_lcr_output", self.statusOutputLineEdit, NO_VALUE)

    def updateState(self, state: Dict) -> None:
        if "lcr_voltage" in state:
            value = state.get("lcr_voltage")
            self.statusVoltageLineEdit.setText(format_metric(value, "V"))
        if "lcr_current" in state:
            value = state.get("lcr_current")
            self.statusCurrentLineEdit.setText(format_metric(value, "A"))
        if "lcr_output" in state:
            value = state.get("lcr_output")
            self.statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))


class EnvironmentMixin:
    """Mixin class providing default controls and status for Environment box."""

    def __init__(self, panel) -> None:
        self.chuckTemperatureLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.chuckTemperatureLineEdit.setReadOnly(True)
        self.chuckTemperatureLineEdit.setText(NO_VALUE)

        self.boxTemperatureLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.boxTemperatureLineEdit.setReadOnly(True)
        self.boxTemperatureLineEdit.setText(NO_VALUE)

        self.boxHumidityLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.boxHumidityLineEdit.setReadOnly(True)
        self.boxHumidityLineEdit.setText(NO_VALUE)

        self.envStatusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox()
        self.envStatusGroupBox.setTitle("LCR Status")

        envStatusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.envStatusGroupBox)
        envStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Chuck temp."), 0, 0)
        envStatusGroupBoxLayout.addWidget(self.chuckTemperatureLineEdit, 1, 0)
        envStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box temp."), 0, 1)
        envStatusGroupBoxLayout.addWidget(self.boxTemperatureLineEdit, 1, 1)
        envStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box humid."), 0, 2)
        envStatusGroupBoxLayout.addWidget(self.boxHumidityLineEdit, 1, 2)

        panel.statusWidget.layout().addWidget(self.envStatusGroupBox)

        panel.addStateHandler(self.updateState)

        # Bindings

        panel.bind("status_env_chuck_temperature", self.chuckTemperatureLineEdit, NO_VALUE)
        panel.bind("status_env_box_temperature", self.boxTemperatureLineEdit, NO_VALUE)
        panel.bind("status_env_box_humidity", self.boxHumidityLineEdit, NO_VALUE)

    def updateState(self, state: Dict) -> None:
        if "env_chuck_temperature" in state:
            value = state.get("env_chuck_temperature")
            self.chuckTemperatureLineEdit.setText(format_metric(value, "°C", decimals=2))
        if "env_box_temperature" in state:
            value = state.get("env_box_temperature")
            self.boxTemperatureLineEdit.setText(format_metric(value, "°C", decimals=2))
        if "env_box_humidity" in state:
            value = state.get("env_box_humidity")
            self.boxHumidityLineEdit.setText(format_metric(value, "%rH", decimals=2))

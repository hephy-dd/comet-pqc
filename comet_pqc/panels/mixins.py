from PyQt5 import QtCore, QtWidgets

from ..components import Metric
from ..utils import format_metric, format_switch

__all__ = [
    "HVSourceMixin",
    "VSourceMixin",
    "ElectrometerMixin",
    "LCRMixin",
    "EnvironmentMixin"
]

NO_VALUE: str = "---"


class HVSourceMixin:
    """Mixin class providing default controls and status for HV Source."""

    def register_hvsource(self):
        senseModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        senseModeComboBox.addItem("local", "local")
        senseModeComboBox.addItem("remote", "remote")

        routeTerminalComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        routeTerminalComboBox.addItem("front", "front")
        routeTerminalComboBox.addItem("rear", "rear")

        def toggleFilter(enabled):
            filterCountSpinBox.setEnabled(enabled)
            filterCountLabel.setEnabled(enabled)
            filterTypeComboBox.setEnabled(enabled)
            filterTypeLabel.setEnabled(enabled)

        filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        filterEnableCheckBox.setText("Enable")
        filterEnableCheckBox.stateChanged.connect(toggleFilter)

        filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        filterCountSpinBox.setRange(0, 100)

        filterCountLabel: QtWidgets.QLabel = QtWidgets.QLabel("Count", self)

        filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        filterTypeComboBox.addItem("repeat", "repeat")
        filterTypeComboBox.addItem("moving", "moving")

        filterTypeLabel: QtWidgets.QLabel = QtWidgets.QLabel("Type", self)

        def toggleSourceVoltageAutorange(enabled: bool) -> None:
            sourceVoltageRangeSpinBox.setEnabled(not enabled)

        sourceVoltageAutorangeEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        sourceVoltageAutorangeEnableCheckBox.setText("Autorange")
        sourceVoltageAutorangeEnableCheckBox.stateChanged.connect(toggleSourceVoltageAutorange)

        sourceVoltageRangeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        sourceVoltageRangeSpinBox.setRange(-2.1e3, 2.1e3)
        sourceVoltageRangeSpinBox.setDecimals(1)
        sourceVoltageRangeSpinBox.setSuffix(" V")

        toggleFilter(False)
        toggleSourceVoltageAutorange(False)

        self.bind("hvsrc_sense_mode", senseModeComboBox, "local")
        self.bind("hvsrc_route_terminal", routeTerminalComboBox, "rear")
        self.bind("hvsrc_filter_enable", filterEnableCheckBox, False)
        self.bind("hvsrc_filter_count", filterCountSpinBox, 10)
        self.bind("hvsrc_filter_type", filterTypeComboBox, "repeat")
        self.bind("hvsrc_source_voltage_autorange_enable", sourceVoltageAutorangeEnableCheckBox, True)
        self.bind("hvsrc_source_voltage_range", sourceVoltageRangeSpinBox, 20, unit="V")

        statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusVoltageLineEdit.setReadOnly(True)
        statusVoltageLineEdit.setText(NO_VALUE)

        statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusCurrentLineEdit.setReadOnly(True)
        statusCurrentLineEdit.setText(NO_VALUE)

        statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusOutputLineEdit.setReadOnly(True)
        statusOutputLineEdit.setText(NO_VALUE)

        self.bind("status_hvsrc_voltage", statusVoltageLineEdit, NO_VALUE)
        self.bind("status_hvsrc_current", statusCurrentLineEdit, NO_VALUE)
        self.bind("status_hvsrc_output", statusOutputLineEdit, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("HV Source Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(statusVoltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(statusCurrentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(statusOutputLineEdit, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(filterCountLabel)
        filterGroupBoxLayout.addWidget(filterCountSpinBox)
        filterGroupBoxLayout.addWidget(filterTypeLabel)
        filterGroupBoxLayout.addWidget(filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        voltageRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        voltageRangeGroupBox.setTitle("Source Voltage Range")

        voltageRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(voltageRangeGroupBox)
        voltageRangeGroupBoxLayout.addWidget(sourceVoltageAutorangeEnableCheckBox)
        voltageRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Range", self))
        voltageRangeGroupBoxLayout.addWidget(sourceVoltageRangeSpinBox)
        voltageRangeGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode", self))
        optionsGroupBoxLayout.addWidget(senseModeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Route Terminal", self))
        optionsGroupBoxLayout.addWidget(routeTerminalComboBox)
        optionsGroupBoxLayout.addStretch()

        controlWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        controlWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(controlWidget)
        controlWidgetLayout.addWidget(filterGroupBox, 1)
        controlWidgetLayout.addWidget(voltageRangeGroupBox, 1)
        controlWidgetLayout.addWidget(optionsGroupBox, 1)

        self.controlTabWidget.addTab(controlWidget, "HV Source")

        def handler(state: dict) -> None:
            if "hvsrc_voltage" in state:
                value = state.get("hvsrc_voltage")
                statusVoltageLineEdit.setText(format_metric(value, "V"))
            if "hvsrc_current" in state:
                value = state.get("hvsrc_current")
                statusCurrentLineEdit.setText(format_metric(value, "A"))
            if "hvsrc_output" in state:
                value = state.get("hvsrc_output")
                statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))

        self.addStateHandler(handler)


class VSourceMixin:
    """Mixin class providing default controls and status for V Source."""

    def register_vsource(self):
        senseModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        senseModeComboBox.addItem("local", "local")
        senseModeComboBox.addItem("remote", "remote")

        def toggleFilter(enabled):
            filterCountSpinBox.setEnabled(enabled)
            filterCountLabel.setEnabled(enabled)
            filterTypeComboBox.setEnabled(enabled)
            filterTypeLabel.setEnabled(enabled)

        filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        filterEnableCheckBox.setText("Enable")
        filterEnableCheckBox.stateChanged.connect(toggleFilter)

        filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        filterCountSpinBox.setRange(0, 100)

        filterCountLabel = QtWidgets.QLabel("Count", self)

        filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        filterTypeComboBox.addItem("repeat", "repeat")
        filterTypeComboBox.addItem("moving", "moving")

        filterTypeLabel = QtWidgets.QLabel("Type", self)

        toggleFilter(False)

        self.bind("vsrc_sense_mode", senseModeComboBox, "local")
        self.bind("vsrc_filter_enable", filterEnableCheckBox, False)
        self.bind("vsrc_filter_count", filterCountSpinBox, 10)
        self.bind("vsrc_filter_type", filterTypeComboBox, "repeat")

        statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusVoltageLineEdit.setReadOnly(True)
        statusVoltageLineEdit.setText(NO_VALUE)

        statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusCurrentLineEdit.setReadOnly(True)
        statusCurrentLineEdit.setText(NO_VALUE)

        statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusOutputLineEdit.setReadOnly(True)
        statusOutputLineEdit.setText(NO_VALUE)

        self.bind("status_vsrc_voltage", statusVoltageLineEdit, NO_VALUE)
        self.bind("status_vsrc_current", statusCurrentLineEdit, NO_VALUE)
        self.bind("status_vsrc_output", statusOutputLineEdit, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("V Source Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(statusVoltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(statusCurrentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(statusOutputLineEdit, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(filterCountLabel)
        filterGroupBoxLayout.addWidget(filterCountSpinBox)
        filterGroupBoxLayout.addWidget(filterTypeLabel)
        filterGroupBoxLayout.addWidget(filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode", self))
        optionsGroupBoxLayout.addWidget(senseModeComboBox)
        optionsGroupBoxLayout.addStretch()

        controlWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        controlWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(controlWidget)
        controlWidgetLayout.addWidget(filterGroupBox, 1)
        controlWidgetLayout.addWidget(optionsGroupBox, 1)
        controlWidgetLayout.addStretch(1)

        self.controlTabWidget.addTab(controlWidget, "V Source")

        def handler(state: dict) -> None:
            if "vsrc_voltage" in state:
                value = state.get("vsrc_voltage")
                statusVoltageLineEdit.setText(format_metric(value, "V"))
            if "vsrc_current" in state:
                value = state.get("vsrc_current")
                statusCurrentLineEdit.setText(format_metric(value, "A"))
            if "vsrc_output" in state:
                value = state.get("vsrc_output")
                statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))

        self.addStateHandler(handler)


class ElectrometerMixin:
    """Mixin class providing default controls and status for Electrometer."""

    def register_electrometer(self):
        def toggleFilter(enabled):
            filterCountSpinBox.setEnabled(enabled)
            filterCountLabel.setEnabled(enabled)
            filterTypeComboBox.setEnabled(enabled)
            filterTypeLabel.setEnabled(enabled)

        filterEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        filterEnableCheckBox.setText("Enable")
        filterEnableCheckBox.stateChanged.connect(toggleFilter)

        filterCountSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        filterCountSpinBox.setRange(0, 100)

        filterCountLabel = QtWidgets.QLabel("Count", self)

        filterTypeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        filterTypeComboBox.addItem("repeat", "repeat")
        filterTypeComboBox.addItem("moving", "moving")

        filterTypeLabel = QtWidgets.QLabel("Type", self)

        zeroCorrectionCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        zeroCorrectionCheckBox.setText("Zero Correction")

        integrationRateSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        integrationRateSpinBox.setRange(0, 100)
        integrationRateSpinBox.setDecimals(2)
        integrationRateSpinBox.setSuffix(" Hz")

        def toggleCurrentAutorange(enabled):
            currentRangeMetric.setEnabled(not enabled)
            currentAutorangeMinimumMetric.setEnabled(enabled)
            currentAutorangeMaximumMetric.setEnabled(enabled)

        currentRangeMetric: Metric = Metric("A", self)
        currentRangeMetric.setPrefixes("munp")
        currentRangeMetric.setDecimals(3)
        currentRangeMetric.setRange(0, 2.1e3)

        currentAutorangeEnableCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        currentAutorangeEnableCheckBox.setText("Enable")
        currentAutorangeEnableCheckBox.stateChanged.connect(toggleCurrentAutorange)

        currentAutorangeMinimumMetric: Metric = Metric("A", self)
        currentAutorangeMinimumMetric.setPrefixes("munp")
        currentAutorangeMinimumMetric.setDecimals(3)
        currentAutorangeMinimumMetric.setRange(0, 2.1e3)

        currentAutorangeMaximumMetric: Metric = Metric("A", self)
        currentAutorangeMaximumMetric.setPrefixes("munp")
        currentAutorangeMaximumMetric.setDecimals(3)
        currentAutorangeMaximumMetric.setRange(0, 2.1e3)

        toggleFilter(False)
        toggleCurrentAutorange(False)

        self.bind("elm_filter_enable", filterEnableCheckBox, False)
        self.bind("elm_filter_count", filterCountSpinBox, 10)
        self.bind("elm_filter_type", filterTypeComboBox, "repeat")
        self.bind("elm_zero_correction", zeroCorrectionCheckBox, False)
        self.bind("elm_integration_rate", integrationRateSpinBox, 50.0)
        self.bind("elm_current_range", currentRangeMetric, 20e-12, unit="A")
        self.bind("elm_current_autorange_enable", currentAutorangeEnableCheckBox, False)
        self.bind("elm_current_autorange_minimum", currentAutorangeMinimumMetric, 2.0E-11, unit="A")
        self.bind("elm_current_autorange_maximum", currentAutorangeMaximumMetric, 2.0E-2, unit="A")

        statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusCurrentLineEdit.setReadOnly(True)
        statusCurrentLineEdit.setText(NO_VALUE)

        self.bind("status_elm_current", statusCurrentLineEdit, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("Electrometer Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 0)
        statusGroupBoxLayout.addWidget(statusCurrentLineEdit, 1, 0)
        statusGroupBoxLayout.setColumnStretch(0, 1)
        statusGroupBoxLayout.setColumnStretch(1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(filterCountLabel)
        filterGroupBoxLayout.addWidget(filterCountSpinBox)
        filterGroupBoxLayout.addWidget(filterTypeLabel)
        filterGroupBoxLayout.addWidget(filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        rangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        rangeGroupBox.setTitle("Range")

        rangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(rangeGroupBox)
        rangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Range", self))
        rangeGroupBoxLayout.addWidget(currentRangeMetric)

        autoRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        autoRangeGroupBox.setTitle("Auto Range")

        autoRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(autoRangeGroupBox)
        autoRangeGroupBoxLayout.addWidget(currentAutorangeEnableCheckBox)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Minimum Current", self))
        autoRangeGroupBoxLayout.addWidget(currentAutorangeMinimumMetric)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum Current", self))
        autoRangeGroupBoxLayout.addWidget(currentAutorangeMaximumMetric)
        autoRangeGroupBoxLayout.addStretch()

        rangeLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        rangeLayout.addWidget(rangeGroupBox)
        rangeLayout.addWidget(autoRangeGroupBox)

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(zeroCorrectionCheckBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Rate", self))
        optionsGroupBoxLayout.addWidget(integrationRateSpinBox)
        optionsGroupBoxLayout.addStretch()

        controlWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        controlWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(controlWidget)
        controlWidgetLayout.addWidget(filterGroupBox, 1)
        controlWidgetLayout.addLayout(rangeLayout, 1)
        controlWidgetLayout.addWidget(optionsGroupBox, 1)

        self.controlTabWidget.addTab(controlWidget, "Electrometer")

        def handler(state: dict) -> None:
            if "elm_current" in state:
                value = state.get("elm_current")
                statusCurrentLineEdit.setText(format_metric(value, "A"))
        self.addStateHandler(handler)


class LCRMixin:
    """Mixin class providing default controls and status for LCR Meter."""

    def register_lcr(self):
        integrationTimeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        integrationTimeComboBox.addItem("short", "short")
        integrationTimeComboBox.addItem("medium", "medium")
        integrationTimeComboBox.addItem("long", "long")

        averagingRateSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        averagingRateSpinBox.setRange(1, 256)

        autoLevelControlCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        autoLevelControlCheckBox.setText("Auto Level Control")

        softFilterCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        softFilterCheckBox.setText("Filter STD/mean < 0.005")

        def changeOpenCorrectionMode(index: int) -> None:
            mode = openCorrectionModeComboBox.itemData(index)
            openCorrectionChannelSpinBox.setEnabled(mode == "multi")

        openCorrectionModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        openCorrectionModeComboBox.addItem("single", "single")
        openCorrectionModeComboBox.addItem("multi", "multi")
        openCorrectionModeComboBox.currentIndexChanged.connect(changeOpenCorrectionMode)

        openCorrectionChannelSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        openCorrectionChannelSpinBox.setRange(0, 127)

        changeOpenCorrectionMode(0)

        self.bind("lcr_integration_time", integrationTimeComboBox, "medium")
        self.bind("lcr_averaging_rate", averagingRateSpinBox, 1)
        self.bind("lcr_auto_level_control", autoLevelControlCheckBox, True)
        self.bind("lcr_soft_filter", softFilterCheckBox, True)
        self.bind("lcr_open_correction_mode", openCorrectionModeComboBox, "single")
        self.bind("lcr_open_correction_channel", openCorrectionChannelSpinBox, 0)

        statusVoltageLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusVoltageLineEdit.setReadOnly(True)
        statusVoltageLineEdit.setText(NO_VALUE)

        statusCurrentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusCurrentLineEdit.setReadOnly(True)
        statusCurrentLineEdit.setText(NO_VALUE)

        statusOutputLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusOutputLineEdit.setReadOnly(True)
        statusOutputLineEdit.setText(NO_VALUE)

        self.bind("status_lcr_voltage", statusVoltageLineEdit, NO_VALUE)
        self.bind("status_lcr_current", statusCurrentLineEdit, NO_VALUE)
        self.bind("status_lcr_output", statusOutputLineEdit, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("LCR Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(statusVoltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(statusCurrentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(statusOutputLineEdit, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        openCorrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        openCorrGroupBox.setTitle("Open Correction")

        openCorrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(openCorrGroupBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Method", self))
        openCorrGroupBoxLayout.addWidget(openCorrectionModeComboBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Channel", self))
        openCorrGroupBoxLayout.addWidget(openCorrectionChannelSpinBox)
        openCorrGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Time", self))
        optionsGroupBoxLayout.addWidget(integrationTimeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Averaging Rate", self))
        optionsGroupBoxLayout.addWidget(averagingRateSpinBox)
        optionsGroupBoxLayout.addWidget(autoLevelControlCheckBox)
        optionsGroupBoxLayout.addWidget(softFilterCheckBox)
        optionsGroupBoxLayout.addStretch()

        controlWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        controlWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(controlWidget)
        controlWidgetLayout.addWidget(openCorrGroupBox, 1)
        controlWidgetLayout.addWidget(optionsGroupBox, 1)
        controlWidgetLayout.addStretch(1)

        self.controlTabWidget.addTab(controlWidget, "LCR")

        def handler(state: dict) -> None:
            if "lcr_voltage" in state:
                value = state.get("lcr_voltage")
                statusVoltageLineEdit.setText(format_metric(value, "V"))
            if "lcr_current" in state:
                value = state.get("lcr_current")
                statusCurrentLineEdit.setText(format_metric(value, "A"))
            if "lcr_output" in state:
                value = state.get("lcr_output")
                statusOutputLineEdit.setText(format_switch(value, default=NO_VALUE))

        self.addStateHandler(handler)


class EnvironmentMixin:
    """Mixin class providing default controls and status for Environment box."""

    def register_environment(self):
        statusChuckTempLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusChuckTempLineEdit.setReadOnly(True)
        statusChuckTempLineEdit.setText(NO_VALUE)

        statusBoxTempLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusBoxTempLineEdit.setReadOnly(True)
        statusBoxTempLineEdit.setText(NO_VALUE)

        statusBoxHumidLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        statusBoxHumidLineEdit.setReadOnly(True)
        statusBoxHumidLineEdit.setText(NO_VALUE)

        self.bind("status_env_chuck_temperature", statusChuckTempLineEdit, NO_VALUE)
        self.bind("status_env_box_temperature", statusBoxTempLineEdit, NO_VALUE)
        self.bind("status_env_box_humidity", statusBoxHumidLineEdit, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("Environment Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Chuck temp.", self), 0, 0)
        statusGroupBoxLayout.addWidget(statusChuckTempLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box temp.", self), 0, 1)
        statusGroupBoxLayout.addWidget(statusBoxTempLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box humid.", self), 0, 2)
        statusGroupBoxLayout.addWidget(statusBoxHumidLineEdit, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        def handler(state: dict) -> None:
            if "env_chuck_temperature" in state:
                value = state.get("env_chuck_temperature")
                statusChuckTempLineEdit.setText(format_metric(value, "°C", decimals=2))
            if "env_box_temperature" in state:
                value = state.get("env_box_temperature")
                statusBoxTempLineEdit.setText(format_metric(value, "°C", decimals=2))
            if "env_box_humidity" in state:
                value = state.get("env_box_humidity")
                statusBoxHumidLineEdit.setText(format_metric(value, "%rH", decimals=2))

        self.addStateHandler(handler)

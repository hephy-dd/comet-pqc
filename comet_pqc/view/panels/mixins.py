from PyQt5 import QtWidgets

from comet_pqc.utils import format_metric, format_switch
from ..components import Metric
from .panel import Panel

__all__ = [
    "HVSourceMixin",
    "VSourceMixin",
    "ElectrometerMixin",
    "LCRMixin",
    "EnvironmentMixin"
]

NO_VALUE = "---"


class HVSourceMixin:
    """Component class providing default controls and status for HV Source."""

    def __init__(self, panel: Panel) -> None:
        self.senseModeComboBox = QtWidgets.QComboBox()
        self.senseModeComboBox.addItems(["local", "remote"])

        self.routeTerminalComboBox = QtWidgets.QComboBox()
        self.routeTerminalComboBox.addItems(["front", "rear"])

        self.filterEnableCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.toggled.connect(self.toggleFilterEnable)

        self.filterCountSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel = QtWidgets.QLabel()
        self.filterCountLabel.setText("Count")

        self.filterTypeComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItems(["repeat", "moving"])

        self.filterTypeLabel = QtWidgets.QLabel()
        self.filterTypeLabel.setText("Type")

        self.voltageAutorangeEnableCheckBox = QtWidgets.QCheckBox()
        self.voltageAutorangeEnableCheckBox.setText("Autorange")
        self.voltageAutorangeEnableCheckBox.toggled.connect(self.toggleVoltageAutorange)

        self.voltageRangeSpinBox = QtWidgets.QDoubleSpinBox()
        self.voltageRangeSpinBox.setDecimals(1)
        self.voltageRangeSpinBox.setRange(-2200, +2200)
        self.voltageRangeSpinBox.setSuffix(" V")

        self.toggleFilterEnable(False)
        self.toggleVoltageAutorange(False)

        self.voltageLineEdit = QtWidgets.QLineEdit()
        self.voltageLineEdit.setReadOnly(True)
        self.voltageLineEdit.setText(NO_VALUE)

        self.currentLineEdit = QtWidgets.QLineEdit()
        self.currentLineEdit.setReadOnly(True)
        self.currentLineEdit.setText(NO_VALUE)

        self.outputLineEdit = QtWidgets.QLineEdit()
        self.outputLineEdit.setReadOnly(True)
        self.outputLineEdit.setText(NO_VALUE)

        self.statusGroupBox = QtWidgets.QGroupBox()
        self.statusGroupBox.setTitle("HV Source Status")

        statusGroupBoxLayout = QtWidgets.QGridLayout(self.statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        statusGroupBoxLayout.addWidget(self.voltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        statusGroupBoxLayout.addWidget(self.currentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        statusGroupBoxLayout.addWidget(self.outputLineEdit, 1, 2)
        statusGroupBoxLayout.setColumnStretch(0, 3)
        statusGroupBoxLayout.setColumnStretch(1, 3)
        statusGroupBoxLayout.setColumnStretch(2, 2)

        panel.statusWidget.layout().addWidget(self.statusGroupBox)

        # Filter

        self.filterGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        # Source voltage range

        self.voltageRangeGroupBox = QtWidgets.QGroupBox()
        self.voltageRangeGroupBox.setTitle("Source Voltage Range")

        voltageRangeGroupBoxLayout = QtWidgets.QVBoxLayout(self.voltageRangeGroupBox)
        voltageRangeGroupBoxLayout.addWidget(self.voltageAutorangeEnableCheckBox)
        voltageRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Range"))
        voltageRangeGroupBoxLayout.addWidget(self.voltageRangeSpinBox)
        voltageRangeGroupBoxLayout.addStretch()

        # Options

        self.optionsGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.senseModeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Route Terminal"))
        optionsGroupBoxLayout.addWidget(self.routeTerminalComboBox)
        optionsGroupBoxLayout.addStretch()

        # HV source tab

        self.widget = QtWidgets.QWidget()

        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.addWidget(self.filterGroupBox, 1)
        layout.addWidget(self.voltageRangeGroupBox, 1)
        layout.addWidget(self.optionsGroupBox, 1)

        panel.controlTabWidget.addTab(self.widget, "HV Source")

        # Bindings

        panel.bind("hvsrc_sense_mode", self.senseModeComboBox, "local")
        panel.bind("hvsrc_route_terminal", self.routeTerminalComboBox, "rear")
        panel.bind("hvsrc_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("hvsrc_filter_count", self.filterCountSpinBox, 10)
        panel.bind("hvsrc_filter_type", self.filterTypeComboBox, "repeat")
        panel.bind("hvsrc_source_voltage_autorange_enable", self.voltageAutorangeEnableCheckBox, True)
        panel.bind("hvsrc_source_voltage_range", self.voltageRangeSpinBox, 20, unit="V")

        panel.bind("status_hvsrc_voltage", self.voltageLineEdit, NO_VALUE)
        panel.bind("status_hvsrc_current", self.currentLineEdit, NO_VALUE)
        panel.bind("status_hvsrc_output", self.outputLineEdit, NO_VALUE)

        # Handler

        def handler(state):
            if "hvsrc_voltage" in state:
                value = state.get("hvsrc_voltage")
                self.voltageLineEdit.setText(format_metric(value, "V"))
            if "hvsrc_current" in state:
                value = state.get("hvsrc_current")
                self.currentLineEdit.setText(format_metric(value, "A"))
            if "hvsrc_output" in state:
                value = state.get("hvsrc_output")
                self.outputLineEdit.setText(format_switch(value, default=NO_VALUE))

        panel.state_handlers.append(handler)

    def toggleVoltageAutorange(self, enabled: bool) -> None:
        self.voltageRangeSpinBox.setEnabled(not enabled)

    def toggleFilterEnable(self, enabled: bool) -> None:
        self.filterCountSpinBox.setEnabled(enabled)
        self.filterCountLabel.setEnabled(enabled)
        self.filterTypeComboBox.setEnabled(enabled)
        self.filterTypeLabel.setEnabled(enabled)


class VSourceMixin:
    """Component class providing default controls and status for V Source."""

    def __init__(self, panel: Panel) -> None:
        self.senseModeComboBox = QtWidgets.QComboBox()
        self.senseModeComboBox.addItems(["local", "remote"])

        self.filterEnableCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.toggled.connect(self.toggleFilterEnable)

        self.filterCountSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel = QtWidgets.QLabel()
        self.filterCountLabel.setText("Count")

        self.filterTypeComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItems(["repeat", "moving"])

        self.filterTypeLabel = QtWidgets.QLabel()
        self.filterTypeLabel.setText("Type")

        self.toggleFilterEnable(False)

        self.voltageLineEdit = QtWidgets.QLineEdit()
        self.voltageLineEdit.setReadOnly(True)
        self.voltageLineEdit.setText(NO_VALUE)

        self.currentLineEdit = QtWidgets.QLineEdit()
        self.currentLineEdit.setReadOnly(True)
        self.currentLineEdit.setText(NO_VALUE)

        self.outputLineEdit = QtWidgets.QLineEdit()
        self.outputLineEdit.setReadOnly(True)
        self.outputLineEdit.setText(NO_VALUE)

        self.statusGroupBox = QtWidgets.QGroupBox()
        self.statusGroupBox.setTitle("V Source Status")

        statusGroupBoxLayout = QtWidgets.QGridLayout(self.statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        statusGroupBoxLayout.addWidget(self.voltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        statusGroupBoxLayout.addWidget(self.currentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        statusGroupBoxLayout.addWidget(self.outputLineEdit, 1, 2)
        statusGroupBoxLayout.setColumnStretch(0, 3)
        statusGroupBoxLayout.setColumnStretch(1, 3)
        statusGroupBoxLayout.setColumnStretch(2, 2)

        panel.statusWidget.layout().addWidget(self.statusGroupBox)

        # Filter

        self.filterGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        # Options

        self.optionsGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.senseModeComboBox)
        optionsGroupBoxLayout.addStretch()

        # V source tab

        self.widget = QtWidgets.QWidget()

        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.addWidget(self.filterGroupBox, 1)
        layout.addWidget(self.optionsGroupBox, 1)
        layout.addStretch(1)

        panel.controlTabWidget.addTab(self.widget, "V Source")

        # Bindings

        panel.bind("vsrc_sense_mode", self.senseModeComboBox, "local")
        panel.bind("vsrc_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("vsrc_filter_count", self.filterCountSpinBox, 10)
        panel.bind("vsrc_filter_type", self.filterTypeComboBox, "repeat")

        panel.bind("status_vsrc_voltage", self.voltageLineEdit, NO_VALUE)
        panel.bind("status_vsrc_current", self.currentLineEdit, NO_VALUE)
        panel.bind("status_vsrc_output", self.outputLineEdit, NO_VALUE)

        # Handler

        def handler(state):
            if "vsrc_voltage" in state:
                value = state.get("vsrc_voltage")
                self.voltageLineEdit.setText(format_metric(value, "V"))
            if "vsrc_current" in state:
                value = state.get("vsrc_current")
                self.currentLineEdit.setText(format_metric(value, "A"))
            if "vsrc_output" in state:
                value = state.get("vsrc_output")
                self.outputLineEdit.setText(format_switch(value, default=NO_VALUE))

        panel.state_handlers.append(handler)

    def toggleFilterEnable(self, enabled: bool) -> None:
        self.filterCountSpinBox.setEnabled(enabled)
        self.filterCountLabel.setEnabled(enabled)
        self.filterTypeComboBox.setEnabled(enabled)
        self.filterTypeLabel.setEnabled(enabled)


class ElectrometerMixin:
    """Component class providing default controls and status for Electrometer."""

    def __init__(self, panel: Panel) -> None:
        self.filterEnableCheckBox = QtWidgets.QCheckBox()
        self.filterEnableCheckBox.setText("Enable")
        self.filterEnableCheckBox.toggled.connect(self.toggleFilterEnable)

        self.filterCountSpinBox = QtWidgets.QSpinBox()
        self.filterCountSpinBox.setRange(1, 100)

        self.filterCountLabel = QtWidgets.QLabel()
        self.filterCountLabel.setText("Count")

        self.filterTypeComboBox = QtWidgets.QComboBox()
        self.filterTypeComboBox.addItems(["repeat", "moving"])

        self.filterTypeLabel = QtWidgets.QLabel()
        self.filterTypeLabel.setText("Type")

        self.zeroCorrCheckBox = QtWidgets.QCheckBox()
        self.zeroCorrCheckBox.setText("Zero Correction")

        self.integrationRateSpinBox = QtWidgets.QDoubleSpinBox()
        self.integrationRateSpinBox.setDecimals(2)
        self.integrationRateSpinBox.setRange(0, 100.0)
        self.integrationRateSpinBox.setSuffix(" Hz")

        self.currentRangeMetric = Metric()
        self.currentRangeMetric.setUnit("A")
        self.currentRangeMetric.setPrefixes("munp")
        self.currentRangeMetric.setDecimals(3)
        self.currentRangeMetric.setRange(0, float("inf"))

        self.currentAutorangeEnableCheckBox = QtWidgets.QCheckBox()
        self.currentAutorangeEnableCheckBox.setText("Enable")
        self.currentAutorangeEnableCheckBox.toggled.connect(self.toggleCurrentAutorange)

        self.currentAutorangeMinimumMetric = Metric()
        self.currentAutorangeMinimumMetric.setUnit("A")
        self.currentAutorangeMinimumMetric.setPrefixes("munp")
        self.currentAutorangeMinimumMetric.setDecimals(3)
        self.currentAutorangeMinimumMetric.setRange(0, float("inf"))

        self.currentAutorangeMaximumMetric = Metric()
        self.currentAutorangeMaximumMetric.setUnit("A")
        self.currentAutorangeMaximumMetric.setPrefixes("munp")
        self.currentAutorangeMaximumMetric.setDecimals(3)
        self.currentAutorangeMaximumMetric.setRange(0, float("inf"))

        self.toggleFilterEnable(False)
        self.toggleCurrentAutorange(False)

        self.currentLineEdit = QtWidgets.QLineEdit()
        self.currentLineEdit.setReadOnly(True)
        self.currentLineEdit.setText(NO_VALUE)

        self.statusGroupBox = QtWidgets.QGroupBox()
        self.statusGroupBox.setTitle("Electrometer Status")

        statusGroupBoxLayout = QtWidgets.QGridLayout(self.statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 0)
        statusGroupBoxLayout.addWidget(self.currentLineEdit, 1, 0)
        statusGroupBoxLayout.setColumnStretch(0, 1)
        statusGroupBoxLayout.setColumnStretch(1, 1)
        statusGroupBoxLayout.setColumnStretch(2, 1)

        panel.statusWidget.layout().addWidget(self.statusGroupBox)

        # Filter

        self.filterGroupBox = QtWidgets.QGroupBox()
        self.filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout = QtWidgets.QVBoxLayout(self.filterGroupBox)
        filterGroupBoxLayout.addWidget(self.filterEnableCheckBox)
        filterGroupBoxLayout.addWidget(self.filterCountLabel)
        filterGroupBoxLayout.addWidget(self.filterCountSpinBox)
        filterGroupBoxLayout.addWidget(self.filterTypeLabel)
        filterGroupBoxLayout.addWidget(self.filterTypeComboBox)
        filterGroupBoxLayout.addStretch()

        # Range

        self.rangeGroupBox = QtWidgets.QGroupBox()
        self.rangeGroupBox.setTitle("Range")

        rangeGroupBoxLayout = QtWidgets.QVBoxLayout(self.rangeGroupBox)
        rangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Range"))
        rangeGroupBoxLayout.addWidget(self.currentRangeMetric)

        # Auto Range

        self.autoRangeGroupBox = QtWidgets.QGroupBox()
        self.autoRangeGroupBox.setTitle("Auto Range")

        autoRangeGroupBoxLayout = QtWidgets.QVBoxLayout(self.autoRangeGroupBox)
        autoRangeGroupBoxLayout.addWidget(self.currentAutorangeEnableCheckBox)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Minimum Current"))
        autoRangeGroupBoxLayout.addWidget(self.currentAutorangeMinimumMetric)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum Current"))
        autoRangeGroupBoxLayout.addWidget(self.currentAutorangeMaximumMetric)
        autoRangeGroupBoxLayout.addStretch()

        # Options

        self.optionsGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(self.zeroCorrCheckBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Rate"))
        optionsGroupBoxLayout.addWidget(self.integrationRateSpinBox)
        optionsGroupBoxLayout.addStretch()

        # Electrometer tab

        self.widget = QtWidgets.QWidget()

        layout = QtWidgets.QGridLayout(self.widget)
        layout.addWidget(self.filterGroupBox, 0, 0, 2, 1)
        layout.addWidget(self.rangeGroupBox, 0, 1)
        layout.addWidget(self.autoRangeGroupBox, 1, 1)
        layout.addWidget(self.optionsGroupBox, 0, 2, 2, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

        panel.controlTabWidget.addTab(self.widget, "Electrometer")

        # Bindings

        panel.bind("elm_filter_enable", self.filterEnableCheckBox, False)
        panel.bind("elm_filter_count", self.filterCountSpinBox, 10)
        panel.bind("elm_filter_type", self.filterTypeComboBox, "repeat")
        panel.bind("elm_zero_correction", self.zeroCorrCheckBox, False)
        panel.bind("elm_integration_rate", self.integrationRateSpinBox, 50.0)
        panel.bind("elm_current_range", self.currentRangeMetric, 20e-12, unit="A")
        panel.bind("elm_current_autorange_enable", self.currentAutorangeEnableCheckBox, False)
        panel.bind("elm_current_autorange_minimum", self.currentAutorangeMinimumMetric, 2.0E-11, unit="A")
        panel.bind("elm_current_autorange_maximum", self.currentAutorangeMaximumMetric, 2.0E-2, unit="A")

        panel.bind("status_elm_current", self.currentLineEdit, NO_VALUE)

        # Handler

        def handler(state):
            if "elm_current" in state:
                value = state.get("elm_current")
                self.currentLineEdit.setText(format_metric(value, "A"))

        panel.state_handlers.append(handler)

    def toggleFilterEnable(self, enabled: bool) -> None:
        self.filterCountSpinBox.setEnabled(enabled)
        self.filterCountLabel.setEnabled(enabled)
        self.filterTypeComboBox.setEnabled(enabled)
        self.filterTypeLabel.setEnabled(enabled)

    def toggleCurrentAutorange(self, enabled: bool) -> None:
        self.currentRangeMetric.setEnabled(not enabled)
        self.currentAutorangeMinimumMetric.setEnabled(enabled)
        self.currentAutorangeMaximumMetric.setEnabled(enabled)


class LCRMixin:
    """Component class providing default controls and status for LCR Meter."""

    def __init__(self, panel: Panel) -> None:
        self.integrationTimeComboBox = QtWidgets.QComboBox()
        self.integrationTimeComboBox.addItems(["short", "medium", "long"])

        self.averagingRateSpinBox = QtWidgets.QSpinBox()
        self.averagingRateSpinBox.setRange(1, 256)

        self.autoLevelControlCheckBox = QtWidgets.QCheckBox()
        self.autoLevelControlCheckBox.setText("Auto Level Control")

        self.softFilterCheckBox = QtWidgets.QCheckBox()
        self.softFilterCheckBox.setText("Filter STD/mean < 0.005")

        self.openCorrModeComboBox = QtWidgets.QComboBox()
        self.openCorrModeComboBox.addItems(["single", "multi"])
        self.openCorrModeComboBox.currentTextChanged.connect(self.openCorrModeChanged)

        self.openCorrChannelSpinBox = QtWidgets.QSpinBox()
        self.openCorrChannelSpinBox.setRange(0, 127)

        self.openCorrModeChanged(self.openCorrModeComboBox.currentText())

        # Open Correction

        self.openCorrGroupBox = QtWidgets.QGroupBox()
        self.openCorrGroupBox.setTitle("Open Correction")

        openCorrGroupBoxLayout = QtWidgets.QVBoxLayout(self.openCorrGroupBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Method"))
        openCorrGroupBoxLayout.addWidget(self.openCorrModeComboBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Channel"))
        openCorrGroupBoxLayout.addWidget(self.openCorrChannelSpinBox)
        openCorrGroupBoxLayout.addStretch()

        # Options

        self.optionsGroupBox = QtWidgets.QGroupBox()
        self.optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Time"))
        optionsGroupBoxLayout.addWidget(self.integrationTimeComboBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Averaging Rate"))
        optionsGroupBoxLayout.addWidget(self.averagingRateSpinBox)
        optionsGroupBoxLayout.addWidget(self.autoLevelControlCheckBox)
        optionsGroupBoxLayout.addWidget(self.softFilterCheckBox)
        optionsGroupBoxLayout.addStretch()

        self.widget = QtWidgets.QWidget()

        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.addWidget(self.openCorrGroupBox, 1)
        layout.addWidget(self.optionsGroupBox, 1)
        layout.addStretch(1)

        panel.controlTabWidget.addTab(self.widget, "LCR")

        # Status

        self.voltageLineEdit = QtWidgets.QLineEdit()
        self.voltageLineEdit.setReadOnly(True)
        self.voltageLineEdit.setText(NO_VALUE)

        self.currentLineEdit = QtWidgets.QLineEdit()
        self.currentLineEdit.setReadOnly(True)
        self.currentLineEdit.setText(NO_VALUE)

        self.outputLineEdit = QtWidgets.QLineEdit()
        self.outputLineEdit.setReadOnly(True)
        self.outputLineEdit.setText(NO_VALUE)

        self.statusGroupBox = QtWidgets.QGroupBox()
        self.statusGroupBox.setTitle("LCR Status")

        statusGroupBoxLayout = QtWidgets.QGridLayout(self.statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        statusGroupBoxLayout.addWidget(self.voltageLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        statusGroupBoxLayout.addWidget(self.currentLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        statusGroupBoxLayout.addWidget(self.outputLineEdit, 1, 2)
        statusGroupBoxLayout.setColumnStretch(0, 3)
        statusGroupBoxLayout.setColumnStretch(1, 3)
        statusGroupBoxLayout.setColumnStretch(2, 2)

        panel.statusWidget.layout().addWidget(self.statusGroupBox)

        # Bindings

        panel.bind("lcr_integration_time", self.integrationTimeComboBox, "medium")
        panel.bind("lcr_averaging_rate", self.averagingRateSpinBox, 1)
        panel.bind("lcr_auto_level_control", self.autoLevelControlCheckBox, True)
        panel.bind("lcr_soft_filter", self.softFilterCheckBox, True)
        panel.bind("lcr_open_correction_mode", self.openCorrModeComboBox, "single")
        panel.bind("lcr_open_correction_channel", self.openCorrChannelSpinBox, 0)

        panel.bind("status_lcr_voltage", self.voltageLineEdit, NO_VALUE)
        panel.bind("status_lcr_current", self.currentLineEdit, NO_VALUE)
        panel.bind("status_lcr_output", self.outputLineEdit, NO_VALUE)

        # Handler

        def handler(state):
            if "lcr_voltage" in state:
                value = state.get("lcr_voltage")
                self.voltageLineEdit.setText(format_metric(value, "V"))
            if "lcr_current" in state:
                value = state.get("lcr_current")
                self.currentLineEdit.setText(format_metric(value, "A"))
            if "lcr_output" in state:
                value = state.get("lcr_output")
                self.outputLineEdit.setText(format_switch(value, default=NO_VALUE))

        panel.state_handlers.append(handler)

    def openCorrModeChanged(self, mode: str) -> None:
        self.openCorrChannelSpinBox.setEnabled(mode == "multi")


class EnvironmentMixin:
    """Component class providing default controls and status for Environment box."""

    def __init__(self, panel: Panel) -> None:

        # Status

        self.chuckTemperatureLineEdit = QtWidgets.QLineEdit()
        self.chuckTemperatureLineEdit.setReadOnly(True)
        self.chuckTemperatureLineEdit.setText(NO_VALUE)

        self.boxTemperatureLineEdit = QtWidgets.QLineEdit()
        self.boxTemperatureLineEdit.setReadOnly(True)
        self.boxTemperatureLineEdit.setText(NO_VALUE)

        self.boxHumidityLineEdit = QtWidgets.QLineEdit()
        self.boxHumidityLineEdit.setReadOnly(True)
        self.boxHumidityLineEdit.setText(NO_VALUE)

        self.statusGroupBox = QtWidgets.QGroupBox()
        self.statusGroupBox.setTitle("Environment Status")

        statusGroupBoxLayout = QtWidgets.QGridLayout(self.statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Chuck temp."), 0, 0)
        statusGroupBoxLayout.addWidget(self.chuckTemperatureLineEdit, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box temp."), 0, 1)
        statusGroupBoxLayout.addWidget(self.boxTemperatureLineEdit, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box humid."), 0, 2)
        statusGroupBoxLayout.addWidget(self.boxHumidityLineEdit, 1, 2)
        statusGroupBoxLayout.setColumnStretch(0, 1)
        statusGroupBoxLayout.setColumnStretch(1, 1)
        statusGroupBoxLayout.setColumnStretch(2, 1)

        panel.statusWidget.layout().addWidget(self.statusGroupBox)

        # Bindings

        panel.bind("status_env_chuck_temperature", self.chuckTemperatureLineEdit, NO_VALUE)
        panel.bind("status_env_box_temperature", self.boxTemperatureLineEdit, NO_VALUE)
        panel.bind("status_env_box_humidity", self.boxHumidityLineEdit, NO_VALUE)

        # Handler

        def handler(state):
            if "env_chuck_temperature" in state:
                value = state.get("env_chuck_temperature")
                self.chuckTemperatureLineEdit.setText(format_metric(value, "°C", decimals=2))
            if "env_box_temperature" in state:
                value = state.get("env_box_temperature")
                self.boxTemperatureLineEdit.setText(format_metric(value, "°C", decimals=2))
            if "env_box_humidity" in state:
                value = state.get("env_box_humidity")
                self.boxHumidityLineEdit.setText(format_metric(value, "%rH", decimals=2))

        panel.state_handlers.append(handler)

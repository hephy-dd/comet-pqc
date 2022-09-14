from comet import ui
from PyQt5 import QtCore, QtWidgets

from ..utils import format_metric, format_switch

__all__ = [
    "HVSourceMixin",
    "VSourceMixin",
    "ElectrometerMixin",
    "LCRMixin",
    "EnvironmentMixin"
]

NO_VALUE = "---"


class HVSourceMixin:
    """Mixin class providing default controls and status for HV Source."""

    def register_hvsource(self):
        self.hvsrc_sense_mode = ui.ComboBox(["local", "remote"])
        self.hvsrc_route_terminal = ui.ComboBox(["front", "rear"])

        def toggle_hvsrc_filter(enabled):
            self.hvsrc_filter_count.enabled = enabled
            self.hvsrcFilterCountLabel.setEnabled(enabled)
            self.hvsrc_filter_type.enabled = enabled
            self.hvsrcFilterTypeLabel.setEnabled(enabled)

        self.hvsrc_filter_enable = ui.CheckBox(text="Enable", changed=toggle_hvsrc_filter)
        self.hvsrc_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.hvsrcFilterCountLabel = QtWidgets.QLabel("Count", self)
        self.hvsrc_filter_type = ui.ComboBox(["repeat", "moving"])
        self.hvsrcFilterTypeLabel = QtWidgets.QLabel("Type", self)

        def toggle_hvsrc_source_voltage_autorange(enabled):
            self.hvsrc_source_voltage_range.enabled = not enabled

        self.hvsrc_source_voltage_autorange_enable = ui.CheckBox(text="Autorange", changed=toggle_hvsrc_source_voltage_autorange)
        self.hvsrc_source_voltage_range = ui.Number(minimum=-1100, maximum=1100, decimals=1, suffix="V")

        toggle_hvsrc_filter(False)
        toggle_hvsrc_source_voltage_autorange(False)

        self.bind("hvsrc_sense_mode", self.hvsrc_sense_mode, "local")
        self.bind("hvsrc_route_terminal", self.hvsrc_route_terminal, "rear")
        self.bind("hvsrc_filter_enable", self.hvsrc_filter_enable, False)
        self.bind("hvsrc_filter_count", self.hvsrc_filter_count, 10)
        self.bind("hvsrc_filter_type", self.hvsrc_filter_type, "repeat")
        self.bind("hvsrc_source_voltage_autorange_enable", self.hvsrc_source_voltage_autorange_enable, True)
        self.bind("hvsrc_source_voltage_range", self.hvsrc_source_voltage_range, 20, unit="V")

        self.status_hvsrc_voltage = ui.Text(value=NO_VALUE, readonly=True)
        self.status_hvsrc_current = ui.Text(value=NO_VALUE, readonly=True)
        self.status_hvsrc_output = ui.Text(value=NO_VALUE, readonly=True)

        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, NO_VALUE)
        self.bind("status_hvsrc_current", self.status_hvsrc_current, NO_VALUE)
        self.bind("status_hvsrc_output", self.status_hvsrc_output, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("HV Source Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(self.status_hvsrc_voltage.qt, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(self.status_hvsrc_current.qt, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(self.status_hvsrc_output.qt, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_enable.qt)
        filterGroupBoxLayout.addWidget(self.hvsrcFilterCountLabel)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_count.qt)
        filterGroupBoxLayout.addWidget(self.hvsrcFilterTypeLabel)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_type.qt)
        filterGroupBoxLayout.addStretch()

        voltageRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        voltageRangeGroupBox.setTitle("Source Voltage Range")

        voltageRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(voltageRangeGroupBox)
        voltageRangeGroupBoxLayout.addWidget(self.hvsrc_source_voltage_autorange_enable.qt)
        voltageRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Range", self))
        voltageRangeGroupBoxLayout.addWidget(self.hvsrc_source_voltage_range.qt)
        voltageRangeGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode", self))
        optionsGroupBoxLayout.addWidget(self.hvsrc_sense_mode.qt)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Route Terminal", self))
        optionsGroupBoxLayout.addWidget(self.hvsrc_route_terminal.qt)
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
                self.status_hvsrc_voltage.value = format_metric(value, "V")
            if "hvsrc_current" in state:
                value = state.get("hvsrc_current")
                self.status_hvsrc_current.value = format_metric(value, "A")
            if "hvsrc_output" in state:
                value = state.get("hvsrc_output")
                self.status_hvsrc_output.value = format_switch(value, default=NO_VALUE)

        self.state_handlers.append(handler)


class VSourceMixin:
    """Mixin class providing default controls and status for V Source."""

    def register_vsource(self):
        self.vsrc_sense_mode = ui.ComboBox(["local", "remote"])

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.enabled = enabled
            self.vsrc_filter_count_label.enabled = enabled
            self.vsrc_filter_type.enabled = enabled
            self.vsrc_filter_type_label.enabled = enabled

        self.vsrc_filter_enable = ui.CheckBox(text="Enable", changed=toggle_vsrc_filter)
        self.vsrc_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.vsrc_filter_count_label = ui.Label(text="Count")
        self.vsrc_filter_type = ui.ComboBox(["repeat", "moving"])
        self.vsrc_filter_type_label = ui.Label(text="Type")

        toggle_vsrc_filter(False)

        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")

        self.status_vsrc_voltage = ui.Text(value=NO_VALUE, readonly=True)
        self.status_vsrc_current = ui.Text(value=NO_VALUE, readonly=True)
        self.status_vsrc_output = ui.Text(value=NO_VALUE, readonly=True)

        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, NO_VALUE)
        self.bind("status_vsrc_current", self.status_vsrc_current, NO_VALUE)
        self.bind("status_vsrc_output", self.status_vsrc_output, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("V Source Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(self.status_vsrc_voltage.qt, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(self.status_vsrc_current.qt, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(self.status_vsrc_output.qt, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_enable.qt)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_count_label.qt)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_count.qt)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_type_label.qt)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_type.qt)
        filterGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode", self))
        optionsGroupBoxLayout.addWidget(self.vsrc_sense_mode.qt)
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
                self.status_vsrc_voltage.value = format_metric(value, "V")
            if "vsrc_current" in state:
                value = state.get("vsrc_current")
                self.status_vsrc_current.value = format_metric(value, "A")
            if "vsrc_output" in state:
                value = state.get("vsrc_output")
                self.status_vsrc_output.value = format_switch(value, default=NO_VALUE)

        self.state_handlers.append(handler)


class ElectrometerMixin:
    """Mixin class providing default controls and status for Electrometer."""

    def register_electrometer(self):
        def toggle_elm_filter(enabled):
            self.elm_filter_count.enabled = enabled
            self.elmFilterCountLabel.setEnabled(enabled)
            self.elm_filter_type.enabled = enabled
            self.elmFilterTypeLabel.setEnabled(enabled)

        self.elm_filter_enable = ui.CheckBox(text="Enable", changed=toggle_elm_filter)
        self.elm_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.elmFilterCountLabel = QtWidgets.QLabel("Count", self)
        self.elm_filter_type = ui.ComboBox(["repeat", "moving"])
        self.elmFilterTypeLabel = QtWidgets.QLabel("Type", self)

        self.elm_zero_correction = ui.CheckBox(text="Zero Correction")
        self.elm_integration_rate = ui.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        def toggle_elm_current_autorange(enabled):
            self.elm_current_range.enabled = not enabled
            self.elm_current_autorange_minimum.enabled = enabled
            self.elm_current_autorange_maximum.enabled = enabled

        self.elm_current_range = ui.Metric(minimum=0, decimals=3, prefixes="munp", unit="A")
        self.elm_current_autorange_enable = ui.CheckBox(text="Enable", changed=toggle_elm_current_autorange)
        self.elm_current_autorange_minimum = ui.Metric(minimum=0, decimals=3, prefixes="munp", unit="A")
        self.elm_current_autorange_maximum = ui.Metric(minimum=0, decimals=3, prefixes="munp", unit="A")

        toggle_elm_filter(False)
        toggle_elm_current_autorange(False)

        self.bind("elm_filter_enable", self.elm_filter_enable, False)
        self.bind("elm_filter_count", self.elm_filter_count, 10)
        self.bind("elm_filter_type", self.elm_filter_type, "repeat")
        self.bind("elm_zero_correction", self.elm_zero_correction, False)
        self.bind("elm_integration_rate", self.elm_integration_rate, 50.0)
        self.bind("elm_current_range", self.elm_current_range, 20e-12, unit="A")
        self.bind("elm_current_autorange_enable", self.elm_current_autorange_enable, False)
        self.bind("elm_current_autorange_minimum", self.elm_current_autorange_minimum, 2.0E-11, unit="A")
        self.bind("elm_current_autorange_maximum", self.elm_current_autorange_maximum, 2.0E-2, unit="A")

        self.status_elm_current = ui.Text(value=NO_VALUE, readonly=True)

        self.bind("status_elm_current", self.status_elm_current, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("Electrometer Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 0)
        statusGroupBoxLayout.addWidget(self.status_elm_current.qt, 1, 0)
        statusGroupBoxLayout.setColumnStretch(0, 1)
        statusGroupBoxLayout.setColumnStretch(1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        filterGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(self.elm_filter_enable.qt)
        filterGroupBoxLayout.addWidget(self.elmFilterCountLabel)
        filterGroupBoxLayout.addWidget(self.elm_filter_count.qt)
        filterGroupBoxLayout.addWidget(self.elmFilterTypeLabel)
        filterGroupBoxLayout.addWidget(self.elm_filter_type.qt)
        filterGroupBoxLayout.addStretch()

        rangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        rangeGroupBox.setTitle("Range")

        rangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(rangeGroupBox)
        rangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Range", self))
        rangeGroupBoxLayout.addWidget(self.elm_current_range.qt)

        autoRangeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        autoRangeGroupBox.setTitle("Auto Range")

        autoRangeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(autoRangeGroupBox)
        autoRangeGroupBoxLayout.addWidget(self.elm_current_autorange_enable.qt)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Minimum Current", self))
        autoRangeGroupBoxLayout.addWidget(self.elm_current_autorange_minimum.qt)
        autoRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum Current", self))
        autoRangeGroupBoxLayout.addWidget(self.elm_current_autorange_maximum.qt)
        autoRangeGroupBoxLayout.addStretch()

        rangeLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        rangeLayout.addWidget(rangeGroupBox)
        rangeLayout.addWidget(autoRangeGroupBox)

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(self.elm_zero_correction.qt)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Rate", self))
        optionsGroupBoxLayout.addWidget(self.elm_integration_rate.qt)
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
                self.status_elm_current.value = format_metric(value, "A")
        self.state_handlers.append(handler)


class LCRMixin:
    """Mixin class providing default controls and status for LCR Meter."""

    def register_lcr(self):
        def change_lcr_open_correction_mode(mode):
            self.lcr_open_correction_channel.enabled = mode == "multi"

        self.lcr_integration_time = ui.ComboBox(["short", "medium", "long"])
        self.lcr_averaging_rate = ui.Number(minimum=1, maximum=256, decimals=0)
        self.lcr_auto_level_control = ui.CheckBox(text="Auto Level Control")
        self.lcr_soft_filter = ui.CheckBox(text="Filter STD/mean < 0.005")
        self.lcr_open_correction_mode = ui.ComboBox(["single", "multi"], changed=change_lcr_open_correction_mode)
        self.lcr_open_correction_channel = ui.Number(minimum=0, maximum=127, decimals=0)

        change_lcr_open_correction_mode(self.lcr_open_correction_mode.current)

        self.bind("lcr_integration_time", self.lcr_integration_time, "medium")
        self.bind("lcr_averaging_rate", self.lcr_averaging_rate, 1)
        self.bind("lcr_auto_level_control", self.lcr_auto_level_control, True)
        self.bind("lcr_soft_filter", self.lcr_soft_filter, True)
        self.bind("lcr_open_correction_mode", self.lcr_open_correction_mode, "single")
        self.bind("lcr_open_correction_channel", self.lcr_open_correction_channel, 0)

        self.status_lcr_voltage = ui.Text(value=NO_VALUE, readonly=True)
        self.status_lcr_current = ui.Text(value=NO_VALUE, readonly=True)
        self.status_lcr_output = ui.Text(value=NO_VALUE, readonly=True)

        self.bind("status_lcr_voltage", self.status_lcr_voltage, NO_VALUE)
        self.bind("status_lcr_current", self.status_lcr_current, NO_VALUE)
        self.bind("status_lcr_output", self.status_lcr_output, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("LCR Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Voltage", self), 0, 0)
        statusGroupBoxLayout.addWidget(self.status_lcr_voltage.qt, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Current", self), 0, 1)
        statusGroupBoxLayout.addWidget(self.status_lcr_current.qt, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Output", self), 0, 2)
        statusGroupBoxLayout.addWidget(self.status_lcr_output.qt, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        openCorrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        openCorrGroupBox.setTitle("Open Correction")

        openCorrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(openCorrGroupBox)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Method", self))
        openCorrGroupBoxLayout.addWidget(self.lcr_open_correction_mode.qt)
        openCorrGroupBoxLayout.addWidget(QtWidgets.QLabel("Channel", self))
        openCorrGroupBoxLayout.addWidget(self.lcr_open_correction_channel.qt)
        openCorrGroupBoxLayout.addStretch()

        optionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Integration Time", self))
        optionsGroupBoxLayout.addWidget(self.lcr_integration_time.qt)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Averaging Rate", self))
        optionsGroupBoxLayout.addWidget(self.lcr_averaging_rate.qt)
        optionsGroupBoxLayout.addWidget(self.lcr_auto_level_control.qt)
        optionsGroupBoxLayout.addWidget(self.lcr_soft_filter.qt)
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
                self.status_lcr_voltage.value = format_metric(value, "V")
            if "lcr_current" in state:
                value = state.get("lcr_current")
                self.status_lcr_current.value = format_metric(value, "A")
            if "lcr_output" in state:
                value = state.get("lcr_output")
                self.status_lcr_output.value = format_switch(value, default=NO_VALUE)

        self.state_handlers.append(handler)


class EnvironmentMixin:
    """Mixin class providing default controls and status for Environment box."""

    def register_environment(self):
        self.status_env_chuck_temperature = ui.Text(value=NO_VALUE, readonly=True)
        self.status_env_box_temperature = ui.Text(value=NO_VALUE, readonly=True)
        self.status_env_box_humidity = ui.Text(value=NO_VALUE, readonly=True)

        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, NO_VALUE)
        self.bind("status_env_box_temperature", self.status_env_box_temperature, NO_VALUE)
        self.bind("status_env_box_humidity", self.status_env_box_humidity, NO_VALUE)

        statusGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        statusGroupBox.setTitle("Environment Status")

        statusGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(statusGroupBox)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Chuck temp.", self), 0, 0)
        statusGroupBoxLayout.addWidget(self.status_env_chuck_temperature.qt, 1, 0)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box temp.", self), 0, 1)
        statusGroupBoxLayout.addWidget(self.status_env_box_temperature.qt, 1, 1)
        statusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box humid.", self), 0, 2)
        statusGroupBoxLayout.addWidget(self.status_env_box_humidity.qt, 1, 2)

        self.statusPanelLayout.addWidget(statusGroupBox)

        def handler(state: dict) -> None:
            if "env_chuck_temperature" in state:
                value = state.get("env_chuck_temperature")
                self.status_env_chuck_temperature.value = format_metric(value, "°C", decimals=2)
            if "env_box_temperature" in state:
                value = state.get("env_box_temperature")
                self.status_env_box_temperature.value = format_metric(value, "°C", decimals=2)
            if "env_box_humidity" in state:
                value = state.get("env_box_humidity")
                self.status_env_box_humidity.value = format_metric(value, "%rH", decimals=2)

        self.state_handlers.append(handler)

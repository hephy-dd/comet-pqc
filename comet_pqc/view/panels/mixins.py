from PyQt5 import QtWidgets

from comet import ui

from comet_pqc.utils import format_metric, format_switch
from ..components import Metric

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
        self.hvsrc_sense_mode = QtWidgets.QComboBox(self)
        self.hvsrc_sense_mode.addItems(["local", "remote"])

        self.hvsrc_route_terminal = QtWidgets.QComboBox(self)
        self.hvsrc_route_terminal.addItems(["front", "rear"])

        def toggle_hvsrc_filter(enabled):
            self.hvsrc_filter_count.setEnabled(enabled)
            self.hvsrc_filter_count_label.setEnabled(enabled)
            self.hvsrc_filter_type.setEnabled(enabled)
            self.hvsrc_filter_type_label.setEnabled(enabled)

        self.hvsrc_filter_enable = QtWidgets.QCheckBox(self)
        self.hvsrc_filter_enable.setText("Enable")
        self.hvsrc_filter_enable.toggled.connect(toggle_hvsrc_filter)

        self.hvsrc_filter_count = QtWidgets.QSpinBox(self)
        self.hvsrc_filter_count.setRange(1, 100)

        self.hvsrc_filter_count_label = QtWidgets.QLabel(self)
        self.hvsrc_filter_count_label.setText("Count")

        self.hvsrc_filter_type = QtWidgets.QComboBox(self)
        self.hvsrc_filter_type.addItems(["repeat", "moving"])

        self.hvsrc_filter_type_label = QtWidgets.QLabel(self)
        self.hvsrc_filter_type_label.setText("Type")

        def toggle_hvsrc_source_voltage_autorange(enabled):
            self.hvsrc_source_voltage_range.setEnabled(not enabled)

        self.hvsrc_source_voltage_autorange_enable = QtWidgets.QCheckBox(self)
        self.hvsrc_source_voltage_autorange_enable.setText("Autorange")
        self.hvsrc_source_voltage_autorange_enable.toggled.connect(toggle_hvsrc_source_voltage_autorange)

        self.hvsrc_source_voltage_range = QtWidgets.QDoubleSpinBox(self)
        self.hvsrc_source_voltage_range.setDecimals(1)
        self.hvsrc_source_voltage_range.setRange(-2200, +2200)
        self.hvsrc_source_voltage_range.setSuffix(" V")

        toggle_hvsrc_filter(False)
        toggle_hvsrc_source_voltage_autorange(False)

        self.status_hvsrc_voltage = QtWidgets.QLineEdit(self)
        self.status_hvsrc_voltage.setReadOnly(True)
        self.status_hvsrc_voltage.setText(NO_VALUE)

        self.status_hvsrc_current = QtWidgets.QLineEdit(self)
        self.status_hvsrc_current.setReadOnly(True)
        self.status_hvsrc_current.setText(NO_VALUE)

        self.status_hvsrc_output = QtWidgets.QLineEdit(self)
        self.status_hvsrc_output.setReadOnly(True)
        self.status_hvsrc_output.setText(NO_VALUE)

        self.hvsrc_status_group_box = QtWidgets.QGroupBox(self)
        self.hvsrc_status_group_box.setTitle("HV Source Status")

        hvsrc_status_group_box_layout = QtWidgets.QGridLayout(self.hvsrc_status_group_box)
        hvsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        hvsrc_status_group_box_layout.addWidget(self.status_hvsrc_voltage, 1, 0)
        hvsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        hvsrc_status_group_box_layout.addWidget(self.status_hvsrc_current, 1, 1)
        hvsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        hvsrc_status_group_box_layout.addWidget(self.status_hvsrc_output, 1, 2)
        hvsrc_status_group_box_layout.setColumnStretch(0, 1)
        hvsrc_status_group_box_layout.setColumnStretch(1, 1)
        hvsrc_status_group_box_layout.setColumnStretch(2, 1)

        self.statusWidget.layout().addWidget(self.hvsrc_status_group_box)

        # Filter

        filterGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_enable)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_count_label)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_count)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_type_label)
        filterGroupBoxLayout.addWidget(self.hvsrc_filter_type)
        filterGroupBoxLayout.addStretch()

        # Source voltage range

        srcVoltageRangeGroupBox = QtWidgets.QGroupBox(self)
        srcVoltageRangeGroupBox.setTitle("Source Voltage Range")

        srcVoltageRangeGroupBoxLayout = QtWidgets.QVBoxLayout(srcVoltageRangeGroupBox)
        srcVoltageRangeGroupBoxLayout.addWidget(self.hvsrc_source_voltage_autorange_enable)
        srcVoltageRangeGroupBoxLayout.addWidget(QtWidgets.QLabel("Range"))
        srcVoltageRangeGroupBoxLayout.addWidget(self.hvsrc_source_voltage_range)
        srcVoltageRangeGroupBoxLayout.addStretch()

        # Options

        optionsGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.hvsrc_sense_mode)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Route Terminal"))
        optionsGroupBoxLayout.addWidget(self.hvsrc_route_terminal)
        optionsGroupBoxLayout.addStretch()

        # HV source tab

        widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(filterGroupBox, 1)
        layout.addWidget(srcVoltageRangeGroupBox, 1)
        layout.addWidget(optionsGroupBox, 1)

        self.controlTabWidget.addTab(widget, "HV Source")

        # Bindings

        self.bind("hvsrc_sense_mode", self.hvsrc_sense_mode, "local")
        self.bind("hvsrc_route_terminal", self.hvsrc_route_terminal, "rear")
        self.bind("hvsrc_filter_enable", self.hvsrc_filter_enable, False)
        self.bind("hvsrc_filter_count", self.hvsrc_filter_count, 10)
        self.bind("hvsrc_filter_type", self.hvsrc_filter_type, "repeat")
        self.bind("hvsrc_source_voltage_autorange_enable", self.hvsrc_source_voltage_autorange_enable, True)
        self.bind("hvsrc_source_voltage_range", self.hvsrc_source_voltage_range, 20, unit="V")

        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, NO_VALUE)
        self.bind("status_hvsrc_current", self.status_hvsrc_current, NO_VALUE)
        self.bind("status_hvsrc_output", self.status_hvsrc_output, NO_VALUE)

        # Handler

        def handler(state):
            if "hvsrc_voltage" in state:
                value = state.get("hvsrc_voltage")
                self.status_hvsrc_voltage.setText(format_metric(value, "V"))
            if "hvsrc_current" in state:
                value = state.get("hvsrc_current")
                self.status_hvsrc_current.setText(format_metric(value, "A"))
            if "hvsrc_output" in state:
                value = state.get("hvsrc_output")
                self.status_hvsrc_output.setText(format_switch(value, default=NO_VALUE))

        self.state_handlers.append(handler)


class VSourceMixin:
    """Mixin class providing default controls and status for V Source."""

    def register_vsource(self):
        self.vsrc_sense_mode = QtWidgets.QComboBox(self)
        self.vsrc_sense_mode.addItems(["local", "remote"])

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.setEnabled(enabled)
            self.vsrc_filter_count_label.setEnabled(enabled)
            self.vsrc_filter_type.setEnabled(enabled)
            self.vsrc_filter_type_label.setEnabled(enabled)

        self.vsrc_filter_enable = QtWidgets.QCheckBox(self)
        self.vsrc_filter_enable.setText("Enable")
        self.vsrc_filter_enable.toggled.connect(toggle_vsrc_filter)

        self.vsrc_filter_count = QtWidgets.QSpinBox(self)
        self.vsrc_filter_count.setRange(1, 100)

        self.vsrc_filter_count_label = QtWidgets.QLabel(self)
        self.vsrc_filter_count_label.setText("Count")

        self.vsrc_filter_type = QtWidgets.QComboBox(self)
        self.vsrc_filter_type.addItems(["repeat", "moving"])

        self.vsrc_filter_type_label = QtWidgets.QLabel(self)
        self.vsrc_filter_type_label.setText("Type")

        toggle_vsrc_filter(False)

        self.status_vsrc_voltage = QtWidgets.QLineEdit(self)
        self.status_vsrc_voltage.setReadOnly(True)
        self.status_vsrc_voltage.setText(NO_VALUE)

        self.status_vsrc_current = QtWidgets.QLineEdit(self)
        self.status_vsrc_current.setReadOnly(True)
        self.status_vsrc_current.setText(NO_VALUE)

        self.status_vsrc_output = QtWidgets.QLineEdit(self)
        self.status_vsrc_output.setReadOnly(True)
        self.status_vsrc_output.setText(NO_VALUE)

        self.vsrc_status_group_box = QtWidgets.QGroupBox(self)
        self.vsrc_status_group_box.setTitle("V Source Status")

        vsrc_status_group_box_layout = QtWidgets.QGridLayout(self.vsrc_status_group_box)
        vsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        vsrc_status_group_box_layout.addWidget(self.status_vsrc_voltage, 1, 0)
        vsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        vsrc_status_group_box_layout.addWidget(self.status_vsrc_current, 1, 1)
        vsrc_status_group_box_layout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        vsrc_status_group_box_layout.addWidget(self.status_vsrc_output, 1, 2)
        vsrc_status_group_box_layout.setColumnStretch(0, 1)
        vsrc_status_group_box_layout.setColumnStretch(1, 1)
        vsrc_status_group_box_layout.setColumnStretch(2, 1)

        self.statusWidget.layout().addWidget(self.vsrc_status_group_box)

        # Filter

        filterGroupBox = QtWidgets.QGroupBox(self)
        filterGroupBox.setTitle("Filter")

        filterGroupBoxLayout = QtWidgets.QVBoxLayout(filterGroupBox)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_enable)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_count_label)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_count)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_type_label)
        filterGroupBoxLayout.addWidget(self.vsrc_filter_type)
        filterGroupBoxLayout.addStretch()

        # Options

        optionsGroupBox = QtWidgets.QGroupBox(self)
        optionsGroupBox.setTitle("Options")

        optionsGroupBoxLayout = QtWidgets.QVBoxLayout(optionsGroupBox)
        optionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Sense Mode"))
        optionsGroupBoxLayout.addWidget(self.vsrc_sense_mode)
        optionsGroupBoxLayout.addStretch()

        # V source tab

        widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(filterGroupBox, 1)
        layout.addWidget(optionsGroupBox, 1)
        layout.addStretch(1)

        self.controlTabWidget.addTab(widget, "V Source")

        # Bindings

        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")

        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, NO_VALUE)
        self.bind("status_vsrc_current", self.status_vsrc_current, NO_VALUE)
        self.bind("status_vsrc_output", self.status_vsrc_output, NO_VALUE)

        # Handler

        def handler(state):
            if "vsrc_voltage" in state:
                value = state.get("vsrc_voltage")
                self.status_vsrc_voltage.setText(format_metric(value, "V"))
            if "vsrc_current" in state:
                value = state.get("vsrc_current")
                self.status_vsrc_current.setText(format_metric(value, "A"))
            if "vsrc_output" in state:
                value = state.get("vsrc_output")
                self.status_vsrc_output.setText(format_switch(value, default=NO_VALUE))

        self.state_handlers.append(handler)


class ElectrometerMixin:
    """Mixin class providing default controls and status for Electrometer."""

    def register_electrometer(self):
        def toggle_elm_filter(enabled):
            self.elm_filter_count.setEnabled(enabled)
            self.elm_filter_count_label.setEnabled(enabled)
            self.elm_filter_type.setEnabled(enabled)
            self.elm_filter_type_label.setEnabled(enabled)

        self.elm_filter_enable = QtWidgets.QCheckBox(self)
        self.elm_filter_enable.setText("Enable")
        self.elm_filter_enable.toggled.connect(toggle_elm_filter)

        self.elm_filter_count = QtWidgets.QSpinBox(self)
        self.elm_filter_count.setRange(1, 100)

        self.elm_filter_count_label = QtWidgets.QLabel(self)
        self.elm_filter_count_label.setText("Count")

        self.elm_filter_type = QtWidgets.QComboBox(self)
        self.elm_filter_type.addItems(["repeat", "moving"])

        self.elm_filter_type_label = QtWidgets.QLabel(self)
        self.elm_filter_type_label.setText("Type")

        self.elm_zero_correction = QtWidgets.QCheckBox(self)
        self.elm_zero_correction.setText("Zero Correction")

        self.elm_integration_rate = QtWidgets.QDoubleSpinBox(self)
        self.elm_integration_rate.setDecimals(2)
        self.elm_integration_rate.setRange(0, 100.0)
        self.elm_integration_rate.setSuffix(" Hz")

        def toggle_elm_current_autorange(enabled):
            self.elm_current_range.setEnabled(not enabled)
            self.elm_current_autorange_minimum.setEnabled(enabled)
            self.elm_current_autorange_maximum.setEnabled(enabled)

        self.elm_current_range = Metric(self)
        self.elm_current_range.setUnit("A")
        self.elm_current_range.setPrefixes("munp")
        self.elm_current_range.setDecimals(3)
        self.elm_current_range.setRange(0, float("inf"))

        self.elm_current_autorange_enable = QtWidgets.QCheckBox(self)
        self.elm_current_autorange_enable.setText("Enable")
        self.elm_current_autorange_enable.toggled.connect(toggle_elm_current_autorange)

        self.elm_current_autorange_minimum = Metric(self)
        self.elm_current_autorange_minimum.setUnit("A")
        self.elm_current_autorange_minimum.setPrefixes("munp")
        self.elm_current_autorange_minimum.setDecimals(3)
        self.elm_current_autorange_minimum.setRange(0, float("inf"))

        self.elm_current_autorange_maximum = Metric(self)
        self.elm_current_autorange_maximum.setUnit("A")
        self.elm_current_autorange_maximum.setPrefixes("munp")
        self.elm_current_autorange_maximum.setDecimals(3)
        self.elm_current_autorange_maximum.setRange(0, float("inf"))

        toggle_elm_filter(False)
        toggle_elm_current_autorange(False)

        self.status_elm_current = QtWidgets.QLineEdit(self)
        self.status_elm_current.setReadOnly(True)
        self.status_elm_current.setText(NO_VALUE)

        self.elm_status_group_box = QtWidgets.QGroupBox(self)
        self.elm_status_group_box.setTitle("Electrometer Status")

        elm_status_group_box_layout = QtWidgets.QGridLayout(self.elm_status_group_box)
        elm_status_group_box_layout.addWidget(QtWidgets.QLabel("Current"), 0, 0)
        elm_status_group_box_layout.addWidget(self.status_elm_current, 1, 0)
        elm_status_group_box_layout.setColumnStretch(0, 1)
        elm_status_group_box_layout.setColumnStretch(1, 1)
        elm_status_group_box_layout.setColumnStretch(2, 1)

        self.statusWidget.layout().addWidget(self.elm_status_group_box)

        # Filter

        filter_group_box = QtWidgets.QGroupBox(self)
        filter_group_box.setTitle("Filter")

        filter_group_box_layout = QtWidgets.QVBoxLayout(filter_group_box)
        filter_group_box_layout.addWidget(self.elm_filter_enable)
        filter_group_box_layout.addWidget(self.elm_filter_count_label)
        filter_group_box_layout.addWidget(self.elm_filter_count)
        filter_group_box_layout.addWidget(self.elm_filter_type_label)
        filter_group_box_layout.addWidget(self.elm_filter_type)
        filter_group_box_layout.addStretch()

        # Range

        range_group_box = QtWidgets.QGroupBox(self)
        range_group_box.setTitle("Range")

        range_group_box_layout = QtWidgets.QVBoxLayout(range_group_box)
        range_group_box_layout.addWidget(QtWidgets.QLabel("Current Range"))
        range_group_box_layout.addWidget(self.elm_current_range)

        # Auto Range

        auto_range_group_box = QtWidgets.QGroupBox(self)
        auto_range_group_box.setTitle("Auto Range")

        auto_range_group_box_layout = QtWidgets.QVBoxLayout(auto_range_group_box)
        auto_range_group_box_layout.addWidget(self.elm_current_autorange_enable)
        auto_range_group_box_layout.addWidget(QtWidgets.QLabel("Minimum Current"))
        auto_range_group_box_layout.addWidget(self.elm_current_autorange_minimum)
        auto_range_group_box_layout.addWidget(QtWidgets.QLabel("Maximum Current"))
        auto_range_group_box_layout.addWidget(self.elm_current_autorange_maximum)
        auto_range_group_box_layout.addStretch()

        # Options

        options_group_box = QtWidgets.QGroupBox(self)
        options_group_box.setTitle("Options")

        options_group_box_layout = QtWidgets.QVBoxLayout(options_group_box)
        options_group_box_layout.addWidget(self.elm_zero_correction)
        options_group_box_layout.addWidget(QtWidgets.QLabel("Integration Rate"))
        options_group_box_layout.addWidget(self.elm_integration_rate)
        options_group_box_layout.addStretch()

        # Electrometer tab

        widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QGridLayout(widget)
        layout.addWidget(filter_group_box, 0, 0, 2, 1)
        layout.addWidget(range_group_box, 0, 1)
        layout.addWidget(auto_range_group_box, 1, 1)
        layout.addWidget(options_group_box, 0, 2, 2, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

        self.controlTabWidget.addTab(widget, "Electrometer")

        # Bindings

        self.bind("elm_filter_enable", self.elm_filter_enable, False)
        self.bind("elm_filter_count", self.elm_filter_count, 10)
        self.bind("elm_filter_type", self.elm_filter_type, "repeat")
        self.bind("elm_zero_correction", self.elm_zero_correction, False)
        self.bind("elm_integration_rate", self.elm_integration_rate, 50.0)
        self.bind("elm_current_range", self.elm_current_range, 20e-12, unit="A")
        self.bind("elm_current_autorange_enable", self.elm_current_autorange_enable, False)
        self.bind("elm_current_autorange_minimum", self.elm_current_autorange_minimum, 2.0E-11, unit="A")
        self.bind("elm_current_autorange_maximum", self.elm_current_autorange_maximum, 2.0E-2, unit="A")

        self.bind("status_elm_current", self.status_elm_current, NO_VALUE)

        # Handler

        def handler(state):
            if "elm_current" in state:
                value = state.get("elm_current")
                self.status_elm_current.setText(format_metric(value, "A"))

        self.state_handlers.append(handler)


class LCRMixin:
    """Mixin class providing default controls and status for LCR Meter."""

    def register_lcr(self):
        def change_lcr_open_correction_mode(mode):
            self.lcr_open_correction_channel.setEnabled(mode == "multi")

        self.lcr_integration_time = QtWidgets.QComboBox(self)
        self.lcr_integration_time.addItems(["short", "medium", "long"])

        self.lcr_averaging_rate = QtWidgets.QSpinBox(self)
        self.lcr_averaging_rate.setRange(1, 256)

        self.lcr_auto_level_control = QtWidgets.QCheckBox(self)
        self.lcr_auto_level_control.setText("Auto Level Control")

        self.lcr_soft_filter = QtWidgets.QCheckBox(self)
        self.lcr_soft_filter.setText("Filter STD/mean < 0.005")

        self.lcr_open_correction_mode = QtWidgets.QComboBox(self)
        self.lcr_open_correction_mode.addItems(["single", "multi"])
        self.lcr_open_correction_mode.currentTextChanged.connect(change_lcr_open_correction_mode)

        self.lcr_open_correction_channel = QtWidgets.QSpinBox(self)
        self.lcr_open_correction_channel.setRange(0, 127)

        change_lcr_open_correction_mode(self.lcr_open_correction_mode.currentText())

        self.status_lcr_voltage = QtWidgets.QLineEdit(self)
        self.status_lcr_voltage.setReadOnly(True)
        self.status_lcr_voltage.setText(NO_VALUE)

        self.status_lcr_current = QtWidgets.QLineEdit(self)
        self.status_lcr_current.setReadOnly(True)
        self.status_lcr_current.setText(NO_VALUE)

        self.status_lcr_output = QtWidgets.QLineEdit(self)
        self.status_lcr_output.setReadOnly(True)
        self.status_lcr_output.setText(NO_VALUE)

        self.lcr_status_group_box = QtWidgets.QGroupBox(self)
        self.lcr_status_group_box.setTitle("LCR Status")

        lcr_status_group_box_layout = QtWidgets.QGridLayout(self.lcr_status_group_box)
        lcr_status_group_box_layout.addWidget(QtWidgets.QLabel("Voltage"), 0, 0)
        lcr_status_group_box_layout.addWidget(self.status_lcr_voltage, 1, 0)
        lcr_status_group_box_layout.addWidget(QtWidgets.QLabel("Current"), 0, 1)
        lcr_status_group_box_layout.addWidget(self.status_lcr_current, 1, 1)
        lcr_status_group_box_layout.addWidget(QtWidgets.QLabel("Output"), 0, 2)
        lcr_status_group_box_layout.addWidget(self.status_lcr_output, 1, 2)
        lcr_status_group_box_layout.setColumnStretch(0, 1)
        lcr_status_group_box_layout.setColumnStretch(1, 1)
        lcr_status_group_box_layout.setColumnStretch(2, 1)

        self.statusWidget.layout().addWidget(self.lcr_status_group_box)

        # Open Correction

        oc_group_box = QtWidgets.QGroupBox(self)
        oc_group_box.setTitle("Open Correction")

        oc_group_box_layout = QtWidgets.QVBoxLayout(oc_group_box)
        oc_group_box_layout.addWidget(QtWidgets.QLabel("Method"))
        oc_group_box_layout.addWidget(self.lcr_open_correction_mode)
        oc_group_box_layout.addWidget(QtWidgets.QLabel("Channel"))
        oc_group_box_layout.addWidget(self.lcr_open_correction_channel)
        oc_group_box_layout.addStretch()

        # Options

        options_group_box = QtWidgets.QGroupBox(self)
        options_group_box.setTitle("Options")

        options_group_box_layout = QtWidgets.QVBoxLayout(options_group_box)
        options_group_box_layout.addWidget(QtWidgets.QLabel("Integration Time"))
        options_group_box_layout.addWidget(self.lcr_integration_time)
        options_group_box_layout.addWidget(QtWidgets.QLabel("Averaging Rate"))
        options_group_box_layout.addWidget(self.lcr_averaging_rate)
        options_group_box_layout.addWidget(self.lcr_auto_level_control)
        options_group_box_layout.addWidget(self.lcr_soft_filter)
        options_group_box_layout.addStretch()

        widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(oc_group_box, 1)
        layout.addWidget(options_group_box, 1)
        layout.addStretch(1)

        self.controlTabWidget.addTab(widget, "LCR")

        # Bindings

        self.bind("lcr_integration_time", self.lcr_integration_time, "medium")
        self.bind("lcr_averaging_rate", self.lcr_averaging_rate, 1)
        self.bind("lcr_auto_level_control", self.lcr_auto_level_control, True)
        self.bind("lcr_soft_filter", self.lcr_soft_filter, True)
        self.bind("lcr_open_correction_mode", self.lcr_open_correction_mode, "single")
        self.bind("lcr_open_correction_channel", self.lcr_open_correction_channel, 0)

        self.bind("status_lcr_voltage", self.status_lcr_voltage, NO_VALUE)
        self.bind("status_lcr_current", self.status_lcr_current, NO_VALUE)
        self.bind("status_lcr_output", self.status_lcr_output, NO_VALUE)

        # Handler

        def handler(state):
            if "lcr_voltage" in state:
                value = state.get("lcr_voltage")
                self.status_lcr_voltage.setText(format_metric(value, "V"))
            if "lcr_current" in state:
                value = state.get("lcr_current")
                self.status_lcr_current.setText(format_metric(value, "A"))
            if "lcr_output" in state:
                value = state.get("lcr_output")
                self.status_lcr_output.setText(format_switch(value, default=NO_VALUE))

        self.state_handlers.append(handler)


class EnvironmentMixin:
    """Mixin class providing default controls and status for Environment box."""

    def register_environment(self) -> None:

        # Status

        self.status_env_chuck_temperature = QtWidgets.QLineEdit(self)
        self.status_env_chuck_temperature.setReadOnly(True)
        self.status_env_chuck_temperature.setText(NO_VALUE)

        self.status_env_box_temperature = QtWidgets.QLineEdit(self)
        self.status_env_box_temperature.setReadOnly(True)
        self.status_env_box_temperature.setText(NO_VALUE)

        self.status_env_box_humidity = QtWidgets.QLineEdit(self)
        self.status_env_box_humidity.setReadOnly(True)
        self.status_env_box_humidity.setText(NO_VALUE)

        self.environmentStatusGroupBox = QtWidgets.QGroupBox(self)
        self.environmentStatusGroupBox.setTitle("Environment Status")

        environmentStatusGroupBoxLayout = QtWidgets.QGridLayout(self.environmentStatusGroupBox)
        environmentStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Chuck temp."), 0, 0)
        environmentStatusGroupBoxLayout.addWidget(self.status_env_chuck_temperature, 1, 0)
        environmentStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box temp."), 0, 1)
        environmentStatusGroupBoxLayout.addWidget(self.status_env_box_temperature, 1, 1)
        environmentStatusGroupBoxLayout.addWidget(QtWidgets.QLabel("Box humid."), 0, 2)
        environmentStatusGroupBoxLayout.addWidget(self.status_env_box_humidity, 1, 2)
        environmentStatusGroupBoxLayout.setColumnStretch(0, 1)
        environmentStatusGroupBoxLayout.setColumnStretch(1, 1)
        environmentStatusGroupBoxLayout.setColumnStretch(2, 1)

        self.statusWidget.layout().addWidget(self.environmentStatusGroupBox)

        # Bindings

        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, NO_VALUE)
        self.bind("status_env_box_temperature", self.status_env_box_temperature, NO_VALUE)
        self.bind("status_env_box_humidity", self.status_env_box_humidity, NO_VALUE)

        # Handler

        def handler(state):
            if "env_chuck_temperature" in state:
                value = state.get("env_chuck_temperature")
                self.status_env_chuck_temperature.setText(format_metric(value, "°C", decimals=2))
            if "env_box_temperature" in state:
                value = state.get("env_box_temperature")
                self.status_env_box_temperature.setText(format_metric(value, "°C", decimals=2))
            if "env_box_humidity" in state:
                value = state.get("env_box_humidity")
                self.status_env_box_humidity.setText(format_metric(value, "%rH", decimals=2))

        self.state_handlers.append(handler)

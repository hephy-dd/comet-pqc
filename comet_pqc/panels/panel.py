import logging

from PyQt5 import QtCore

import comet

from ..utils import format_metric
from ..metric import Metric
from ..logwindow import LogWidget

__all__ = ["Panel"]

class VSourceMixin:

    def register_vsource(self):
        self.vsrc_sense_mode = comet.ComboBox(items=["local", "remote"])
        self.vsrc_route_termination = comet.ComboBox(items=["front", "rear"])

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.enabled = enabled
            self.vsrc_filter_count_label.enabled = enabled
            self.vsrc_filter_type.enabled = enabled
            self.vsrc_filter_type_label.enabled = enabled

        self.vsrc_filter_enable = comet.CheckBox(text="Enable", changed=toggle_vsrc_filter)
        self.vsrc_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.vsrc_filter_count_label = comet.Label(text="Count")
        self.vsrc_filter_type = comet.ComboBox(items=["repeat", "moving"])
        self.vsrc_filter_type_label = comet.Label(text="Type")

        toggle_vsrc_filter(False)

        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_route_termination", self.vsrc_route_termination, "front")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")

        self.status_vsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "---")
        self.status_vsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_current", self.status_vsrc_current, "---")
        self.status_vsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_output", self.status_vsrc_output, "---")

        self.status_panel.append(comet.GroupBox(
            title="V Source Status",
            layout=comet.Column(
                comet.Row(
                    comet.Column(
                        comet.Label("Voltage"),
                        self.status_vsrc_voltage
                    ),
                    comet.Column(
                        comet.Label("Current"),
                        self.status_vsrc_current
                    ),
                    comet.Column(
                        comet.Label("Output"),
                        self.status_vsrc_output
                    )
                )
            )
        ))

        self.control_tabs.append(comet.Tab(
            title="V Source",
            layout=comet.Row(
                comet.GroupBox(
                    title="Filter",
                    layout=comet.Column(
                        self.vsrc_filter_enable,
                        self.vsrc_filter_count_label,
                        self.vsrc_filter_count,
                        self.vsrc_filter_type_label,
                        self.vsrc_filter_type,
                        comet.Spacer()
                    )
                ),
                comet.GroupBox(
                    title="Options",
                    layout=comet.Column(
                        comet.Label(text="Sense Mode"),
                        self.vsrc_sense_mode,
                        comet.Label(text="Route Termination"),
                        self.vsrc_route_termination,
                        comet.Spacer()
                    )
                ),
                comet.Spacer(),
                stretch=(1, 1, 1)
            )
        ))

        def handler(state):
            if 'vsrc_voltage' in state:
                value = state.get('vsrc_voltage')
                self.status_vsrc_voltage.value = format_metric(value, "V")
            if 'vsrc_current' in state:
                value = state.get('vsrc_current')
                self.status_vsrc_current.value = format_metric(value, "A")
            if 'vsrc_output' in state:
                labels = {False: "OFF", True: "ON", None: "---"}
                self.status_vsrc_output.value = labels[state.get('vsrc_output')]

        self.state_handlers.append(handler)

class EnvironmentMixin:

    def register_environment(self):
        self.status_env_chuck_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, "---")
        self.status_env_box_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_temperature", self.status_env_box_temperature, "---")
        self.status_env_box_humidity = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_humidity", self.status_env_box_humidity, "---")

        self.status_panel.append(comet.GroupBox(
            title="Environment Status",
            layout=comet.Column(
                comet.Row(
                    comet.Column(
                        comet.Label("Chuck temp."),
                        self.status_env_chuck_temperature
                    ),
                    comet.Column(
                        comet.Label("Box temp."),
                        self.status_env_box_temperature
                    ),
                    comet.Column(
                        comet.Label("Box humid."),
                        self.status_env_box_humidity
                    )
                )
            )
        ))

        def handler(state):
            if 'env_chuck_temperature' in state:
                value = state.get('env_chuck_temperature',)
                self.status_env_chuck_temperature.value = format_metric(value, "°C", decimals=2)
            if 'env_box_temperature' in state:
                value = state.get('env_box_temperature')
                self.status_env_box_temperature.value = format_metric(value, "°C", decimals=2)
            if 'env_box_humidity' in state:
                value = state.get('env_box_humidity')
                self.status_env_box_humidity.value = format_metric(value, "%rH", decimals=2)

        self.state_handlers.append(handler)

class Panel(comet.Widget):
    """Base class for measurement panels."""

    type = "measurement"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bindings = {}
        self.state_handlers = []
        self.title_label = comet.Label(
            stylesheet="font-size: 16px; font-weight: bold; background-color: white; height: 32px;"
        )
        self.title_label.qt.setTextFormat(QtCore.Qt.RichText)
        self.description_label = comet.Label()
        self.data_panel = comet.Column()
        self.general_tab = comet.Tab(
                title="General",
                layout=comet.Row()
            )
        self.control_tabs = comet.Tabs(self.general_tab)
        self.status_panel = comet.Column()
        self.status_panel.width = 280
        self.control_panel = comet.Row(
            self.control_tabs,
            self.status_panel,
            stretch=(3, 1)
        )
        self.layout = comet.Column(
            self.title_label,
            self.description_label,
            self.data_panel,
            self.control_panel,
            comet.Spacer(),
            stretch=(0, 0, 0, 0, 1)
        )
        self.measurement = None
        self.log_widget = LogWidget()
        self.data_tabs = comet.Tabs()
        self.data_tabs.append(comet.Tab(title="Logs", layout=self.log_widget))
        self.data_panel.append(self.data_tabs)

        self.bind("logs", self.log_widget, [])

    def bind(self, key, element, default=None, unit=None):
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> self.value = comet.Number()
        >>> self.bind("value", self.value, default=10.0, unit="V")
        """
        self._bindings[key] = element, default, unit

    def mount(self, measurement):
        """Mount measurement to panel."""
        self.unmount()
        self.title_label.text = f"{self.title} &rarr; {measurement.name}"
        self.description_label.text = measurement.description
        self.measurement = measurement
        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, item in self._bindings.items():
            element, default, unit = item
            value = parameters.get(key, default)
            if unit is not None:
                if isinstance(value, comet.ureg.Quantity):
                    value = value.to(unit).m
            if isinstance(element, comet.List):
                setattr(element, "values", value)
            elif isinstance(element, comet.ComboBox):
                setattr(element, "current", value)
            elif isinstance(element, comet.CheckBox):
                setattr(element, "checked", value)
            elif isinstance(element, comet.Text):
                setattr(element, "value", value)
            elif isinstance(element, comet.Label):
                setattr(element, "text", format(value))
            elif isinstance(element, Metric):
                setattr(element, "value", value)
            else:
                setattr(element, "value", value)
        # Show first tab on mount
        self.data_tabs.qt.setCurrentIndex(0)
        # Load hiostory, attach logger
        self.log_widget.load(self.measurement.parameters.get("history", []))
        self.log_widget.add_logger(logging.getLogger())

    def unmount(self):
        """Unmount measurement from panel."""
        # Detach logger
        self.log_widget.remove_logger(logging.getLogger())
        if self.measurement:
            self.measurement.parameters["history"] = self.log_widget.dump()
        self.title_label.text = ""
        self.description_label.text = ""
        self.measurement = None

    def store(self):
        """Store UI element values to measurement parameters."""
        if self.measurement:
            parameters = self.measurement.parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                if isinstance(element, comet.List):
                    value = getattr(element, "values")
                elif isinstance(element, comet.ComboBox):
                    value = getattr(element, "current")
                elif isinstance(element, comet.CheckBox):
                    value = getattr(element, "checked")
                elif isinstance(element, comet.Text):
                    value = getattr(element, "value")
                elif isinstance(element, comet.Label):
                    value = getattr(element, "text")
                elif isinstance(element, Metric):
                    value = getattr(element, "value")
                else:
                    value = getattr(element, "value")
                if unit is not None:
                    value = value * comet.ureg(unit)
                parameters[key] = value

    def restore(self):
        """Restore measurement defaults."""
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                value = default_parameters.get(key, default)
                if unit is not None:
                    if isinstance(value, comet.ureg.Quantity):
                        value = value.to(unit).m
                if isinstance(element, comet.List):
                    setattr(element, "values", value)
                elif isinstance(element, comet.ComboBox):
                    setattr(element, "current", value)
                elif isinstance(element, comet.CheckBox):
                    setattr(element, "checked", value)
                elif isinstance(element, comet.Text):
                    setattr(element, "value", value)
                elif isinstance(element, Metric):
                    setattr(element, "value", value)
                else:
                    setattr(element, "value", value)

    def state(self, state):
        for handler in self.state_handlers:
            handler(state)

    def append_reading(self, name, x, y):
        pass

    def update_readings(self):
        pass

    def clear_readings(self):
        self.log_widget.clear()

    def lock(self):
        #self.control_panel.enabled = False
        for tab in self.control_tabs:
            tab.enabled = False
        if self.general_tab in self.control_tabs:
            self.control_tabs.current = self.general_tab
        self.control_tabs.enabled = True
        self.status_panel.enabled = True

    def unlock(self):
        #self.control_panel.enabled = True
        for tab in self.control_tabs:
            tab.enabled = True

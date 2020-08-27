import logging

from PyQt5 import QtCore

import comet
from comet import ui

from ..utils import format_metric

__all__ = ['Panel']

class Panel(ui.Widget):
    """Base class for measurement panels."""

    type = "measurement"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bindings = {}
        self.state_handlers = []
        self.title_label = ui.Label(
            stylesheet="font-size: 16px; font-weight: bold; height: 32px;"
        )
        self.title_label.qt.setTextFormat(QtCore.Qt.RichText)
        self.description_label = ui.Label()
        self.data_panel = ui.Column()
        self.general_tab = ui.Tab(
                title="General",
                layout=ui.Row()
            )
        self.control_tabs = ui.Tabs(self.general_tab)
        self.status_panel = ui.Column()
        self.control_panel = ui.Row(
            self.control_tabs,
            ui.Column(
                self.status_panel,
                ui.Spacer(horizontal=False)
            ),
            stretch=(3, 1)
        )
        self.layout = ui.Column(
            self.title_label,
            self.description_label,
            self.data_panel,
            self.control_panel,
            ui.Spacer(),
            stretch=(0, 0, 0, 0, 1)
        )
        self.measurement = None
        self.data_tabs = ui.Tabs()
        self.data_panel.append(self.data_tabs)

    def bind(self, key, element, default=None, unit=None):
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> self.value = ui.Number()
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
            if isinstance(element, ui.List):
                setattr(element, "values", value)
            elif isinstance(element, ui.ComboBox):
                setattr(element, "current", value)
            elif isinstance(element, ui.CheckBox):
                setattr(element, "checked", value)
            elif isinstance(element, ui.Text):
                setattr(element, "value", value)
            elif isinstance(element, ui.Label):
                setattr(element, "text", format(value))
            elif isinstance(element, ui.Metric):
                setattr(element, "value", value)
            else:
                setattr(element, "value", value)
        # Show first tab on mount
        self.data_tabs.qt.setCurrentIndex(0)

    def unmount(self):
        """Unmount measurement from panel."""
        self.title_label.text = ""
        self.description_label.text = ""
        self.measurement = None

    def store(self):
        """Store UI element values to measurement parameters."""
        if self.measurement:
            parameters = self.measurement.parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                if isinstance(element, ui.List):
                    value = getattr(element, "values")
                elif isinstance(element, ui.ComboBox):
                    value = getattr(element, "current")
                elif isinstance(element, ui.CheckBox):
                    value = getattr(element, "checked")
                elif isinstance(element, ui.Text):
                    value = getattr(element, "value")
                elif isinstance(element, ui.Label):
                    value = getattr(element, "text")
                elif isinstance(element, ui.Metric):
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
                if isinstance(element, ui.List):
                    setattr(element, "values", value)
                elif isinstance(element, ui.ComboBox):
                    setattr(element, "current", value)
                elif isinstance(element, ui.CheckBox):
                    setattr(element, "checked", value)
                elif isinstance(element, ui.Text):
                    setattr(element, "value", value)
                elif isinstance(element, ui.Metric):
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
        pass

    def lock(self):
        for tab in self.control_tabs:
            tab.enabled = False
        if self.general_tab in self.control_tabs:
            self.control_tabs.current = self.general_tab
        self.control_tabs.enabled = True
        self.status_panel.enabled = True

    def unlock(self):
        for tab in self.control_tabs:
            tab.enabled = True

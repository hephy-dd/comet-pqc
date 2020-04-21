import logging

from PyQt5 import QtCore

import comet

__all__ = ["Panel"]

class Handler(logging.Handler):

    targets = []

    def emit(self, record):
        for target in self.targets:
            target(record)

class Panel(comet.Widget):
    """Base class for measurement panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stream_handler = Handler()
        self._stream_handler.setLevel(logging.DEBUG)
        self._bindings = {}
        self.title_label = comet.Label(
            stylesheet="font-size: 16px; font-weight: bold; background-color: white; height: 32px;"
        )
        self.title_label.qt.setTextFormat(QtCore.Qt.RichText)
        self.description_label = comet.Label()
        self.data = comet.Column()
        self.controls = comet.Column()
        self.layout = comet.Column(
            self.title_label,
            self.description_label,
            self.data,
            self.controls,
            comet.Stretch(),
            stretch=(0, 0, 0, 0, 1)
        )
        self.unmount()

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
        logging.getLogger().addHandler(self._stream_handler)
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
            elif isinstance(element, comet.Select):
                setattr(element, "current", value)
            elif isinstance(element, comet.CheckBox):
                setattr(element, "checked", value)
            elif isinstance(element, comet.Text):
                setattr(element, "value", value)
            else:
                setattr(element, "value", value)

    def unmount(self):
        """Unmount measurement from panel."""
        self.title_label.text = ""
        self.description_label.text = ""
        self.measurement = None
        logging.getLogger().removeHandler(self._stream_handler)

    def store(self):
        """Store UI element values to measurement parameters."""
        if self.measurement:
            parameters = self.measurement.parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                if isinstance(element, comet.List):
                    value = getattr(element, "values")
                elif isinstance(element, comet.Select):
                    value = getattr(element, "current")
                elif isinstance(element, comet.CheckBox):
                    value = getattr(element, "checked")
                elif isinstance(element, comet.Text):
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
                elif isinstance(element, comet.Select):
                    setattr(element, "current", value)
                elif isinstance(element, comet.CheckBox):
                    setattr(element, "checked", value)
                elif isinstance(element, comet.Text):
                    setattr(element, "value", value)
                else:
                    setattr(element, "value", value)

    def append_reading(self, name, x, y):
        pass

    def update_readings(self):
        pass

    def clear_readings(self):
        pass

    @property
    def locked(self):
        """Returns True if panel controls are locked."""
        return self.controls.enabled

    @locked.setter
    def locked(self, locked):
        """Set lcoked state of panel controls."""
        self.controls.enabled = not locked

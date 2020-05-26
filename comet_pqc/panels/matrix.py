import logging

import comet
from comet.device import DeviceMixin

from ..logwindow import LogWidget
from .panel import Panel

__all__ = ["MatrixPanel"]

def encode_matrix(values):
    return ", ".join(map(format, values))

def decode_matrix(value):
    return list(map(str.strip, value.split(",")))

class MatrixChannelsText(comet.Text):
    """Overloaded text input to handle matrix channel list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def value(self):
        return decode_matrix(self.qt.text())

    @value.setter
    def value(self, value):
        self.qt.setText(encode_matrix(value or []))

class MatrixPanel(Panel, DeviceMixin):
    """Base class for matrix switching panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log_widget = LogWidget()

        self.data_tabs = comet.Tabs()
        self.data_tabs.append(comet.Tab(title="Logs", layout=self.log_widget))
        self.data.append(self.data_tabs)

        self.matrix_enabled = comet.CheckBox(text="Enable Switching")
        self.matrix_enabled.enabled = False
        self.matrix_channels = MatrixChannelsText(
            tooltip="Matrix card switching channels, comma separated list."
        )

        self.bind("logs", self.log_widget, [])
        self.bind("matrix_enabled", self.matrix_enabled, False)
        self.bind("matrix_channels", self.matrix_channels, [])

        self.controls.append(comet.FieldSet(
            title="Matrix",
            layout=comet.Column(
                self.matrix_enabled,
                comet.Label(text="Channels"),
                comet.Row(
                    self.matrix_channels,
                    comet.Button(text="Load from Matrix", clicked=self.load_matrix_channels)
                )
            )
        ))

    def load_matrix_channels(self):
        """Load closed matrix channels for slot 1 from instrument."""
        self.enabled = False
        try:
            with self.devices.get("matrix") as matrix:
                # Junk fix
                matrix.resource.write("print()")
                matrix.resource.read_raw()
                result = matrix.resource.query("print(channel.getclose('slot1'))")
                logging.info("Loaded matrix channels for slot 1: %s", result)
                channels = result.split(";")
            self.matrix_channels.value = channels
        except Exception as e:
            comet.show_exception(e)
        self.enabled = True

    def mount(self, measurement):
        super().mount(measurement)
        # Show first tab on mount
        self.data_tabs.qt.setCurrentIndex(0)
        # Load hiostory, attach logger
        self.log_widget.load(self.measurement.parameters.get("history", []))
        self.log_widget.add_logger(logging.getLogger())

    def unmount(self):
        # Detach logger
        self.log_widget.remove_logger(logging.getLogger())
        if self.measurement:
            self.measurement.parameters["history"] = self.log_widget.dump()
        super().unmount()

    def clear_readings(self):
        super().clear_readings()
        self.log_widget.clear()

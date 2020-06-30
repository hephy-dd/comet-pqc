import logging

import comet
from comet.resource import ResourceMixin

from ..driver import K707B
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

class MatrixPanel(Panel, ResourceMixin):
    """Base class for matrix switching panels."""

    type = "matrix"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.matrix_enabled = comet.CheckBox(text="Enable Switching")
        self.matrix_channels = MatrixChannelsText(
            tool_tip="Matrix card switching channels, comma separated list."
        )

        self.bind("matrix_enabled", self.matrix_enabled, False)
        self.bind("matrix_channels", self.matrix_channels, [])

        self.control_tabs.append(comet.Tab(
            title="Matrix",
            layout=comet.Column(
                comet.GroupBox(
                    title="Matrix",
                    layout=comet.Column(
                        self.matrix_enabled,
                        comet.Label(text="Channels"),
                        comet.Row(
                            self.matrix_channels,
                            ## comet.Button(text="Load from Matrix", clicked=self.load_matrix_channels)
                        )
                    )
                ),
                comet.Spacer(),
                stretch=(0, 1)
            )
        ))

    def load_matrix_channels(self):
        """Load closed matrix channels for slot 1 from instrument."""
        self.enabled = False
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                closed_channels = matrix.channel.getclose()
            self.matrix_channels.value = closed_channels
        except Exception as e:
            comet.show_exception(e)
        self.enabled = True

    def mount(self, measurement):
        super().mount(measurement)

    def unmount(self):
        super().unmount()

    def clear_readings(self):
        super().clear_readings()

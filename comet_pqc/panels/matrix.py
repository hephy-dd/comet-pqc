from comet import ui
from comet.driver.keithley import K707B
from comet.resource import ResourceMixin

from .panel import Panel

__all__ = ["MatrixPanel"]


def encode_matrix(values):
    return ", ".join(map(format, values))


def decode_matrix(value):
    return list(map(str.strip, value.split(",")))


class MatrixChannelsText(ui.Text):
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

        self.matrix_enable = ui.CheckBox(text="Enable Switching")
        self.matrix_channels = MatrixChannelsText(
            tool_tip="Matrix card switching channels, comma separated list."
        )

        self.bind("matrix_enable", self.matrix_enable, True)
        self.bind("matrix_channels", self.matrix_channels, [])

        self.control_tabs.append(ui.Tab(
            title="Matrix",
            layout=ui.Column(
                ui.GroupBox(
                    title="Matrix",
                    layout=ui.Column(
                        self.matrix_enable,
                        ui.Label(text="Channels"),
                        ui.Row(
                            self.matrix_channels,
                            # ui.Button(text="Load from Matrix", clicked=self.load_matrix_channels)
                        )
                    )
                ),
                ui.Spacer(),
                stretch=(0, 1)
            )
        ))

    # def load_matrix_channels(self):
    #     """Load closed matrix channels for slot 1 from instrument."""
    #     self.enabled = False
    #     try:
    #         with self.resources.get("matrix") as matrix_res:
    #             matrix = K707B(matrix_res)
    #             closed_channels = matrix.channel.getclose()
    #         self.matrix_channels.value = closed_channels
    #     except Exception as e:
    #         ui.show_exception(e)
    #     self.enabled = True

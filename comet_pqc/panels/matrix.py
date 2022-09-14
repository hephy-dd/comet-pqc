from comet import ui
from comet.resource import ResourceMixin
from PyQt5 import QtCore, QtWidgets

from .panel import MeasurementPanel

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


class MatrixPanel(MeasurementPanel, ResourceMixin):
    """Base class for matrix switching panels."""

    type = "matrix"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.matrix_enable = ui.CheckBox(text="Enable Switching")
        self.matrix_channels = MatrixChannelsText(
            tool_tip="Matrix card switching channels, comma separated list."
        )

        self.bind("matrix_enable", self.matrix_enable, True)
        self.bind("matrix_channels", self.matrix_channels, [])

        matrixGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        matrixGroupBox.setTitle("Matrix")

        matrixGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(matrixGroupBox)
        matrixGroupBoxLayout.addWidget(self.matrix_enable.qt)
        matrixGroupBoxLayout.addWidget(QtWidgets.QLabel("Channels", self))
        matrixGroupBoxLayout.addWidget(self.matrix_channels.qt)

        matrixWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        matrixWidgetLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(matrixWidget)
        matrixWidgetLayout.addWidget(matrixGroupBox)
        matrixWidgetLayout.addStretch()

        self.controlTabWidget.addTab(matrixWidget, "Matrix")

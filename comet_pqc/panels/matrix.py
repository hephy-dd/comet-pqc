from typing import Iterable, List

from comet.resource import ResourceMixin
from PyQt5 import QtCore, QtWidgets

from .panel import MeasurementPanel

__all__ = ["MatrixPanel"]


def encode_channels(values: Iterable[str]) -> str:
    return ", ".join(map(format, values))


def decode_channels(value) -> List[str]:
    return list(map(str.strip, value.split(",")))


class MatrixChannelsLineEdit(QtWidgets.QLineEdit):
    """Overloaded line edit to handle matrix channel list."""

    def channels(self) -> List[str]:
        return decode_channels(self.text())

    def setChannels(self, channels: Iterable[str]) -> None:
        self.setText(encode_channels(channels or []))


class MatrixPanel(MeasurementPanel, ResourceMixin):
    """Base class for matrix switching panels."""

    type = "matrix"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.matrix_enable: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.matrix_enable.setText("Enable Switching")

        self.matrix_channels = MatrixChannelsLineEdit(self)
        self.matrix_channels.setStatusTip("Matrix card switching channels, comma separated list.")

        self.bindings.register(MatrixChannelsLineEdit, lambda element: element.channels(), lambda element, value: element.setChannels(value))

        self.bind("matrix_enable", self.matrix_enable, True)
        self.bind("matrix_channels", self.matrix_channels, [])

        matrixGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        matrixGroupBox.setTitle("Matrix")

        matrixGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(matrixGroupBox)
        matrixGroupBoxLayout.addWidget(self.matrix_enable)
        matrixGroupBoxLayout.addWidget(QtWidgets.QLabel("Channels", self))
        matrixGroupBoxLayout.addWidget(self.matrix_channels)

        matrixWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        matrixWidgetLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(matrixWidget)
        matrixWidgetLayout.addWidget(matrixGroupBox)
        matrixWidgetLayout.addStretch()

        self.controlTabWidget.addTab(matrixWidget, "Matrix")

from comet.resource import ResourceMixin
from PyQt5 import QtCore, QtWidgets

from .panel import MeasurementPanel, MatrixChannelsLineEdit

__all__ = ["MatrixPanel"]


class MatrixPanel(MeasurementPanel, ResourceMixin):
    """Base class for matrix switching panels."""

    type = "matrix"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.matrix_enable: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.matrix_enable.setText("Enable Switching")

        self.matrix_channels = MatrixChannelsLineEdit(self)
        self.matrix_channels.setStatusTip("Matrix card switching channels, comma separated list.")

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

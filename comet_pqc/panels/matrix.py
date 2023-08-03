from typing import List, Optional

from PyQt5 import QtWidgets

from ..utils import join_channels, split_channels

from .panel import Panel

__all__ = ["MatrixPanel"]


class MatrixChannelsEdit(QtWidgets.QLineEdit):
    """Custom QLineEdit to handle matrix channel list."""

    def channels(self) -> List[str]:
        return split_channels(self.text())

    def setChannels(self, channels: List[str]) -> None:
        self.setText(join_channels(channels))


class MatrixPanel(Panel):
    """Base class for matrix switching panels."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Matrix enable

        self.matrixEnableCheckBox = QtWidgets.QCheckBox(self)
        self.matrixEnableCheckBox.setText("Enable Switching")

        # Matrix channels

        self.matrixChannelsLabel = QtWidgets.QLabel(self)
        self.matrixChannelsLabel.setText("Channels")

        self.matrixChannelsEdit = MatrixChannelsEdit(self)
        self.matrixChannelsEdit.setToolTip("Matrix card switching channels, comma separated list.")

        # Matrix group box

        self.matrixGroupBox = QtWidgets.QGroupBox(self)
        self.matrixGroupBox.setTitle("Matrix")

        matrixgroupBoxLayout = QtWidgets.QVBoxLayout(self.matrixGroupBox)
        matrixgroupBoxLayout.addWidget(self.matrixEnableCheckBox)
        matrixgroupBoxLayout.addWidget(self.matrixChannelsLabel)
        matrixgroupBoxLayout.addWidget(self.matrixChannelsEdit)

        # Layout

        self.matrixWidget = QtWidgets.QWidget(self)

        matrixWidgetLayout = QtWidgets.QVBoxLayout(self.matrixWidget)
        matrixWidgetLayout.addWidget(self.matrixGroupBox)
        matrixWidgetLayout.addStretch()

        self.controlTabWidget.addTab(self.matrixWidget, "Matrix")

        # Bindings

        self.registerBindType(
            MatrixChannelsEdit,
            lambda widget: widget.channels(),
            lambda widget, value: widget.setChannels(value),
        )

        self.bind("matrix_enable", self.matrixEnableCheckBox, True)
        self.bind("matrix_channels", self.matrixChannelsEdit, [])

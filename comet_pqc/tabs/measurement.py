from typing import List

from PyQt5 import QtCore, QtWidgets

from ..panels import (
    ContactPanel,
    CVRampAltPanel,
    CVRampHVPanel,
    CVRampPanel,
    FrequencyScanPanel,
    IVRamp4WirePanel,
    IVRampBiasElmPanel,
    IVRampBiasPanel,
    IVRampElmPanel,
    IVRampPanel,
    SamplePanel,
)

__all__ = ["MeasurementWidget"]


class MeasurementWidget(QtWidgets.QWidget):

    restore = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.panels = PanelStack(self)

        self.restoreButton = QtWidgets.QPushButton(self)
        self.restoreButton.setText("Restore Defaults")
        self.restoreButton.setToolTip("Restore default measurement parameters.")
        self.restoreButton.clicked.connect(self.restore.emit)

        self.controlsLayout = QtWidgets.QWidget(self)
        self.controlsLayout.setVisible(False)

        controlsLayout = QtWidgets.QHBoxLayout(self.controlsLayout)
        controlsLayout.addWidget(self.restoreButton)
        controlsLayout.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.panels)
        layout.addWidget(self.controlsLayout)
        layout.setContentsMargins(0, 0, 0, 0)

    def setLocked(self, state: bool) -> None:
        self.panels.setLocked(state)
        self.controlsLayout.setEnabled(not state)

class PanelStack(QtWidgets.QWidget):
    """Stack of measurement panels."""

    sampleChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.panelWidgets: List = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.addPanel(SamplePanel(visible=False, sample_changed=self.sampleChanged.emit))
        self.addPanel(ContactPanel(visible=False))
        self.addPanel(IVRampPanel(visible=False))
        self.addPanel(IVRampElmPanel(visible=False))
        self.addPanel(IVRampBiasPanel(visible=False))
        self.addPanel(IVRampBiasElmPanel(visible=False))
        self.addPanel(CVRampPanel(visible=False))
        self.addPanel(CVRampHVPanel(visible=False))
        self.addPanel(CVRampAltPanel(visible=False))
        self.addPanel(IVRamp4WirePanel(visible=False))
        self.addPanel(FrequencyScanPanel(visible=False))

    def addPanel(self, panel):
        self.panelWidgets.append(panel)
        self.layout().addWidget(panel.qt)

    def store(self):
        for child in self.panelWidgets:
            child.store()

    def unmount(self):
        for child in self.panelWidgets:
            child.unmount()

    def clear_readings(self):
        for child in self.panelWidgets:
            child.clear_readings()

    def hide(self):
        for child in self.panelWidgets:
            child.visible = False

    def setLocked(self, state: bool) -> None:
        for child in self.panelWidgets:
            child.lock() if state else child.unlock()

    def get(self, type):
        """Get panel by type."""
        for child in self.panelWidgets:
            if child.type == type:
                return child
        return None

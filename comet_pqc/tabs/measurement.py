from typing import List, Optional

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
    BasicPanel,
)

__all__ = ["MeasurementWidget"]


class MeasurementWidget(QtWidgets.QWidget):

    restore: QtCore.pyqtSignal = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.panels: PanelStack = PanelStack(self)

        self.restoreButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.restoreButton.setText("Restore Defaults")
        self.restoreButton.setToolTip("Restore default measurement parameters.")
        self.restoreButton.clicked.connect(self.restore.emit)

        self.controlsLayout: QtWidgets.QWidget = QtWidgets.QWidget(self)
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

    sampleChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.panelWidgets: List[BasicPanel] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.samplePanel = SamplePanel(self)
        self.samplePanel.sampleChanged.connect(self.sampleChanged.emit)
        self.addPanel(self.samplePanel)

        self.addPanel(ContactPanel(self))
        self.addPanel(IVRampPanel(self))
        self.addPanel(IVRampElmPanel(self))
        self.addPanel(IVRampBiasPanel(self))
        self.addPanel(IVRampBiasElmPanel(self))
        self.addPanel(CVRampPanel(self))
        self.addPanel(CVRampHVPanel(self))
        self.addPanel(CVRampAltPanel(self))
        self.addPanel(IVRamp4WirePanel(self))
        self.addPanel(FrequencyScanPanel(self))

        self.hide()

    def addPanel(self, panel: BasicPanel) ->  None:
        self.panelWidgets.append(panel)
        self.layout().addWidget(panel)

    def store(self) -> None:
        for child in self.panelWidgets:
            child.store()

    def unmount(self) -> None:
        for child in self.panelWidgets:
            child.unmount()

    def clearReadings(self) -> None:
        for child in self.panelWidgets:
            child.clearReadings()

    def hide(self) -> None:
        for child in self.panelWidgets:
            child.setVisible(False)

    def setLocked(self, state: bool) -> None:
        for child in self.panelWidgets:
            child.lock() if state else child.unlock()

    def get(self, type) -> Optional[BasicPanel]:
        """Get panel by type."""
        for child in self.panelWidgets:
            if child.type == type:
                return child
        return None

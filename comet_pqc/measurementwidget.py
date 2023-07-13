from typing import Optional

from PyQt5 import QtCore, QtWidgets

from .panels import (
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

    restoreDefaults = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.panels = PanelStack(self)

        self.restoreDefaultsButton = QtWidgets.QPushButton(self)
        self.restoreDefaultsButton.setText("Restore Defaults")
        self.restoreDefaultsButton.setToolTip("Restore default measurement parameters.")
        self.restoreDefaultsButton.clicked.connect(self.restoreDefaults.emit)

        self.controlsWidget = QtWidgets.QWidget(self)
        self.controlsWidget.setVisible(False)

        self.controlsLayout = QtWidgets.QHBoxLayout(self.controlsWidget)
        self.controlsLayout.addWidget(self.restoreDefaultsButton)
        self.controlsLayout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panels, 1)
        layout.addWidget(self.controlsWidget, 0)

    def setControlsVisible(self, state: bool) -> None:
        self.controlsWidget.setVisible(state)

    def setLocked(self, state: bool) -> None:
        self.panels.setLocked(state)
        self.controlsWidget.setEnabled(not state)


class PanelStack(QtWidgets.QWidget):
    """Stack of measurement panels."""

    sampleChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.panels = []

        samplePanel = SamplePanel()
        samplePanel.sampleChanged.connect(self.sampleChanged.emit)

        self.addPanel(samplePanel)
        self.addPanel(ContactPanel())
        self.addPanel(IVRampPanel())
        self.addPanel(IVRampElmPanel())
        self.addPanel(IVRampBiasPanel())
        self.addPanel(IVRampBiasElmPanel())
        self.addPanel(CVRampPanel())
        self.addPanel(CVRampHVPanel())
        self.addPanel(CVRampAltPanel())
        self.addPanel(IVRamp4WirePanel())
        self.addPanel(FrequencyScanPanel())

        self.hide()

    def addPanel(self, panel) -> None:
        self.panels.append(panel)
        self.layout().addWidget(panel)

    def store(self):
        for child in self.panels:
            child.store()

    def unmount(self):
        for child in self.panels:
            child.unmount()

    def clear(self) -> None:
        for child in self.panels:
            child.clear_readings()

    def hide(self):
        for child in self.panels:
            child.setVisible(False)

    def setLocked(self, locked: bool) -> None:
        for child in self.panels:
            child.setLocked(locked)

    def get(self, type):
        """Get panel by type."""
        for child in self.panels:
            if child.type == type:
                return child
        return None

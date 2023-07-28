from typing import Optional

from PyQt5 import QtCore, QtWidgets

from .panels import (
    ContactPanel,
    CVRampAltPanel,
    CVRampHVPanel,
    CVRampPanel,
    FrequencyScanPanel,
    IVRamp4WirePanel,
    IVRamp4WireBiasPanel,
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

        self.panels: Dict[str, QtWidgets.QWidget] = {}

        samplePanel = SamplePanel()
        samplePanel.sampleChanged.connect(self.sampleChanged.emit)

        self.addPanel("sample", samplePanel)
        self.addPanel("contact", ContactPanel())
        self.addPanel("iv_ramp", IVRampPanel())
        self.addPanel("iv_ramp_elm", IVRampElmPanel())
        self.addPanel("iv_ramp_bias", IVRampBiasPanel())
        self.addPanel("iv_ramp_bias_elm", IVRampBiasElmPanel())
        self.addPanel("cv_ramp", CVRampPanel())
        self.addPanel("cv_ramp_vsrc", CVRampHVPanel())
        self.addPanel("cv_ramp_alt", CVRampAltPanel())
        self.addPanel("iv_ramp_4_wire", IVRamp4WirePanel())
        self.addPanel("iv_ramp_4_wire_bias", IVRamp4WireBiasPanel())
        self.addPanel("frequency_scan", FrequencyScanPanel())

    def addPanel(self, type: str, panel: QtWidgets.QWidget) -> None:
        self.panels.update({type: panel})
        self.layout().addWidget(panel)
        panel.setVisible(False)

    def store(self):
        for child in self.panels.values():
            child.store()

    def unmount(self):
        for child in self.panels.values():
            child.unmount()

    def clear(self) -> None:
        for child in self.panels.values():
            child.clear_readings()

    def hide(self):
        for child in self.panels.values():
            child.setVisible(False)

    def setLocked(self, locked: bool) -> None:
        for child in self.panels.values():
            child.setLocked(locked)

    def get(self, type: str) -> Optional[QtWidgets.QWidget]:
        """Get panel by type name."""
        return self.panels.get(type)

from typing import Dict, List, Optional

from PyQt5 import QtCore, QtWidgets

from .panels import (ContactPanel, CVRampAltPanel, CVRampHVPanel, CVRampPanel,
                     FrequencyScanPanel, IVRamp4WirePanel, IVRampBiasElmPanel,
                     IVRampBiasPanel, IVRampElmPanel, IVRampPanel, SamplePanel, DebugPanel)
from .panels.panel import Panel

__all__ = ["MeasurementWidget"]


class MeasurementWidget(QtWidgets.QWidget):

    restoreClicked = QtCore.pyqtSignal()
    sampleChanged = QtCore.pyqtSignal(object)
    moveRequested = QtCore.pyqtSignal(object)
    contactRequested = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        samplePanel: SamplePanel = SamplePanel()
        samplePanel.sampleChanged.connect(self.sampleChanged.emit)

        contactPanel: ContactPanel = ContactPanel()
        contactPanel.moveRequested.connect(self.moveRequested.emit)
        contactPanel.contactRequested.connect(self.contactRequested.emit)

        self.panels: PanelStack = PanelStack(self)
        self.panels.addPanel("sample", samplePanel)
        self.panels.addPanel("contact", contactPanel)
        self.panels.addPanel("iv_ramp", IVRampPanel())
        self.panels.addPanel("iv_ramp_elm", IVRampElmPanel())
        self.panels.addPanel("iv_ramp_bias", IVRampBiasPanel())
        self.panels.addPanel("iv_ramp_bias_elm", IVRampBiasElmPanel())
        self.panels.addPanel("cv_ramp", CVRampPanel())
        self.panels.addPanel("cv_ramp_vsrc", CVRampHVPanel())
        self.panels.addPanel("cv_ramp_alt", CVRampAltPanel())
        self.panels.addPanel("iv_ramp_4_wire", IVRamp4WirePanel())
        self.panels.addPanel("frequency_scan", FrequencyScanPanel())
        self.panels.addPanel("debug", DebugPanel())

        self.restoreButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.restoreButton.setText("Restore Defaults")
        self.restoreButton.setStatusTip("Restore default measurement parameters.")
        self.restoreButton.clicked.connect(self.restoreClicked.emit)

        self.controlsWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.controlsWidget.setVisible(False)

        controlsWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.controlsWidget)
        controlsWidgetLayout.addWidget(self.restoreButton)
        controlsWidgetLayout.addStretch()

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panels, 1)
        layout.addWidget(self.controlsWidget, 0)
        layout.addStretch()
        layout.addStretch()

    def setLocked(self, locked: bool) -> None:
        self.panels.setLocked(locked)
        self.controlsWidget.setEnabled(not locked)

    def setControlsVisible(self, visible: bool) -> None:
        self.controlsWidget.setVisible(visible)


class PanelStack(QtWidgets.QStackedWidget):
    """Stack of measurement panels."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._panels: Dict[str, Panel] = {}
        self.addWidget(QtWidgets.QWidget())  # empty page

    def addPanel(self, type: str, panel: Panel) -> None:
        self._panels[type] = panel
        self.addWidget(panel)

    def panels(self) -> List[Panel]:
        return list(self._panels.values())

    def findPanel(self, type: str) -> Optional[Panel]:
        return self._panels.get(type)

    def store(self) -> None:
        for panel in self.panels():
            panel.store()

    def unmount(self) -> None:
        for panel in self.panels():
            panel.unmount()

    def clearReadings(self) -> None:
        for panel in self.panels():
            panel.clearReadings()

    def setLocked(self, locked: bool) -> None:
        for panel in self.panels():
            panel.setLocked(locked)

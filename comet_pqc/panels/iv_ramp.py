from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from comet_pqc.components import Metric
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin

__all__ = ["IVRampPanel"]


class IVRampPanel(MatrixPanel, HVSourceMixin, EnvironmentMixin):
    """Panel for IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("IV Ramp")

        self.register_hvsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("hvsrc", "x", "y", text="HV Source", color="red")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.dataTabWidget.insertTab(0, self.plot.qt, "IV Curve")

        self.voltage_start = QtWidgets.QDoubleSpinBox(self)
        self.voltage_start.setDecimals(3)
        self.voltage_start.setRange(-2200, +2200)
        self.voltage_start.setSuffix(" V")

        self.voltage_stop = QtWidgets.QDoubleSpinBox(self)
        self.voltage_stop.setDecimals(3)
        self.voltage_stop.setRange(-2200, +2200)
        self.voltage_stop.setSuffix(" V")

        self.voltage_step = QtWidgets.QDoubleSpinBox(self)
        self.voltage_step.setDecimals(3)
        self.voltage_step.setRange(0, 200)
        self.voltage_step.setSuffix(" V")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.hvsrcCurrentComplianceSpinBox = Metric(self)
        self.hvsrcCurrentComplianceSpinBox.setUnit("A")
        self.hvsrcCurrentComplianceSpinBox.setPrefixes("mun")
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, float("inf"))

        self.hvsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")

        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout = QtWidgets.QVBoxLayout(rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start"))
        rampGroupBoxLayout.addWidget(self.voltage_start)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop"))
        rampGroupBoxLayout.addWidget(self.voltage_stop)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step"))
        rampGroupBoxLayout.addWidget(self.voltage_step)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time"))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        hvsrcGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvsrcGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(hvsrcGroupBox, 1)
        layout.addStretch(1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["hvsrc"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("hvsrc")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series.get(name).append(*tr(x, y))
        self.updateReadings()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plot.series.get(name).append(*tr(x, y))
                self.plot.series.get(name).qt.setVisible(True)

    def updateReadings(self) -> None:
        super().updateReadings()
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.fit()

    def clearReadings(self) -> None:
        super().clearReadings()
        self.plot.series.get("xfit").qt.setVisible(False)
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from comet_pqc.components import Metric
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, VSourceMixin

__all__ = ["IVRamp4WireBiasPanel"]


class IVRamp4WireBiasPanel(MatrixPanel, HVSourceMixin, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp with bias measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("4 Wire IV Ramp Bias")

        self.register_hvsource()
        self.register_vsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="blue")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.dataTabWidget.insertTab(0, self.plot.qt, "IV Curve")

        self.current_start = QtWidgets.QDoubleSpinBox(self)
        self.current_start.setDecimals(3)
        self.current_start.setRange(float("-inf"), float("+inf"))
        self.current_start.setSuffix(" uA")

        self.current_stop = QtWidgets.QDoubleSpinBox(self)
        self.current_stop.setDecimals(3)
        self.current_stop.setRange(float("-inf"), float("+inf"))
        self.current_stop.setSuffix(" uA")

        self.current_step = QtWidgets.QDoubleSpinBox(self)
        self.current_step.setDecimals(3)
        self.current_step.setRange(0, float("inf"))
        self.current_step.setSuffix(" uA")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.bias_voltage = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage.setDecimals(3)
        self.bias_voltage.setRange(-2200, +2200)
        self.bias_voltage.setSuffix(" V")

        self.bias_voltage_step = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage_step.setDecimals(3)
        self.bias_voltage_step.setRange(-2200, +2200)
        self.bias_voltage_step.setSuffix(" V")

        self.hvsrcCurrentComplianceSpinBox = Metric(self)
        self.hvsrcCurrentComplianceSpinBox.setUnit("A")
        self.hvsrcCurrentComplianceSpinBox.setPrefixes("mun")
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, float("inf"))

        self.hvsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.vsrcVoltageComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcVoltageComplianceSpinBox.setDecimals(3)
        self.vsrcVoltageComplianceSpinBox.setRange(-2200, +2200)
        self.vsrcVoltageComplianceSpinBox.setSuffix(" V")

        self.vsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 10, unit="V")
        self.bind("bias_voltage_step", self.bias_voltage_step, 1, unit="V")

        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)
        self.bind("vsrc_voltage_compliance", self.vsrcVoltageComplianceSpinBox, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout = QtWidgets.QVBoxLayout(rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start"))
        rampGroupBoxLayout.addWidget(self.current_start)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop"))
        rampGroupBoxLayout.addWidget(self.current_stop)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step"))
        rampGroupBoxLayout.addWidget(self.current_step)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time"))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        hvsrcBiasGroupBox = QtWidgets.QGroupBox(self)
        hvsrcBiasGroupBox.setTitle("HV Source Bias")

        hvsrcBiasGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcBiasGroupBox)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        hvsrcBiasGroupBoxLayout.addWidget(self.bias_voltage)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage Step"))
        hvsrcBiasGroupBoxLayout.addWidget(self.bias_voltage_step)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance"))
        hvsrcBiasGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcBiasGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvsrcBiasGroupBoxLayout.addStretch()

        vsrcGroupBox = QtWidgets.QGroupBox(self)
        vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout = QtWidgets.QVBoxLayout(vsrcGroupBox)
        vsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        vsrcGroupBoxLayout.addWidget(self.vsrcVoltageComplianceSpinBox)
        vsrcGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vsrcGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(hvsrcBiasGroupBox, 1)
        layout.addWidget(vsrcGroupBox, 1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["vsrc"] = lambda x, y: ((x * ampere).to("uA").m, (y * volt).to("V").m)
        self.series_transform["xfit"] = self.series_transform.get("vsrc")

    def mount(self, measurement):
        super().mount(measurement)
        self.plot.series.get("xfit").qt.setVisible(False)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series.get(name).append(*tr(x, y))
            self.plot.series.get(name).qt.setVisible(True)
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
                self.plot.qt.chart().zoomOut() # HACK
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

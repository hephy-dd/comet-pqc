from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from ..components import Metric
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

        self.currentStartSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStartSpinBox.setDecimals(3)
        self.currentStartSpinBox.setRange(float("-inf"), float("+inf"))
        self.currentStartSpinBox.setSuffix(" uA")

        self.currentStopSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStopSpinBox.setDecimals(3)
        self.currentStopSpinBox.setRange(float("-inf"), float("+inf"))
        self.currentStopSpinBox.setSuffix(" uA")

        self.currentStepSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStepSpinBox.setDecimals(3)
        self.currentStepSpinBox.setRange(0, float("inf"))
        self.currentStepSpinBox.setSuffix(" uA")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.biasVoltageSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setRange(-2200, +2200)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.biasVoltageStepSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageStepSpinBox.setDecimals(3)
        self.biasVoltageStepSpinBox.setRange(-2200, +2200)
        self.biasVoltageStepSpinBox.setSuffix(" V")

        self.hvsrcCurrentComplianceMetric = Metric(self)
        self.hvsrcCurrentComplianceMetric.setUnit("A")
        self.hvsrcCurrentComplianceMetric.setPrefixes("mun")
        self.hvsrcCurrentComplianceMetric.setDecimals(3)
        self.hvsrcCurrentComplianceMetric.setRange(0, float("inf"))

        self.hvsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.vsrcVoltageComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcVoltageComplianceSpinBox.setDecimals(3)
        self.vsrcVoltageComplianceSpinBox.setRange(-2200, +2200)
        self.vsrcVoltageComplianceSpinBox.setSuffix(" V")

        self.vsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.bind("current_start", self.currentStartSpinBox, 0, unit="uA")
        self.bind("current_stop", self.currentStopSpinBox, 0, unit="uA")
        self.bind("current_step", self.currentStepSpinBox, 0, unit="uA")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("bias_voltage", self.biasVoltageSpinBox, 10, unit="V")
        self.bind("bias_voltage_step", self.biasVoltageStepSpinBox, 1, unit="V")

        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceMetric, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)
        self.bind("vsrc_voltage_compliance", self.vsrcVoltageComplianceSpinBox, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout = QtWidgets.QVBoxLayout(rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start"))
        rampGroupBoxLayout.addWidget(self.currentStartSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop"))
        rampGroupBoxLayout.addWidget(self.currentStopSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step"))
        rampGroupBoxLayout.addWidget(self.currentStepSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time"))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        hvsrcBiasGroupBox = QtWidgets.QGroupBox(self)
        hvsrcBiasGroupBox.setTitle("HV Source Bias")

        hvsrcBiasGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcBiasGroupBox)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        hvsrcBiasGroupBoxLayout.addWidget(self.biasVoltageSpinBox)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage Step"))
        hvsrcBiasGroupBoxLayout.addWidget(self.biasVoltageStepSpinBox)
        hvsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance"))
        hvsrcBiasGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceMetric)
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

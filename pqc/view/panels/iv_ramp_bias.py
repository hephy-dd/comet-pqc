from typing import Optional

from PyQt5 import QtWidgets

import comet

from ..components import PlotWidget
from ..components import Metric
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, VSourceMixin

__all__ = ["IVRampBiasPanel"]


class IVRampBiasPanel(MatrixPanel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("Bias + IV Ramp")

        HVSourceMixin(self)
        VSourceMixin(self)
        EnvironmentMixin(self)

        self.plotWidget = PlotWidget(self)
        self.plotWidget.addAxis("x", align="bottom", text="Voltage [V]")
        self.plotWidget.addAxis("y", align="right", text="Current [uA]")
        self.plotWidget.addSeries("vsrc", "x", "y", text="V Source", color="blue")
        self.plotWidget.addSeries("xfit", "x", "y", text="Fit", color="magenta")
        self.dataTabWidget.insertTab(0, self.plotWidget, "IV Curve")

        self.voltageStartSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStartSpinBox.setDecimals(3)
        self.voltageStartSpinBox.setRange(-2200, +2200)
        self.voltageStartSpinBox.setSuffix(" V")

        self.voltageStopSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStopSpinBox.setDecimals(3)
        self.voltageStopSpinBox.setRange(-2200, +2200)
        self.voltageStopSpinBox.setSuffix(" V")

        self.voltageStepSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStepSpinBox.setDecimals(3)
        self.voltageStepSpinBox.setRange(0, 200)
        self.voltageStepSpinBox.setSuffix(" V")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.biasVoltageSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setRange(-2200, +2200)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.bias_mode = QtWidgets.QComboBox(self)
        self.bias_mode.addItems(["constant", "offset"])

        self.hvsrcCurrentComplianceMetric = Metric(self)
        self.hvsrcCurrentComplianceMetric.setUnit("A")
        self.hvsrcCurrentComplianceMetric.setPrefixes("mun")
        self.hvsrcCurrentComplianceMetric.setDecimals(3)
        self.hvsrcCurrentComplianceMetric.setRange(0, float("inf"))

        self.hvsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.vsrcCurrentComplianceMetric = Metric(self)
        self.vsrcCurrentComplianceMetric.setUnit("A")
        self.vsrcCurrentComplianceMetric.setPrefixes("mun")
        self.vsrcCurrentComplianceMetric.setDecimals(3)
        self.vsrcCurrentComplianceMetric.setRange(0, float("inf"))

        self.vsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.bind("voltage_start", self.voltageStartSpinBox, 0, unit="V")
        self.bind("voltage_stop", self.voltageStopSpinBox, 0, unit="V")
        self.bind("voltage_step", self.voltageStepSpinBox, 0, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("bias_voltage", self.biasVoltageSpinBox, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceMetric, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)
        self.bind("vsrc_current_compliance", self.vsrcCurrentComplianceMetric, 0, unit="A")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("HV Source Ramp")

        rampGroupBoxLayout = QtWidgets.QVBoxLayout(rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start"))
        rampGroupBoxLayout.addWidget(self.voltageStartSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop"))
        rampGroupBoxLayout.addWidget(self.voltageStopSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step"))
        rampGroupBoxLayout.addWidget(self.voltageStepSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time"))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        vsrcBiasGroupBox = QtWidgets.QGroupBox(self)
        vsrcBiasGroupBox.setTitle("V Source Bias")

        vsrcBiasGroupBoxLayout = QtWidgets.QVBoxLayout(vsrcBiasGroupBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        vsrcBiasGroupBoxLayout.addWidget(self.biasVoltageSpinBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance"))
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcCurrentComplianceMetric)
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Mode"))
        vsrcBiasGroupBoxLayout.addWidget(self.bias_mode)
        vsrcBiasGroupBoxLayout.addStretch()

        hvsrcGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceMetric)
        hvsrcGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvsrcGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(vsrcBiasGroupBox, 1)
        layout.addWidget(hvsrcGroupBox, 1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["vsrc"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("vsrc")

    def mount(self, measurement):
        super().mount(measurement)
        self.plotWidget.clear()
        for name, points in measurement.series.items():
            if name in self.plotWidget.series():
                tr = self.series_transform.get(name, self.series_transform_default)
                if points[0][0] > points[-1][0]:
                    self.plotWidget.axes().get("x").qt.setReverse(True)
                else:
                    self.plotWidget.axes().get("x").qt.setReverse(False)
                for x, y in points:
                    self.plotWidget.series().get(name).append(*tr(x, y))
        self.updateReadings()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            if name in self.plotWidget.series():
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                if self.voltageStartSpinBox.value() > self.voltageStopSpinBox.value():
                    self.plotWidget.axes().get("x").qt.setReverse(True)
                else:
                    self.plotWidget.axes().get("x").qt.setReverse(False)
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plotWidget.series().get(name).append(*tr(x, y))
                self.plotWidget.series().get(name).qt.setVisible(True)

    def updateReadings(self) -> None:
        super().updateReadings()
        if self.measurement:
            self.plotWidget.smartFit()

    def clearReadings(self) -> None:
        super().clearReadings()
        self.plotWidget.series().get("xfit").qt.setVisible(False)
        self.plotWidget.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plotWidget.fit()

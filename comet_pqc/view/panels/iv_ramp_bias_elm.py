from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from .matrix import MatrixPanel
from .mixins import (
    ElectrometerMixin,
    EnvironmentMixin,
    HVSourceMixin,
    VSourceMixin,
)

__all__ = ["IVRampBiasElmPanel"]


class IVRampBiasElmPanel(MatrixPanel, HVSourceMixin, VSourceMixin, ElectrometerMixin, EnvironmentMixin):
    """Panel for bias IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("IV Ramp Bias Elm")

        self.register_hvsource()
        self.register_vsource()
        self.register_electrometer()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
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

        self.bias_voltage = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage.setDecimals(3)
        self.bias_voltage.setRange(-2200, +2200)
        self.bias_voltage.setSuffix(" V")

        self.bias_mode = QtWidgets.QComboBox(self)
        self.bias_mode.addItems(["constant", "offset"])

        self.hvsrcCurrentComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setRange(float("-inf"), float("inf"))
        self.hvsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.hvsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.vsrcCurrentComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcCurrentComplianceSpinBox.setDecimals(3)
        self.vsrcCurrentComplianceSpinBox.setRange(float("-inf"), float("inf"))
        self.vsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.vsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)
        self.bind("vsrc_current_compliance", self.vsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("HV Source Ramp")

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

        vsrcBiasGroupBox = QtWidgets.QGroupBox(self)
        vsrcBiasGroupBox.setTitle("V Source Bias")

        vsrcBiasGroupBoxLayout = QtWidgets.QVBoxLayout(vsrcBiasGroupBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        vsrcBiasGroupBoxLayout.addWidget(self.bias_voltage)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance"))
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcCurrentComplianceSpinBox)
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Mode"))
        vsrcBiasGroupBoxLayout.addWidget(self.bias_mode)
        vsrcBiasGroupBoxLayout.addStretch()

        hvsrcGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvsrcGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(vsrcBiasGroupBox, 1)
        layout.addWidget(hvsrcGroupBox, 1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["elm"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("elm")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                if name in self.plot.series:
                    self.plot.series.clear()
                tr = self.series_transform.get(name, self.series_transform_default)
                if points[0][0] > points[-1][0]:
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
                for x, y in points:
                    self.plot.series.get(name).append(*tr(x, y))
        self.updateReadings()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                if self.voltage_start.value() > self.voltage_stop.value():
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
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

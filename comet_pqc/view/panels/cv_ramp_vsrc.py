from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, LCRMixin, VSourceMixin

__all__ = ["CVRampHVPanel"]


class CVRampHVPanel(MatrixPanel, VSourceMixin, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("CV Ramp (V Source)")

        self.register_vsource()
        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(0, self.plot.qt, "CV Curve")

        self.plot2 = ui.Plot(height=300, legend="right")
        self.plot2.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot2.add_axis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plot2.axes.get("y").qt.setLabelFormat("%G")
        self.plot2.add_series("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(1, self.plot2.qt, "1/C² Curve")

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

        self.vsrcCurrentComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcCurrentComplianceSpinBox.setDecimals(3)
        self.vsrcCurrentComplianceSpinBox.setRange(0, float("inf"))
        self.vsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.vsrcAcceptComplianceCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.lcrFrequencySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrFrequencySpinBox.setDecimals(3)
        self.lcrFrequencySpinBox.setRange(0.020, 20e3)
        self.lcrFrequencySpinBox.setSuffix(" kHz")
        self.lcrFrequencySpinBox.setValue(1)

        self.lcrAmplitudeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setRange(0, float("inf"))
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("vsrc_current_compliance", self.vsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)
        self.bind("lcr_frequency", self.lcrFrequencySpinBox, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 250, unit="mV")

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("V Source Ramp")

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

        vSourceGroupBox = QtWidgets.QGroupBox(self)
        vSourceGroupBox.setTitle("V Source")

        vSourceGroupBoxLayout = QtWidgets.QVBoxLayout(vSourceGroupBox)
        vSourceGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        vSourceGroupBoxLayout.addWidget(self.vsrcCurrentComplianceSpinBox)
        vSourceGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vSourceGroupBoxLayout.addStretch()

        lcrGroupBox = QtWidgets.QGroupBox(self)
        lcrGroupBox.setTitle("LCR")

        lcrGroupBoxLayout = QtWidgets.QVBoxLayout(lcrGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency"))
        lcrGroupBoxLayout.addWidget(self.lcrFrequencySpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude"))
        lcrGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(vSourceGroupBox, 1)
        layout.addWidget(lcrGroupBox, 1)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)

    def mount(self, measurement):
        super().mount(measurement)
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        for name, points in measurement.series.items():
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                for x, y in points:
                    self.plot.series.get(name).append(*tr(x, y))
            elif name == "lcr2":
                for x, y in points:
                    self.plot2.series.get(name).append(*tr(x, y))
        self.plot.fit()
        self.plot2.fit()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series.get(name).append(*tr(x, y))
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
            elif name == "lcr2":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot2.series.get(name).append(*tr(x, y))
                if self.plot2.zoomed:
                    self.plot2.update("x")
                else:
                    self.plot2.fit()

    def clearReadings(self) -> None:
        super().clearReadings()
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

from typing import Optional

from PyQt5 import QtWidgets

import comet

from ..components import PlotWidget
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, LCRMixin

__all__ = ["CVRampAltPanel"]


class CVRampAltPanel(MatrixPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("CV Ramp (LCR)")

        LCRMixin(self)
        EnvironmentMixin(self)

        self.plotWidget = PlotWidget(self)
        self.plotWidget.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plotWidget.addAxis("y", align="right", text="Capacitance [pF]")
        self.lcrSeries = self.plotWidget.addSeries("lcr", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(0, self.plotWidget, "CV Curve")

        self.plotWidget2 = PlotWidget(self)
        self.plotWidget2.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plotWidget2.addAxis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plotWidget2.axes().get("y").qt.setLabelFormat("%G")
        self.lcr2Series = self.plotWidget2.addSeries("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(1, self.plotWidget2, "1/C² Curve")

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

        self.lcrFrequencySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrFrequencySpinBox.setDecimals(3)
        self.lcrFrequencySpinBox.setRange(0.020, 20e3)
        self.lcrFrequencySpinBox.setSuffix(" kHz")
        self.lcrFrequencySpinBox.setValue(1)

        self.lcrAmplitudeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setRange(0, float("inf"))
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.bind("bias_voltage_start", self.voltageStartSpinBox, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltageStopSpinBox, 0, unit="V")
        self.bind("bias_voltage_step", self.voltageStepSpinBox, 0, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("lcr_frequency", self.lcrFrequencySpinBox, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 250, unit="mV")

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("LCR Ramp")

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

        lcrFreqGroupBox = QtWidgets.QGroupBox(self)
        lcrFreqGroupBox.setTitle("LCR Freq.")

        lcrFreqGroupBoxLayout = QtWidgets.QVBoxLayout(lcrFreqGroupBox)
        lcrFreqGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency"))
        lcrFreqGroupBoxLayout.addWidget(self.lcrFrequencySpinBox)
        lcrFreqGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude"))
        lcrFreqGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrFreqGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(lcrFreqGroupBox, 1)
        layout.addStretch(1)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)

    def mount(self, measurement):
        super().mount(measurement)
        self.plotWidget.clear()
        self.plotWidget2.clear()
        for name, points in measurement.series.items():
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                for x, y in points:
                    self.lcrSeries.append(*tr(x, y))
            elif name == "lcr2":
                for x, y in points:
                    self.lcr2Series.append(*tr(x, y))
        self.plotWidget.fit()
        self.plotWidget2.fit()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.lcrSeries.append(*tr(x, y))
                self.plotWidget.smartFit()
            elif name == "lcr2":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.lcr2Series.append(*tr(x, y))
                self.plotWidget2.smartFit()

    def clearReadings(self) -> None:
        super().clearReadings()
        self.plotWidget.clear()
        self.plotWidget2.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plotWidget.fit()

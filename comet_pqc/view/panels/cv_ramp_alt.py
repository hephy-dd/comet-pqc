from typing import Optional

import comet
from PyQt5 import QtWidgets

from ..plotwidget import PlotWidget
from .mixins import EnvironmentMixin, LCRMixin, MatrixMixin
from .panel import MeasurementPanel

__all__ = ["CVRampAltPanel"]


class CVRampAltPanel(MeasurementPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "CV Ramp (LCR)"

        self.plot = PlotWidget(self)
        self.plot.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.addAxis("y", align="right", text="Capacitance [pF]")
        self.plot.addSeries("lcr", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(0, self.plot, "CV Curve")

        self.plot2 =  PlotWidget(self)
        self.plot2.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot2.addAxis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plot2.axes().get("y").qt.setLabelFormat("%G")  # type: ignore
        self.plot2.addSeries("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.dataTabWidget.insertTab(1, self.plot2, "1/C² Curve")

        self.voltageStartSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStartSpinBox.setRange(-2200, +2200)
        self.voltageStartSpinBox.setDecimals(3)
        self.voltageStartSpinBox.setSuffix(" V")

        self.voltageStopSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStopSpinBox.setRange(-2200, +2200)
        self.voltageStopSpinBox.setDecimals(3)
        self.voltageStopSpinBox.setSuffix(" V")

        self.voltageStepSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStepSpinBox.setRange(0, 200)
        self.voltageStepSpinBox.setDecimals(3)
        self.voltageStepSpinBox.setSuffix(" V")

        self.waitingTimeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.lcrFrequencySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrFrequencySpinBox.setRange(20e-3, 2e3)
        self.lcrFrequencySpinBox.setValue(1)
        self.lcrFrequencySpinBox.setDecimals(3)
        self.lcrFrequencySpinBox.setSuffix(" kHz")

        self.lcrAmplitudeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setRange(0, 20e3)
        self.lcrAmplitudeSpinBox.setValue(1)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.lcrRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrRampGroupBox.setTitle("LCR Ramp")

        lcrRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.lcrRampGroupBox)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        lcrRampGroupBoxLayout.addWidget(self.voltageStartSpinBox)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        lcrRampGroupBoxLayout.addWidget(self.voltageStopSpinBox)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        lcrRampGroupBoxLayout.addWidget(self.voltageStepSpinBox)
        lcrRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        lcrRampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        lcrRampGroupBoxLayout.addStretch()

        self.lcrFreqGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrFreqGroupBox.setTitle("LCR Freq.")

        lcrFreqGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.lcrFreqGroupBox)
        lcrFreqGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency", self))
        lcrFreqGroupBoxLayout.addWidget(self.lcrFrequencySpinBox)
        lcrFreqGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        lcrFreqGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrFreqGroupBoxLayout.addStretch()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)
        generalWidgetLayout.addWidget(self.lcrRampGroupBox)
        generalWidgetLayout.addWidget(self.lcrFreqGroupBox)
        generalWidgetLayout.addStretch()
        generalWidgetLayout.setStretch(0, 1)
        generalWidgetLayout.setStretch(1, 1)
        generalWidgetLayout.setStretch(2, 1)

        self.controlTabWidget.insertTab(0, self.generalWidget, "General")
        self.controlTabWidget.setCurrentWidget(self.generalWidget)

        MatrixMixin(self)
        LCRMixin(self)
        EnvironmentMixin(self)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)

        # Bindings

        self.bind("bias_voltage_start", self.voltageStartSpinBox, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltageStopSpinBox, 0, unit="V")
        self.bind("bias_voltage_step", self.voltageStepSpinBox, 0, unit="V")
        self.bind("waitingTimeSpinBox", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("lcr_frequency", self.lcrFrequencySpinBox, 1, unit="kHz")
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 0, unit="mV")

    def mount(self, measurement):
        super().mount(measurement)
        for series in self.plot.series().values():
            series.clear()
        for series in self.plot2.series().values():
            series.clear()
        for name, points in measurement.series.items():
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                for x, y in points:
                    self.plot.series().get(name).append(*tr(x, y))
            elif name == "lcr2":
                for x, y in points:
                    self.plot2.series().get(name).append(*tr(x, y))
        self.plot.fit()
        self.plot2.fit()

    def append_reading(self, name, x, y):
        if self.measurement:
            tr = self.series_transform.get(name, self.series_transform_default)
            if name == "lcr":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series().get(name).append(*tr(x, y))
                if self.plot.isZoomed():
                    self.plot.update("x")
                else:
                    self.plot.fit()
            elif name == "lcr2":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot2.series().get(name).append(*tr(x, y))
                if self.plot2.isZoomed():
                    self.plot2.update("x")
                else:
                    self.plot2.fit()

    def clearReadings(self):
        super().clearReadings()
        for series in self.plot.series().values():
            series.clear()
        for series in self.plot2.series().values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

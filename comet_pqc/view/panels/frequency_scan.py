from typing import Optional

import comet
from PyQt5 import QtWidgets

from ..plotwidget import PlotWidget
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin, MatrixMixin
from .panel import MeasurementPanel

__all__ = ["FrequencyScanPanel"]


class FrequencyScanPanel(MeasurementPanel):
    """Frequency scan with log10 steps."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "Frequency Scan"

        self.plot = PlotWidget(self)
        self.plot.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.addAxis("y", align="right", text="Capacitance [pF]")
        self.plot.addSeries("lcr", "x", "y", text="LCR", color="blue")
        self.dataTabWidget.insertTab(0, self.plot, "CV Curve")

        self.biasVoltageSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageSpinBox.setRange(-2200, +2200)
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.hvsrcCurrentComplianceSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, 2e6)
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.frequencyStartSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.frequencyStartSpinBox.setRange(0, 20e3)
        self.frequencyStartSpinBox.setDecimals(3)
        self.frequencyStartSpinBox.setSuffix(" Hz")

        self.frequencyStopSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.frequencyStopSpinBox.setRange(0, 20e0)
        self.frequencyStopSpinBox.setDecimals(3)
        self.frequencyStopSpinBox.setSuffix(" MHz")

        self.frequencyStepsSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.frequencyStepsSpinBox.setRange(1, 1_000)

        self.lcrAmplitudeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setRange(0, 20e3)
        self.lcrAmplitudeSpinBox.setValue(1)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage", self))
        hvsrcGroupBoxLayout.addWidget(self.biasVoltageSpinBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addStretch()

        self.lcrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("LCR")

        lcrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Start", self))
        lcrGroupBoxLayout.addWidget(self.frequencyStartSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Stop", self))
        lcrGroupBoxLayout.addWidget(self.frequencyStopSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Steps (log10)", self))
        lcrGroupBoxLayout.addWidget(self.frequencyStepsSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        lcrGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrGroupBoxLayout.addStretch()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)
        generalWidgetLayout.addWidget(self.hvsrcGroupBox)
        generalWidgetLayout.addWidget(self.lcrGroupBox)
        generalWidgetLayout.addStretch()
        generalWidgetLayout.setStretch(0, 1)
        generalWidgetLayout.setStretch(1, 1)
        generalWidgetLayout.setStretch(2, 1)

        self.controlTabWidget.addTab(self.generalWidget, "General")

        MatrixMixin(self)
        HVSourceMixin(self)
        LCRMixin(self)
        EnvironmentMixin(self)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)
        self.series_transform["xfit"] = self.series_transform["lcr"]

        # Bindings

        self.bind("bias_voltage", self.biasVoltageSpinBox, 0, unit="V")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("lcr_frequency_start", self.frequencyStartSpinBox, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.frequencyStopSpinBox, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.frequencyStepsSpinBox, 1)
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 0, unit="mV")

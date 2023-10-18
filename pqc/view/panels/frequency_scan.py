from typing import Optional

from PyQt5 import QtWidgets

import comet

from ..components import PlotWidget
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["FrequencyScanPanel"]


class FrequencyScanPanel(MatrixPanel):
    """Frequency scan with log10 steps."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("Frequency Scan")

        HVSourceMixin(self)
        LCRMixin(self)
        EnvironmentMixin(self)

        self.plotWidget = PlotWidget(self)
        self.plotWidget.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plotWidget.addAxis("y", align="right", text="Capacitance [pF]")
        self.plotWidget.addSeries("lcr", "x", "y", text="LCR", color="blue")
        self.dataTabWidget.insertTab(0, self.plotWidget, "CV Curve")

        self.biasVoltageSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setRange(-2200, +2200)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.hvsrcCurrentComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, float("inf"))
        self.hvsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.lcFrequencyStartSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcFrequencyStartSpinBox.setDecimals(3)
        self.lcFrequencyStartSpinBox.setRange(0, float("inf"))
        self.lcFrequencyStartSpinBox.setSuffix(" Hz")

        self.lcFrequencyStopSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcFrequencyStopSpinBox.setDecimals(3)
        self.lcFrequencyStopSpinBox.setRange(0, float("inf"))
        self.lcFrequencyStopSpinBox.setSuffix(" MHz")

        self.lcFrequencyStepsSpinBox = QtWidgets.QSpinBox(self)
        self.lcFrequencyStepsSpinBox.setRange(1, 1000)

        self.lcrAmplitudeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setRange(0, float("inf"))
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.bind("bias_voltage", self.biasVoltageSpinBox, 0, unit="V")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("lcr_frequency_start", self.lcFrequencyStartSpinBox, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcFrequencyStopSpinBox, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcFrequencyStepsSpinBox, 1)
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 0, unit="mV")

        hvsrcGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        hvsrcGroupBoxLayout.addWidget(self.biasVoltageSpinBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Compliance"))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addStretch()

        lcrGroupBox = QtWidgets.QGroupBox(self)
        lcrGroupBox.setTitle("LCR")

        lcrGroupBoxLayout = QtWidgets.QVBoxLayout(lcrGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Start"))
        lcrGroupBoxLayout.addWidget(self.lcFrequencyStartSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Stop"))
        lcrGroupBoxLayout.addWidget(self.lcFrequencyStopSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Steps (log10)"))
        lcrGroupBoxLayout.addWidget(self.lcFrequencyStepsSpinBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude"))
        lcrGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(hvsrcGroupBox, 1)  # type: ignore
        layout.addWidget(lcrGroupBox, 1)  # type: ignore
        layout.addStretch(1)  # type: ignore

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)
        self.series_transform["xfit"] = self.series_transform.get("lcr")

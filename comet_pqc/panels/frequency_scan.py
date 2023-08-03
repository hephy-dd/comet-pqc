from typing import Optional

from PyQt5 import QtWidgets

import comet
from comet import ui

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["FrequencyScanPanel"]


class FrequencyScanPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Frequency scan with log10 steps."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("Frequency Scan")

        self.register_hvsource()
        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.dataTabWidget.insertTab(0, self.plot.qt, "CV Curve")

        self.bias_voltage = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage.setDecimals(3)
        self.bias_voltage.setRange(-2200, +2200)
        self.bias_voltage.setSuffix(" V")

        self.hvsrcCurrentComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, float("inf"))
        self.hvsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.lcr_frequency_start = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency_start.setDecimals(3)
        self.lcr_frequency_start.setRange(0, float("inf"))
        self.lcr_frequency_start.setSuffix(" Hz")

        self.lcr_frequency_stop = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency_stop.setDecimals(3)
        self.lcr_frequency_stop.setRange(0, float("inf"))
        self.lcr_frequency_stop.setSuffix(" MHz")

        self.lcr_frequency_steps = QtWidgets.QSpinBox(self)
        self.lcr_frequency_steps.setRange(1, 1000)

        self.lcrAmplitudeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrAmplitudeSpinBox.setDecimals(3)
        self.lcrAmplitudeSpinBox.setRange(0, float("inf"))
        self.lcrAmplitudeSpinBox.setSuffix(" mV")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcrAmplitudeSpinBox, 0, unit="mV")

        hvsrcGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage"))
        hvsrcGroupBoxLayout.addWidget(self.bias_voltage)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Compliance"))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addStretch()

        lcrGroupBox = QtWidgets.QGroupBox(self)
        lcrGroupBox.setTitle("LCR")

        lcrGroupBoxLayout = QtWidgets.QVBoxLayout(lcrGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Start"))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_start)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Stop"))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_stop)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Steps (log10)"))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_steps)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude"))
        lcrGroupBoxLayout.addWidget(self.lcrAmplitudeSpinBox)
        lcrGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(hvsrcGroupBox, 1)
        layout.addWidget(lcrGroupBox, 1)
        layout.addStretch(1)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)
        self.series_transform["xfit"] = self.series_transform.get("lcr")

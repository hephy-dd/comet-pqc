from typing import Optional

from comet import ui, ureg
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["FrequencyScanPanel"]


class FrequencyScanPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Frequency scan with log10 steps."""

    type_name = "frequency_scan"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Frequency Scan")

        self.register_hvsource()
        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.plot.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(0, self.plot.qt, "CV Curve")

        self.bias_voltage: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage.setRange(-2.1e3, +2.1e3)
        self.bias_voltage.setDecimals(3)
        self.bias_voltage.setSuffix(" V")

        self.hvsrc_current_compliance: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrc_current_compliance.setRange(0, 2.1e4)
        self.hvsrc_current_compliance.setDecimals(3)
        self.hvsrc_current_compliance.setSuffix(" uA")

        self.lcr_frequency_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency_start.setRange(0, 2.1e3)
        self.lcr_frequency_start.setDecimals(3)
        self.lcr_frequency_start.setSuffix(" Hz")

        self.lcr_frequency_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency_stop.setRange(0, 2.1e3)
        self.lcr_frequency_stop.setDecimals(3)
        self.lcr_frequency_stop.setSuffix(" MHz")

        self.lcr_frequency_steps: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.lcr_frequency_steps.setRange(1, 1000)

        self.lcr_amplitude: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_amplitude.setRange(0, 2.1e4)
        self.lcr_amplitude.setDecimals(3)
        self.lcr_amplitude.setSuffix(" mV")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage", self))
        hvsrcGroupBoxLayout.addWidget(self.bias_voltage)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance)
        hvsrcGroupBoxLayout.addStretch()

        lcrRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        lcrRampGroupBox.setTitle("LCR")

        lcrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(lcrRampGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Start", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_start)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Stop", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_stop)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Steps (log10)", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_steps)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        lcrGroupBoxLayout.addWidget(self.lcr_amplitude)
        lcrGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)
        self.generalWidgetLayout.addWidget(lcrRampGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        fahrad = ureg("F")
        volt = ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)
        self.series_transform["xfit"] = self.series_transform.get("lcr")

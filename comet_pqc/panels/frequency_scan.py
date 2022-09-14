import comet
from comet import ui
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["FrequencyScanPanel"]


class FrequencyScanPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Frequency scan with log10 steps."""

    type = "frequency_scan"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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

        self.bias_voltage = ui.Number(decimals=3, suffix="V")

        self.hvsrc_current_compliance = ui.Number(decimals=3, suffix="uA")

        self.lcr_frequency_start = ui.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = ui.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = ui.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = ui.Number(minimum=0, decimals=3, suffix="mV")

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
        hvsrcGroupBoxLayout.addWidget(self.bias_voltage.qt)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Current Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance.qt)
        hvsrcGroupBoxLayout.addStretch()

        lcrRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        lcrRampGroupBox.setTitle("LCR")

        lcrGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(lcrRampGroupBox)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Start", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_start.qt)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Stop", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_stop.qt)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency Steps (log10)", self))
        lcrGroupBoxLayout.addWidget(self.lcr_frequency_steps.qt)
        lcrGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        lcrGroupBoxLayout.addWidget(self.lcr_amplitude.qt)
        lcrGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)
        self.generalWidgetLayout.addWidget(lcrRampGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        fahrad = comet.ureg("F")
        volt = comet.ureg("V")

        self.series_transform["lcr"] = lambda x, y: ((x * volt).to("V").m, (y * fahrad).to("pF").m)
        self.series_transform["xfit"] = self.series_transform.get("lcr")

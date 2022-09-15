from comet import ui, ureg
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["CVRampPanel"]


class CVRampPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp measurements."""

    type = "cv_ramp"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setTitle("CV Ramp (HV Source)")

        self.register_hvsource()
        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR Cp", color="blue")
        self.plot.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(0, self.plot.qt, "CV Curve")

        self.plot2 = ui.Plot(height=300, legend="right")
        self.plot2.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot2.add_axis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plot2.axes.get("y").qt.setLabelFormat("%G")
        self.plot2.add_series("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.plot2.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(1, self.plot2.qt, "1/C² Curve")

        self.voltage_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_start.setRange(-2.1e3, 2.1e3)
        self.voltage_start.setDecimals(3)
        self.voltage_start.setSuffix(" V")

        self.voltage_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_stop.setRange(-2.1e3, 2.1e3)
        self.voltage_stop.setDecimals(3)
        self.voltage_stop.setSuffix(" V")

        self.voltage_step: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_step.setRange(0, 2.1e2)
        self.voltage_step.setDecimals(3)
        self.voltage_step.setSuffix(" V")

        self.waiting_time: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time.setRange(0, 60)
        self.waiting_time.setDecimals(2)
        self.waiting_time.setSuffix(" s")

        self.hvsrc_current_compliance: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrc_current_compliance.setRange(0, 2.1e6)
        self.hvsrc_current_compliance.setDecimals(3)
        self.hvsrc_current_compliance.setSuffix(" uA")

        self.hvsrc_accept_compliance: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrc_accept_compliance.setText("Accept Compliance")

        self.lcr_frequency: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_frequency.setDecimals(3)
        self.lcr_frequency.setRange(0.020, 20e3)
        self.lcr_frequency.setValue(1)
        self.lcr_frequency.setSuffix(" kHz")

        self.lcr_amplitude: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcr_amplitude.setDecimals(3)
        self.lcr_amplitude.setRange(0, 2.1e6)
        self.lcr_amplitude.setSuffix(" mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("hvsrc_accept_compliance", self.hvsrc_accept_compliance, False)
        self.bind("lcr_frequency", self.lcr_frequency, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 250, unit="mV")

        hvsrcRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcRampGroupBox.setTitle("HV Source Ramp")

        hvsrcRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcRampGroupBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_start)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_stop)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_step)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        hvsrcRampGroupBoxLayout.addWidget(self.waiting_time)
        hvsrcRampGroupBoxLayout.addStretch()

        hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance)
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_accept_compliance)
        hvsrcGroupBoxLayout.addStretch()

        frequencyGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        frequencyGroupBox.setTitle("LCR")

        frequencyGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(frequencyGroupBox)
        frequencyGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Frequency", self))
        frequencyGroupBoxLayout.addWidget(self.lcr_frequency)
        frequencyGroupBoxLayout.addWidget(QtWidgets.QLabel("AC Amplitude", self))
        frequencyGroupBoxLayout.addWidget(self.lcr_amplitude)
        frequencyGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)
        self.generalWidgetLayout.addWidget(frequencyGroupBox, 1)

        fahrad = ureg("F")
        volt = ureg("V")

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

    def append_reading(self, name, x, y):
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

    def clearReadings(self):
        super().clearReadings()
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

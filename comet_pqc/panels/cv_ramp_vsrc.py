import comet
from comet import ui
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, LCRMixin, VSourceMixin

__all__ = ["CVRampHVPanel"]


class CVRampHVPanel(MatrixPanel, VSourceMixin, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp measurements."""

    type = "cv_ramp_vsrc"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.title = "CV Ramp (V Source)"

        self.register_hvsource()
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

        self.voltage_start = ui.Number(decimals=3, suffix="V")
        self.voltage_stop = ui.Number(decimals=3, suffix="V")
        self.voltage_step = ui.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")

        self.vsrc_current_compliance = ui.Number(decimals=3, suffix="uA")
        self.vsrc_accept_compliance = ui.CheckBox("Accept Compliance")

        self.lcr_frequency = ui.Number(value=1, minimum=0.020, maximum=20e3, decimals=3, suffix="kHz")
        self.lcr_amplitude = ui.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_accept_compliance", self.vsrc_accept_compliance, False)
        self.bind("lcr_frequency", self.lcr_frequency, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 250, unit="mV")

        self.general_tab.layout = ui.Row(
            ui.GroupBox(
                title="V Source Ramp",
                layout=ui.Column(
                    ui.Label(text="Start"),
                    self.voltage_start,
                    ui.Label(text="Stop"),
                    self.voltage_stop,
                    ui.Label(text="Step"),
                    self.voltage_step,
                    ui.Label(text="Waiting Time"),
                    self.waiting_time,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="V Source",
                layout=ui.Column(
                    ui.Label(text="Compliance"),
                    self.vsrc_current_compliance,
                    self.vsrc_accept_compliance,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="LCR",
                layout=ui.Column(
                    ui.Label(text="AC Frequency"),
                    self.lcr_frequency,
                    ui.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    ui.Spacer()
                )
            ),
            stretch=(1, 1, 1)
        )

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

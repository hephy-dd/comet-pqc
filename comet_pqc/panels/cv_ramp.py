import logging

import comet

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import HVSourceMixin
from .panel import LCRMixin
from .panel import EnvironmentMixin

__all__ = ["CVRampPanel"]

class CVRampPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp measurements."""

    type = "cv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (HV Source)"

        self.register_vsource()
        self.register_lcr()
        self.register_environment()

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR Cp", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="CV Curve", layout=self.plot))

        self.plot2 = comet.Plot(height=300, legend="right")
        self.plot2.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot2.add_axis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plot2.axes.get("y").qt.setLabelFormat("%G")
        self.plot2.add_series("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.data_tabs.insert(1, comet.Tab(title="1/C² Curve", layout=self.plot2))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")

        self.hvsrc_current_compliance = comet.Number(decimals=3, suffix="uA")

        self.lcr_frequency = comet.Number(value=1, minimum=0.020, maximum=20e3, decimals=3, suffix="kHz")
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("lcr_frequency", self.lcr_frequency, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 250, unit="mV")

        self.general_tab.layout = comet.Row(
            comet.GroupBox(
                title="HV Source Ramp",
                layout=comet.Column(
                    comet.Label(text="Start"),
                    self.voltage_start,
                    comet.Label(text="Stop"),
                    self.voltage_stop,
                    comet.Label(text="Step"),
                    self.voltage_step,
                    comet.Label(text="Waiting Time"),
                    self.waiting_time,
                    comet.Spacer()
                )
            ),
            comet.GroupBox(
                title="HV Source Compliance",
                layout=comet.Column(
                    self.hvsrc_current_compliance,
                    comet.Spacer()
                )
            ),
            comet.GroupBox(
                title="LCR",
                layout=comet.Column(
                    comet.Label(text="AC Frequency"),
                    self.lcr_frequency,
                    comet.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    comet.Spacer()
                )
            ),
            stretch=(1, 1, 1)
        )

    def mount(self, measurement):
        super().mount(measurement)
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        for name, points in measurement.series.items():
            if name == "lcr":
                for x, y in points:
                    capacitance = y * comet.ureg('F')
                    self.plot.series.get(name).append(x, capacitance.to('pF').m)
            elif name == "lcr2":
                for x, y in points:
                    self.plot2.series.get(name).append(x, y)
        self.plot.fit()
        self.plot2.fit()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name == "lcr":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                capacitance = y * comet.ureg('F')
                self.plot.series.get(name).append(x, capacitance.to('pF').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
            elif name == "lcr2":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot2.series.get(name).append(x, y)
                if self.plot2.zoomed:
                    self.plot2.update("x")
                else:
                    self.plot2.fit()

    def clear_readings(self):
        super().clear_readings()
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

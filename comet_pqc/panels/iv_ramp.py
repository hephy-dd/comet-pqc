import logging
import re

import comet

from ..utils import format_metric
from ..metric import Metric
from .matrix import MatrixPanel
from .panel import HVSourceMixin
from .panel import EnvironmentMixin

__all__ = ["IVRampPanel"]

class IVRampPanel(MatrixPanel, HVSourceMixin, EnvironmentMixin):
    """Panel for IV ramp measurements."""

    type = "iv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp"

        self.register_vsource()
        self.register_environment()

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("hvsrc", "x", "y", text="HV Source", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")

        self.hvsrc_current_compliance = Metric(minimum=0, decimals=3, prefixes='mun', unit="A")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")

        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="A")

        self.general_tab.layout = comet.Row(
            comet.GroupBox(
                title="Ramp",
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
            comet.Spacer(),
            stretch=(1, 1, 1)
        )

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            for x, y in points:
                voltage = x * comet.ureg('V')
                current = y * comet.ureg('A')
                self.plot.series.get(name).append(x, current.to('uA').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
                self.plot.fit()

    def append_reading(self, name, x, y):
        voltage = x * comet.ureg('V')
        current = y * comet.ureg('A')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series.get(name).append(x, current.to('uA').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()

    def clear_readings(self):
        super().clear_readings()
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

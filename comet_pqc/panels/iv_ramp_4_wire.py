import comet

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import VSourceMixin
from .panel import EnvironmentMixin

__all__ = ["IVRamp4WirePanel"]

class IVRamp4WirePanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp measurements."""

    type = "iv_ramp_4_wire"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.register_hvsource()
        self.register_environment()

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.vsrc_voltage_compliance = comet.Number(decimals=3, suffix="V")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_voltage_compliance", self.vsrc_voltage_compliance, 0, unit="V")

        self.general_tab.layout = comet.Row(
            comet.GroupBox(
                title="Ramp",
                layout=comet.Column(
                    comet.Label(text="Start"),
                    self.current_start,
                    comet.Label(text="Stop"),
                    self.current_stop,
                    comet.Label(text="Step"),
                    self.current_step,
                    comet.Label(text="Waiting Time"),
                    self.waiting_time,
                    comet.Spacer()
                )
            ),
            comet.GroupBox(
                title="V Source Compliance",
                layout=comet.Column(
                    self.vsrc_voltage_compliance,
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
                current = x * comet.ureg('A')
                voltage = y * comet.ureg('V')
                self.plot.series.get(name).append(current.to('uA').m, voltage.m)
        self.update_readings()

    def append_reading(self, name, x, y):
        current = x * comet.ureg('A')
        voltage = y * comet.ureg('V')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((current.m, voltage.m))
                self.plot.series.get(name).append(current.to('uA').m, voltage.m)

    def update_readings(self):
        if self.measurement:
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

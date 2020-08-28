import comet
from comet import ui

from ..utils import format_metric
from .matrix import MatrixPanel
from .mixins import HVSourceMixin
from .mixins import VSourceMixin
from .mixins import EnvironmentMixin

__all__ = ["IVRampBiasPanel"]

class IVRampBiasPanel(MatrixPanel, HVSourceMixin, VSourceMixin, EnvironmentMixin):
    """Panel for bias IV ramp measurements."""

    type = "iv_ramp_bias"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Bias + IV Ramp"

        self.register_vsource()
        self.register_hvsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="blue")
        self.data_tabs.insert(0, ui.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = ui.Number(decimals=3, suffix="V")
        self.voltage_stop = ui.Number(decimals=3, suffix="V")
        self.voltage_step = ui.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")
        self.bias_voltage = ui.Number(decimals=3, suffix="V")
        self.bias_mode = ui.ComboBox(items=["constant", "offset"])

        self.hvsrc_current_compliance = ui.Metric(minimum=0, decimals=3, prefixes='mun', unit="A")
        self.vsrc_current_compliance = ui.Metric(minimum=0, decimals=3, prefixes='mun', unit="A")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="A")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="A")

        self.general_tab.layout = ui.Row(
            ui.GroupBox(
                title="HV Source Ramp",
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
                title="V Source Bias",
                layout=ui.Column(
                    ui.Label(text="Bias Voltage"),
                    self.bias_voltage,
                    ui.Label(text="Bias Compliance"),
                    self.vsrc_current_compliance,
                    ui.Label(text="Bias Mode"),
                    self.bias_mode,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="HV Source",
                layout=ui.Column(
                    ui.Label(text="Compliance"),
                    self.hvsrc_current_compliance,
                    ui.Spacer()
                )
            ),
            stretch=(1, 1, 1)
        )

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).clear()
                if points[0][0] > points[-1][0]:
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
                for x, y in points:
                    voltage = x * comet.ureg('V')
                    current = y * comet.ureg('A')
                    self.plot.series.get(name).append(voltage.m, current.to('uA').m)
        self.update_readings()

    def append_reading(self, name, x, y):
        voltage = x * comet.ureg('V')
        current = y * comet.ureg('A')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((voltage.m, current.m))
                if self.voltage_start.value > self.voltage_stop.value:
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
                self.plot.series.get(name).append(voltage.m, current.to('uA').m)

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

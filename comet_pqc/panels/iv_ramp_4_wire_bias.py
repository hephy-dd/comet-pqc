import comet
from comet import ui

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin, VSourceMixin

__all__ = ["IVRamp4WireBiasPanel"]


class IVRamp4WireBiasPanel(MatrixPanel, HVSourceMixin, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp with bias measurements."""

    type = "iv_ramp_4_wire_bias"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp Bias"

        self.register_vsource()
        self.register_hvsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="blue")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.data_tabs.insert(0, ui.Tab(title="IV Curve", layout=self.plot))

        self.current_start = ui.Number(decimals=3, suffix="uA")
        self.current_stop = ui.Number(decimals=3, suffix="uA")
        self.current_step = ui.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")
        self.bias_voltage = ui.Number(decimals=3, suffix="V")
        self.bias_mode = ui.ComboBox(["constant", "offset"])

        self.hvsrc_current_compliance = ui.Metric(minimum=0, decimals=3, prefixes="mun", unit="A")
        self.hvsrc_accept_compliance = ui.CheckBox("Accept Compliance")
        self.vsrc_voltage_compliance = ui.Number(decimals=3, suffix="V")
        self.vsrc_accept_compliance = ui.CheckBox("Accept Compliance")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")

        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrc_accept_compliance, False)
        self.bind("vsrc_voltage_compliance", self.vsrc_voltage_compliance, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrc_accept_compliance, False)

        self.general_tab.layout = ui.Row(
            ui.GroupBox(
                title="Ramp",
                layout=ui.Column(
                    ui.Label(text="Start"),
                    self.current_start,
                    ui.Label(text="Stop"),
                    self.current_stop,
                    ui.Label(text="Step"),
                    self.current_step,
                    ui.Label(text="Waiting Time"),
                    self.waiting_time,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="HV Source Bias",
                layout=ui.Column(
                    ui.Label(text="Bias Voltage"),
                    self.bias_voltage,
                    ui.Label(text="Bias Compliance"),
                    self.hvsrc_current_compliance,
                    self.hvsrc_accept_compliance,
                    ui.Label(text="Bias Mode"),
                    self.bias_mode,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="V Source",
                layout=ui.Column(
                    ui.Label(text="Compliance"),
                    self.vsrc_voltage_compliance,
                    self.vsrc_accept_compliance,
                    ui.Spacer()
                )
            ),
            ui.Spacer(),
            stretch=(1, 1, 1)
        )

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["vsrc"] = lambda x, y: ((x * ampere).to("uA").m, (y * volt).to("V").m)
        self.series_transform["xfit"] = self.series_transform.get("vsrc")

    def mount(self, measurement):
        super().mount(measurement)
        self.plot.series.get("xfit").qt.setVisible(False)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series.get(name).append(*tr(x, y))
            self.plot.series.get(name).qt.setVisible(True)
        self.update_readings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plot.series.get(name).append(*tr(x, y))
                self.plot.series.get(name).qt.setVisible(True)

    def update_readings(self):
        super().update_readings()
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.qt.chart().zoomOut() # HACK
                self.plot.fit()

    def clear_readings(self):
        super().clear_readings()
        self.plot.series.get("xfit").qt.setVisible(False)
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

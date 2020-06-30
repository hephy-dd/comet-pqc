import comet

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import VSourceMixin
from .panel import EnvironmentMixin

__all__ = ["IVRampBiasPanel"]

class IVRampBiasPanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for bias IV ramp measurements."""

    type = "iv_ramp_bias"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Bias + IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("hvsrc", "x", "y", text="HV Source", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.bias_mode = comet.ComboBox(items=["constant", "offset"])

        self.register_vsource()
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.hvsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.hvsrc_sense_mode = comet.ComboBox(items=["local", "remote"])

        def toggle_hvsrc_filter(enabled):
            self.hvsrc_filter_count.enabled = enabled
            self.hvsrc_filter_count_label.enabled = enabled
            self.hvsrc_filter_type.enabled = enabled
            self.hvsrc_filter_type_label.enabled = enabled

        self.hvsrc_filter_enable = comet.CheckBox(text="Enable", changed=toggle_hvsrc_filter)
        self.hvsrc_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.hvsrc_filter_count_label = comet.Label(text="Count")
        self.hvsrc_filter_type = comet.ComboBox(items=["repeat", "moving"])
        self.hvsrc_filter_type_label = comet.Label(text="Type")

        toggle_hvsrc_filter(False)

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("hvsrc_sense_mode", self.hvsrc_sense_mode, "local")
        self.bind("hvsrc_filter_enable", self.hvsrc_filter_enable, False)
        self.bind("hvsrc_filter_count", self.hvsrc_filter_count, 10)
        self.bind("hvsrc_filter_type", self.hvsrc_filter_type, "repeat")

        # Instruments status

        self.status_hvsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, "---")
        self.status_hvsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_current", self.status_hvsrc_current, "---")
        self.status_hvsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_output", self.status_hvsrc_output, "---")

        self.register_environment()

        self.status_panel.append(comet.GroupBox(
            title="HV Source Status",
            layout=comet.Column(
                comet.Row(
                    comet.Column(
                        comet.Label("Voltage"),
                        self.status_hvsrc_voltage
                    ),
                    comet.Column(
                        comet.Label("Current"),
                        self.status_hvsrc_current
                    ),
                    comet.Column(
                        comet.Label("Output"),
                        self.status_hvsrc_output
                    )
                )
            )
        ))

        self.status_panel.append(comet.Spacer())

        self.general_tab.layout.append(comet.GroupBox(
            title="V Source Ramp",
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
        ))

        self.general_tab.layout.append(comet.GroupBox(
            title="HV Source Bias",
            layout=comet.Column(
                comet.Label(text="Bias Voltage"),
                self.bias_voltage,
                comet.Label(text="Bias Mode"),
                self.bias_mode,
                comet.Spacer()
            )
        ))

        self.general_tab.layout.append(comet.GroupBox(
            title="Compliance",
            layout=comet.Column(
                comet.Label(text="V Source Compliance"),
                self.vsrc_current_compliance,
                comet.Label(text="HV Source Compliance"),
                self.hvsrc_current_compliance,
                comet.Spacer()
            )
        ))

        self.general_tab.stretch = 1, 1, 1

        self.control_tabs.append(comet.Tab(
            title="HV Source",
            layout=comet.Row(
                comet.GroupBox(
                    title="Filter",
                    layout=comet.Column(
                        self.hvsrc_filter_enable,
                        self.hvsrc_filter_count_label,
                        self.hvsrc_filter_count,
                        self.hvsrc_filter_type_label,
                        self.hvsrc_filter_type,
                        comet.Spacer()
                    )
                ),
                comet.GroupBox(
                    title="Options",
                    layout=comet.Column(
                        comet.Label(text="Sense Mode"),
                        self.hvsrc_sense_mode,
                        comet.Spacer()
                    )
                ),
                comet.Spacer(),
                stretch=(1, 1, 1)
            )
        ))

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

    def unmount(self):
        super().unmount()

    def state(self, state):
        if 'hvsrc_voltage' in state:
            value = state.get('hvsrc_voltage')
            self.status_hvsrc_voltage.value = format_metric(value, "V")
        if 'hvsrc_current' in state:
            value = state.get('hvsrc_current')
            self.status_hvsrc_current.value = format_metric(value, "A")
        if 'hvsrc_output' in state:
            self.status_hvsrc_output.value = state.get('hvsrc_output') or '---'
        super().state(state)

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

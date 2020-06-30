import comet

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import EnvironmentMixin

__all__ = ["IVRamp4WirePanel"]

class IVRamp4WirePanel(MatrixPanel, EnvironmentMixin):
    """Panel for 4 wire IV ramp measurements."""

    type = "iv_ramp_4_wire"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("hvsrc", "x", "y", text="HV Source", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.hvsrc_voltage_compliance = comet.Number(decimals=3, suffix="V")
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

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("hvsrc_voltage_compliance", self.hvsrc_voltage_compliance, 0, unit="V")
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
        ))

        self.general_tab.layout.append(comet.GroupBox(
            title="HV Source Compliance",
            layout=comet.Column(
                self.hvsrc_voltage_compliance,
                comet.Spacer()
            )
        ))

        self.general_tab.layout.append(comet.Spacer())

        self.general_tab.strech = 1, 1, 1

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
                self.plot.series.clear()
            for x, y in points:
                current = x * comet.ureg('A')
                voltage = y * comet.ureg('V')
                self.plot.series.get(name).append(current.to('uA').m, voltage.m)
        self.update_readings()

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

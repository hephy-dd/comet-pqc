import comet

from ..utils import format_metric
from ..metric import Metric
from .matrix import MatrixPanel

__all__ = ["IVRampBiasElmPanel"]

class IVRampBiasElmPanel(MatrixPanel):
    """Panel for bias IV ramp measurements."""

    type = "iv_ramp_bias_elm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp Bias Elm"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.bias_mode = comet.ComboBox(items=["constant", "offset"])
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.vsrc_sense_mode = comet.ComboBox(items=["local", "remote"])
        self.vsrc_route_termination = comet.ComboBox(items=["front", "rear"])
        self.hvsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.hvsrc_sense_mode = comet.ComboBox(items=["local", "remote"])

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.enabled = enabled
            self.vsrc_filter_count_label.enabled = enabled
            self.vsrc_filter_type.enabled = enabled
            self.vsrc_filter_type_label.enabled = enabled

        self.vsrc_filter_enable = comet.CheckBox(text="Enable", changed=toggle_vsrc_filter)
        self.vsrc_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.vsrc_filter_count_label = comet.Label(text="Count")
        self.vsrc_filter_type = comet.ComboBox(items=["repeat", "moving"])
        self.vsrc_filter_type_label = comet.Label(text="Type")

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

        def toggle_elm_filter(enabled):
            self.elm_filter_count.enabled = enabled
            self.elm_filter_count_label.enabled = enabled
            self.elm_filter_type.enabled = enabled
            self.elm_filter_type_label.enabled = enabled

        self.elm_filter_enable = comet.CheckBox(text="Enable", changed=toggle_elm_filter)
        self.elm_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.elm_filter_count_label = comet.Label(text="Count")
        self.elm_filter_type = comet.ComboBox(items=["repeat", "moving"])
        self.elm_filter_type_label = comet.Label(text="Type")

        self.elm_zero_correction = comet.CheckBox(text="Zero Correction")
        self.elm_integration_rate = comet.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        self.elm_current_range = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")

        def toggle_elm_current_autorange(enabled):
            self.elm_current_range.enabled = not enabled
            self.elm_current_autorange_minimum.enabled = enabled
            self.elm_current_autorange_maximum.enabled = enabled

        self.elm_current_range = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_enable = comet.CheckBox(text="Enable", changed=toggle_elm_current_autorange)
        self.elm_current_autorange_minimum = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_maximum = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")

        toggle_vsrc_filter(False)
        toggle_hvsrc_filter(False)
        toggle_elm_filter(False)
        toggle_elm_current_autorange(False)

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_route_termination", self.vsrc_route_termination, "rear")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("hvsrc_sense_mode", self.hvsrc_sense_mode, "local")
        self.bind("hvsrc_filter_enable", self.hvsrc_filter_enable, False)
        self.bind("hvsrc_filter_count", self.hvsrc_filter_count, 10)
        self.bind("hvsrc_filter_type", self.hvsrc_filter_type, "repeat")
        self.bind("elm_filter_enable", self.elm_filter_enable, False)
        self.bind("elm_filter_count", self.elm_filter_count, 10)
        self.bind("elm_filter_type", self.elm_filter_type, "repeat")
        self.bind("elm_zero_correction", self.elm_zero_correction, False)
        self.bind("elm_integration_rate", self.elm_integration_rate, 50.0)
        self.bind("elm_current_range", self.elm_current_range, 20e-12, unit="A")
        self.bind("elm_current_autorange_enable", self.elm_current_autorange_enable, True)
        self.bind("elm_current_autorange_minimum", self.elm_current_autorange_minimum, 2.0E-11, unit="A")
        self.bind("elm_current_autorange_maximum", self.elm_current_autorange_maximum, 2.0E-2, unit="A")

        # Instruments status

        self.status_vsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "---")
        self.status_vsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_current", self.status_vsrc_current, "---")
        self.status_vsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_output", self.status_vsrc_output, "---")

        self.status_hvsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, "---")
        self.status_hvsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_current", self.status_hvsrc_current, "---")
        self.status_hvsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_output", self.status_hvsrc_output, "---")

        self.status_elm_current = comet.Text(value="---", readonly=True)
        self.bind("status_elm_current", self.status_elm_current, "---")

        self.status_env_chuck_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, "---")
        self.status_env_box_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_temperature", self.status_env_box_temperature, "---")
        self.status_env_box_humidity = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_humidity", self.status_env_box_humidity, "---")

        self.status_instruments = comet.Column(
            comet.GroupBox(
                title="V Source Status",
                layout=comet.Column(
                    comet.Row(
                        comet.Column(
                            comet.Label("Voltage"),
                            self.status_vsrc_voltage
                        ),
                        comet.Column(
                            comet.Label("Current"),
                            self.status_vsrc_current
                        ),
                        comet.Column(
                            comet.Label("Output"),
                            self.status_vsrc_output
                        )
                    )
                )
            ),
            comet.GroupBox(
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
            ),
            comet.GroupBox(
                title="Electrometer Status",
                layout=comet.Column(
                    comet.Row(
                        comet.Column(
                            comet.Label("Current"),
                            self.status_elm_current
                        ),
                        comet.Spacer(),
                        stretch=(1, 2)
                    )
                )
            ),
            comet.GroupBox(
                title="Environment Status",
                layout=comet.Column(
                    comet.Row(
                        comet.Column(
                            comet.Label("Chuck temp."),
                            self.status_env_chuck_temperature
                        ),
                        comet.Column(
                            comet.Label("Box temp."),
                            self.status_env_box_temperature
                        ),
                        comet.Column(
                            comet.Label("Box humid."),
                            self.status_env_box_humidity
                        )
                    )
                )
            ),
            comet.Spacer()
        )
        self.status_instruments.width = 240

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.GroupBox(
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
                    ),
                    comet.GroupBox(
                        title="HV Source Bias",
                        layout=comet.Column(
                            comet.Label(text="Bias Voltage"),
                            self.bias_voltage,
                            comet.Label(text="Bias Mode"),
                            self.bias_mode,
                            comet.Spacer()
                        )
                    ),
                    comet.GroupBox(
                        title="Compliance",
                        layout=comet.Column(
                            comet.Label(text="V Source Compliance"),
                            self.vsrc_current_compliance,
                            comet.Label(text="HV Source Compliance"),
                            self.hvsrc_current_compliance,
                            comet.Spacer()
                        )
                    ),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Matrix",
                layout=comet.Column(
                    self.control_panel[0],
                    comet.Spacer(),
                    stretch=(0, 1)
                )
            ),
            comet.Tab(
                title="V Source",
                layout=comet.Row(
                    comet.GroupBox(
                        title="Filter",
                        layout=comet.Column(
                            self.vsrc_filter_enable,
                            self.vsrc_filter_count_label,
                            self.vsrc_filter_count,
                            self.vsrc_filter_type_label,
                            self.vsrc_filter_type,
                            comet.Spacer()
                        )
                    ),
                    comet.GroupBox(
                        title="Options",
                        layout=comet.Column(
                            comet.Label(text="Sense Mode"),
                            self.vsrc_sense_mode,
                            comet.Label(text="Route Termination"),
                            self.vsrc_route_termination,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
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
            ),
            comet.Tab(
                title="Electrometer",
                layout=comet.Row(
                    comet.GroupBox(
                        title="Filter",
                        layout=comet.Column(
                            self.elm_filter_enable,
                            self.elm_filter_count_label,
                            self.elm_filter_count,
                            self.elm_filter_type_label,
                            self.elm_filter_type,
                            comet.Spacer()
                        )
                    ),
                    comet.Column(
                        comet.GroupBox(
                            title="Range",
                            layout=comet.Column(
                                comet.Label(text="Current Range"),
                                self.elm_current_range,
                            )
                        ),
                        comet.GroupBox(
                            title="Auto Range",
                            layout=comet.Column(
                                self.elm_current_autorange_enable,
                                comet.Label(text="Minimum Current"),
                                self.elm_current_autorange_minimum,
                                comet.Label(text="Maximum Current"),
                                self.elm_current_autorange_maximum,
                                comet.Spacer()
                            )
                        )
                    ),
                    comet.GroupBox(
                        title="Options",
                        layout=comet.Column(
                            self.elm_zero_correction,
                            comet.Label(text="Integration Rate"),
                            self.elm_integration_rate,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 1, 1)
                )
            )
        )

        self.control_panel.append(comet.Row(
            self.tabs,
            self.status_instruments,
            stretch=(3, 1)
        ))

    def lock(self):
        for tab in self.tabs:
            tab.enabled = False
        self.status_instruments.enabled = True
        if len(self.tabs):
            self.tabs.current = self.tabs[0]

    def unlock(self):
        for tab in self.tabs:
            tab.enabled = True

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
        if 'vsrc_voltage' in state:
            value = state.get('vsrc_voltage')
            self.status_vsrc_voltage.value = format_metric(value, "V")
        if 'vsrc_current' in state:
            value = state.get('vsrc_current')
            self.status_vsrc_current.value = format_metric(value, "A")
        if 'vsrc_output' in state:
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_vsrc_output.value = labels[state.get('vsrc_output')]
        if 'hvsrc_voltage' in state:
            value = state.get('hvsrc_voltage')
            self.status_hvsrc_voltage.value = format_metric(value, "V")
        if 'hvsrc_current' in state:
            value = state.get('hvsrc_current')
            self.status_hvsrc_current.value = format_metric(value, "A")
        if 'hvsrc_output' in state:
            self.status_hvsrc_output.value = state.get('hvsrc_output') or '---'
        if 'elm_current' in state:
            value = state.get('elm_current')
            self.status_elm_current.value = format_metric(value, "A")
        if 'env_chuck_temperature' in state:
            value = state.get('env_chuck_temperature')
            self.status_env_chuck_temperature.value = format_metric(value, "°C", decimals=2)
        if 'env_box_temperature' in state:
            value = state.get('env_box_temperature')
            self.status_env_box_temperature.value = format_metric(value, "°C", decimals=2)
        if 'env_box_humidity' in state:
            value = state.get('env_box_humidity')
            self.status_env_box_humidity.value = format_metric(value, "%rH", decimals=2)
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

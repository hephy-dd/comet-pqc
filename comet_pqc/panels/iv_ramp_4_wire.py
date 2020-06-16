import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["IVRamp4WirePanel"]

class IVRamp4WirePanel(MatrixPanel):
    """Panel for 4 wire IV ramp measurements."""

    type = "iv_ramp_4_wire"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("hvsrc", "x", "y", text="HVSource", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.hvsrc_voltage_compliance = comet.Number(decimals=3, suffix="V")
        self.hvsrc_sense_mode = comet.ComboBox(items=["local", "remote"])

        def toggle_vsrc_filter(enabled):
            self.hvsrc_filter_count.enabled = enabled
            self.hvsrc_filter_count_label.enabled = enabled
            self.hvsrc_filter_type.enabled = enabled
            self.hvsrc_filter_type_label.enabled = enabled

        self.hvsrc_filter_enable = comet.CheckBox(text="Enable", changed=toggle_vsrc_filter)
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

        self.status_hvsrc_model = comet.Label()
        self.bind("status_hvsrc_model", self.status_hvsrc_model, "Model: n/a")
        self.status_hvsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, "n/a")
        self.status_hvsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_current", self.status_hvsrc_current, "n/a")
        self.status_hvsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_hvsrc_output", self.status_hvsrc_output, "n/a")

        self.status_env_model = comet.Label()
        self.bind("status_env_model", self.status_env_model, "Model: n/a")
        self.status_env_chuck_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, "n/a")
        self.status_env_box_temperature = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_temperature", self.status_env_box_temperature, "n/a")
        self.status_env_box_humidity = comet.Text(value="---", readonly=True)
        self.bind("status_env_box_humidity", self.status_env_box_humidity, "n/a")

        self.status_instruments = comet.Column(
            comet.GroupBox(
                title="HVSource Status",
                layout=comet.Column(
                    self.status_hvsrc_model,
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
                title="Environment Status",
                layout=comet.Column(
                    self.status_env_model,
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

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
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
                        title="HVSource Compliance",
                        layout=comet.Column(
                            self.hvsrc_voltage_compliance,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Matrix",
                layout=comet.Column(
                    self.controls[0],
                    comet.Spacer(),
                    stretch=(0, 1)
                )
            ),
            comet.Tab(
                title="HVSource",
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
            )
        )

        self.controls.append(comet.Row(
            self.tabs,
            self.status_instruments,
            stretch=(2, 1)
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
                self.plot.series.clear()
            for x, y in points:
                voltage = x * comet.ureg('V')
                current = y * comet.ureg('A')
                self.plot.series.get(name).append(current.to('uA').m, voltage.m)
        self.update_readings()

    def state(self, state):
        if 'hvsrc_model' in state:
            value = state.get('hvsrc_model', "n/a")
            self.status_hvsrc_model.text = f"Model: {value}"
        if 'hvsrc_voltage' in state:
            value = state.get('hvsrc_voltage')
            self.status_hvsrc_voltage.value = auto_unit(value, "V")
        if 'hvsrc_current' in state:
            value = state.get('hvsrc_current')
            self.status_hvsrc_current.value = auto_unit(value, "A")
        if 'hvsrc_output' in state:
            self.status_hvsrc_output.value = state.get('hvsrc_output') or '---'
        if 'env_model' in state:
            value = state.get('env_model', "n/a")
            self.status_env_model.text = f"Model: {value}"
        if 'env_chuck_temperature' in state:
            value = state.get('env_chuck_temperature', "n/a")
            self.status_env_chuck_temperature.value = auto_unit(value, "°C", decimals=2)
        if 'env_box_temperature' in state:
            value = state.get('env_box_temperature', "n/a")
            self.status_env_box_temperature.value = auto_unit(value, "°C", decimals=2)
        if 'env_box_humidity' in state:
            value = state.get('env_box_humidity', "n/a")
            self.status_env_box_humidity.value = auto_unit(value, "%rH", decimals=2)
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

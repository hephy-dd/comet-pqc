import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["IVRamp4WirePanel"]

class IVRamp4WirePanel(MatrixPanel):
    """Panel for 4 wire IV ramp measurements."""

    type = "4wire_iv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("smu", "x", "y", text="SMU", color="red")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.voltage_compliance = comet.Number(decimals=3, suffix="V")
        self.sense_mode = comet.ComboBox(items=["local", "remote"])
        self.route_termination = comet.ComboBox(items=["front", "rear"])

        self.zero_correction = comet.CheckBox(text="Zero Correction")
        self.integration_rate = comet.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("voltage_compliance", self.voltage_compliance, 0, unit="V")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("zero_correction", self.zero_correction, False)
        self.bind("integration_rate", self.integration_rate, 50.0)

        # Instruments status

        self.status_smu_model = comet.Label()
        self.bind("status_smu_model", self.status_smu_model, "Model: n/a")
        self.status_smu_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_smu_voltage", self.status_smu_voltage, "n/a")
        self.status_smu_current = comet.Text(value="---", readonly=True)
        self.bind("status_smu_current", self.status_smu_current, "n/a")
        self.status_smu_output = comet.Text(value="---", readonly=True)
        self.bind("status_smu_output", self.status_smu_output, "n/a")

        self.status_elm_model = comet.Label()
        self.bind("status_elm_model", self.status_elm_model, "Model: n/a")
        self.status_elm_current = comet.Text(value="---", readonly=True)
        self.bind("status_elm_current", self.status_elm_current, "n/a")

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
                title="SMU Status",
                layout=comet.Column(
                    self.status_smu_model,
                    comet.Row(
                        comet.Column(
                            comet.Label("Voltage"),
                            self.status_smu_voltage
                        ),
                        comet.Column(
                            comet.Label("Current"),
                            self.status_smu_current
                        ),
                        comet.Column(
                            comet.Label("Output"),
                            self.status_smu_output
                        )
                    )
                )
            ),
            comet.GroupBox(
                title="Electrometer Status",
                layout=comet.Column(
                    self.status_elm_model,
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
                        title="SMU Compliance",
                        layout=comet.Column(
                            self.voltage_compliance,
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
                title="SMU",
                layout=comet.Row()
            ),
            comet.Tab(
                title="Electrometer",
                layout=comet.Row(
                    comet.GroupBox(
                        title="Options",
                        layout=comet.Column(
                            self.zero_correction,
                            comet.Label(text="Integration Rate"),
                            self.integration_rate,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 1)
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
                self.plot.series.get(name).append(x, current.to('uA').m)
        self.update_readings()

    def state(self, state):
        if 'smu_model' in state:
            value = state.get('smu_model', "n/a")
            self.status_smu_model.text = f"Model: {value}"
        if 'smu_voltage' in state:
            value = state.get('smu_voltage')
            self.status_smu_voltage.value = auto_unit(value, "V")
        if 'smu_current' in state:
            value = state.get('smu_current')
            self.status_smu_current.value = auto_unit(value, "A")
        if 'smu_output' in state:
            self.status_smu_output.value = state.get('smu_output') or '---'
        if 'elm_model' in state:
            value = state.get('elm_model', "n/a")
            self.status_elm_model.text = f"Model: {value}"
        if 'elm_current' in state:
            value = state.get('elm_current')
            self.status_elm_current.value = auto_unit(value, "A")
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
        voltage = x * comet.ureg('V')
        current = y * comet.ureg('A')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series.get(name).append(x, current.to('uA').m)

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

import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["IVRampBiasPanel"]

class IVRampBiasPanel(MatrixPanel):
    """Panel for bias IV ramp measurements."""

    type = "bias_iv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Bias + IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("vsrc", "x", "y", text="VSource", color="red")
        self.plot.add_series("hvsrc", "x", "y", text="HVSource", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.bias_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_current_compliance", self.bias_current_compliance, 0, unit="uA")
        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")

        # Instruments status

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
                title="VSource Status",
                layout=comet.Column()
            ),
            comet.GroupBox(
                title="HVSource Status",
                layout=comet.Column()
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
                        title="HVSource",
                        layout=comet.Column(
                            comet.Label(text="Voltage"),
                            self.bias_voltage,
                            comet.Label(text="Current Compliance"),
                            self.bias_current_compliance,
                            comet.Spacer()
                        )
                    ),
                    comet.GroupBox(
                        title="VSource",
                        layout=comet.Column(
                            comet.Label(text="Start"),
                            self.voltage_start,
                            comet.Label(text="Stop"),
                            self.voltage_stop,
                            comet.Label(text="Step"),
                            self.voltage_step
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
                title="VSource",
                layout=comet.Column()
            ),
            comet.Tab(
                title="HVSource",
                layout=comet.Column()
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

    def unmount(self):
        super().unmount()

    def state(self, state):
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

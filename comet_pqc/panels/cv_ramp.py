import logging

import comet

from ..utils import format_metric
from .matrix import MatrixPanel

__all__ = ["CVRampPanel"]

class CVRampPanel(MatrixPanel):
    """Panel for CV ramp measurements."""

    type = "cv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (VSrc)"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Capacitance [pF]")
        self.plot.add_series("lcr", "x", "y", text="LCR Cp", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="CV Curve", layout=self.plot))

        self.plot2 = comet.Plot(height=300, legend="right")
        self.plot2.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot2.add_axis("y", align="right", text="1/Capacitance² [1/F²]")
        self.plot2.add_series("lcr2", "x", "y", text="LCR Cp", color="blue")
        self.data_tabs.insert(1, comet.Tab(title="1/C² Curve", layout=self.plot2))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.vsrc_sense_mode = comet.ComboBox(items=["local", "remote"])
        self.vsrc_route_termination = comet.ComboBox(items=["front", "rear"])

        self.lcr_frequency = comet.Number(value=1, minimum=0.020, maximum=20e3, decimals=3, suffix="kHz")
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")
        self.lcr_integration_time = comet.ComboBox(items=["short", "medium", "long"])
        self.lcr_averaging_rate = comet.Number(minimum=1, maximum=256, decimals=0)
        self.lcr_auto_level_control = comet.CheckBox(text="Auto Level Control")
        self.lcr_soft_filter = comet.CheckBox(text="Filter STD/mean < 0.005")

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

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_route_termination", self.vsrc_route_termination, "rear")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")
        self.bind("lcr_frequency", self.lcr_frequency, 1.0, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 250, unit="mV")
        self.bind("lcr_integration_time", self.lcr_integration_time, "medium")
        self.bind("lcr_averaging_rate", self.lcr_averaging_rate, 1)
        self.bind("lcr_auto_level_control", self.lcr_auto_level_control, True)
        self.bind("lcr_soft_filter", self.lcr_soft_filter, True)

        # Instruments status

        self.status_vsrc_model = comet.Label()
        self.bind("status_vsrc_model", self.status_vsrc_model, "Model: n/a")
        self.status_vsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "---")
        self.status_vsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_current", self.status_vsrc_current, "---")
        self.status_vsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_output", self.status_vsrc_output, "---")

        self.status_lcr_model = comet.Label()
        self.bind("status_lcr_model", self.status_lcr_model, "Model: n/a")

        self.status_env_model = comet.Label()
        self.bind("status_env_model", self.status_env_model, "Model: n/a")
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
                    self.status_vsrc_model,
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
                title="LCR Status",
                layout=comet.Column(
                    self.status_lcr_model,
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
                        title="V Source Compliance",
                        layout=comet.Column(
                            self.vsrc_current_compliance,
                            comet.Spacer()
                        )
                    ),
                    comet.GroupBox(
                        title="LCR",
                        layout=comet.Column(
                            comet.Label(text="AC Frequency"),
                            self.lcr_frequency,
                            comet.Label(text="AC Amplitude"),
                            self.lcr_amplitude,
                            comet.Spacer()
                        )
                    ),
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
                title="LCR",
                layout=comet.Row(
                    comet.GroupBox(
                        title="Options",
                        layout=comet.Column(
                            comet.Label(text="Integration Time"),
                            self.lcr_integration_time,
                            comet.Label(text="Averaging Rate"),
                            self.lcr_averaging_rate,
                            self.lcr_auto_level_control,
                            self.lcr_soft_filter,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 2)
                )
            )
        )

        self.controls.append(comet.Row(
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
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        for name, points in measurement.series.items():
            if name == "lcr":
                for x, y in points:
                    capacitance = y * comet.ureg('F')
                    self.plot.series.get(name).append(x, capacitance.to('pF').m)
            elif name == "lcr2":
                for x, y in points:
                    self.plot2.series.get(name).append(x, y)
        self.plot.fit()
        self.plot2.fit()

    def unmount(self):
        super().unmount()

    def state(self, state):
        if 'vsrc_model' in state:
            value = state.get('vsrc_model', "n/a")
            self.status_vsrc_model.text = f"Model: {value}"
        if 'vsrc_voltage' in state:
            value = state.get('vsrc_voltage')
            self.status_vsrc_voltage.value = format_metric(value, "V")
        if 'vsrc_current' in state:
            value = state.get('vsrc_current')
            self.status_vsrc_current.value = format_metric(value, "A")
        if 'vsrc_output' in state:
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_vsrc_output.value = labels[state.get('vsrc_output')]
        if 'lcr_model' in state:
            value = state.get('lcr_model', "n/a")
            self.status_lcr_model.text = f"Model: {value}"
        if 'env_model' in state:
            value = state.get('env_model', "n/a")
            self.status_env_model.text = f"Model: {value}"
        if 'env_chuck_temperature' in state:
            value = state.get('env_chuck_temperature', "---")
            self.status_env_chuck_temperature.value = format_metric(value, "°C", decimals=2)
        if 'env_box_temperature' in state:
            value = state.get('env_box_temperature', "---")
            self.status_env_box_temperature.value = format_metric(value, "°C", decimals=2)
        if 'env_box_humidity' in state:
            value = state.get('env_box_humidity', "---")
            self.status_env_box_humidity.value = format_metric(value, "%rH", decimals=2)
        super().state(state)

    def append_reading(self, name, x, y):
        if self.measurement:
            if name == "lcr":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                capacitance = y * comet.ureg('F')
                self.plot.series.get(name).append(x, capacitance.to('pF').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
            elif name == "lcr2":
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot2.series.get(name).append(x, y)
                if self.plot2.zoomed:
                    self.plot2.update("x")
                else:
                    self.plot2.fit()

    def clear_readings(self):
        super().clear_readings()
        for series in self.plot.series.values():
            series.clear()
        for series in self.plot2.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()

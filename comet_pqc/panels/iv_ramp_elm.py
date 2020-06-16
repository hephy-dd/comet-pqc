import logging

import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["IVRampElmPanel"]

class IVRampElmPanel(MatrixPanel):
    """Panel for IV ramp with electrometer measurements."""

    type = "iv_ramp_elm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp Elm"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("vsrc", "x", "y", text="VSource", color="red")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.ComboBox(items=["local", "remote"])
        self.route_termination = comet.ComboBox(items=["front", "rear"])

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

        self.zero_correction = comet.CheckBox(text="Zero Correction")
        self.integration_rate = comet.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")
        self.bind("elm_filter_enable", self.elm_filter_enable, False)
        self.bind("elm_filter_count", self.elm_filter_count, 10)
        self.bind("elm_filter_type", self.elm_filter_type, "repeat")
        self.bind("zero_correction", self.zero_correction, False)
        self.bind("integration_rate", self.integration_rate, 50.0)

        # Instruments status

        self.status_vsrc_model = comet.Label()
        self.bind("status_vsrc_model", self.status_vsrc_model, "Model: n/a")
        self.status_vsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "n/a")
        self.status_vsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_current", self.status_vsrc_current, "n/a")
        self.status_vsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_output", self.status_vsrc_output, "n/a")

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
                title="VSource Status",
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
                        title="VSource Ramp",
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
                        title="VSource Compliance",
                        layout=comet.Column(
                            self.current_compliance,
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
                title="VSource",
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
                            self.sense_mode,
                            comet.Label(text="Route Termination"),
                            self.route_termination,
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
                self.plot.series.get(name).append(x, current.to('uA').m)
        self.update_readings()

    def state(self, state):
        if 'vsrc_model' in state:
            value = state.get('vsrc_model', "n/a")
            self.status_vsrc_model.text = f"Model: {value}"
        if 'vsrc_voltage' in state:
            value = state.get('vsrc_voltage')
            self.status_vsrc_voltage.value = auto_unit(value, "V")
        if 'vsrc_current' in state:
            value = state.get('vsrc_current')
            self.status_vsrc_current.value = auto_unit(value, "A")
        if 'vsrc_output' in state:
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_vsrc_output.value = labels[state.get('vsrc_output')]
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

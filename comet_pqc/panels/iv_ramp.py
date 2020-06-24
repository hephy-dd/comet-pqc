import logging
import re

import comet

from ..utils import format_metric
from .matrix import MatrixPanel

__all__ = ["IVRampPanel"]

class IVRampPanel(MatrixPanel):
    """Panel for IV ramp measurements."""

    type = "iv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.vsrc_sense_mode = comet.ComboBox(items=["local", "remote"])
        self.vsrc_route_termination = comet.ComboBox(items=["front", "rear"])

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

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_route_termination", self.vsrc_route_termination, "front")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")

        # Instruments status

        self.status_vsrc_model = comet.Label()
        self.bind("status_vsrc_model", self.status_vsrc_model, "Model: n/a")
        self.status_vsrc_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "---")
        self.status_vsrc_current = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_current", self.status_vsrc_current, "---")
        self.status_vsrc_output = comet.Text(value="---", readonly=True)
        self.bind("status_vsrc_output", self.status_vsrc_output, "---")

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
            comet.Spacer()
        )
        self.status_instruments.width = 240

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.GroupBox(
                        title="Ramp",
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
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            for x, y in points:
                voltage = x * comet.ureg('V')
                current = y * comet.ureg('A')
                self.plot.series.get(name).append(x, current.to('uA').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
                self.plot.fit()

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

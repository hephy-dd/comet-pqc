import logging
import re

import comet

from ..utils import auto_unit
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
        self.plot.add_series("series", "x", "y", text="SMU", color="red")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.route_termination = comet.Select(values=["front", "rear"])

        def toggle_smu_filter(enabled):
            self.smu_filter_count.enabled = enabled
            self.smu_filter_count_label.enabled = enabled
            self.smu_filter_type.enabled = enabled
            self.smu_filter_type_label.enabled = enabled

        self.smu_filter_enable = comet.CheckBox(text="Enable", changed=toggle_smu_filter)
        self.smu_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.smu_filter_count_label = comet.Label(text="Count")
        self.smu_filter_type = comet.Select(values=["repeat", "moving"])
        self.smu_filter_type_label = comet.Label(text="Type")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("smu_filter_enable", self.smu_filter_enable, False)
        self.bind("smu_filter_count", self.smu_filter_count, 10)
        self.bind("smu_filter_type", self.smu_filter_type, "repeat")

        # Instruments status

        self.status_smu_model = comet.Label()
        self.bind("status_smu_model", self.status_smu_model, "Model: n/a")
        self.status_smu_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_smu_voltage", self.status_smu_voltage, "n/a")
        self.status_smu_current = comet.Text(value="---", readonly=True)
        self.bind("status_smu_current", self.status_smu_current, "n/a")
        self.status_smu_output = comet.Text(value="---", readonly=True)
        self.bind("status_smu_output", self.status_smu_output, "n/a")

        self.status_instruments = comet.Column(
            comet.FieldSet(
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
            comet.Stretch()
        )

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.FieldSet(
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
                            comet.Stretch()
                        )
                    ),
                    comet.FieldSet(
                        title="SMU Compliance",
                        layout=comet.Column(
                            self.current_compliance,
                            comet.Stretch()
                        )
                    ),
                    comet.Stretch(),
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Matrix",
                layout=comet.Column(
                    self.controls.children[0],
                    comet.Stretch(),
                    stretch=(0, 1)
                )
            ),
            comet.Tab(
                title="SMU",
                layout=comet.Row(
                    comet.FieldSet(
                        title="Filter",
                        layout=comet.Column(
                            self.smu_filter_enable,
                            self.smu_filter_count_label,
                            self.smu_filter_count,
                            self.smu_filter_type_label,
                            self.smu_filter_type,
                            comet.Stretch()
                        )
                    ),
                    comet.FieldSet(
                        title="Options",
                        layout=comet.Column(
                            comet.Label(text="Sense Mode"),
                            self.sense_mode,
                            comet.Label(text="Route Termination"),
                            self.route_termination,
                            comet.Stretch()
                        )
                    ),
                    comet.Stretch(),
                    stretch=(1, 1, 1)
                )
            ),
        )

        self.controls.append(comet.Row(
            self.tabs,
            self.status_instruments,
            stretch=(2, 1)
        ))

    def lock(self):
        for tab in self.tabs.children:
            tab.enabled = False
        self.status_instruments.enabled = True
        self.tabs.current = 0

    def unlock(self):
        for tab in self.tabs.children:
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
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_smu_output.value = labels[state.get('smu_output')]
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

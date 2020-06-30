import logging

import comet

from ..utils import format_metric
from ..metric import Metric
from .matrix import MatrixPanel
from .panel import VSourceMixin
from .panel import EnvironmentMixin

__all__ = ["IVRampElmPanel"]

class IVRampElmPanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for IV ramp with electrometer measurements."""

    type = "iv_ramp_elm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp Elm"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="red")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="IV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")

        self.register_vsource()
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")

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

        def toggle_elm_current_autorange(enabled):
            self.elm_current_range.enabled = not enabled
            self.elm_current_autorange_minimum.enabled = enabled
            self.elm_current_autorange_maximum.enabled = enabled

        self.elm_current_range = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_enable = comet.CheckBox(text="Enable", changed=toggle_elm_current_autorange)
        self.elm_current_autorange_minimum = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_maximum = Metric(minimum=0, decimals=3, prefixes='munp', unit="A")

        toggle_elm_filter(False)
        toggle_elm_current_autorange(False)

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
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

        self.status_elm_current = comet.Text(value="---", readonly=True)
        self.bind("status_elm_current", self.status_elm_current, "---")

        self.register_environment()

        self.status_panel.append(comet.GroupBox(
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
            title="V Source Compliance",
            layout=comet.Column(
                self.vsrc_current_compliance,
                comet.Spacer()
            )
        ))

        self.general_tab.layout.append(comet.Spacer())
        self.general_tab.stretch = 1, 1, 1

        self.control_tabs.append(comet.Tab(
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
        ))

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
        if 'elm_current' in state:
            value = state.get('elm_current')
            self.status_elm_current.value = format_metric(value, "A")
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

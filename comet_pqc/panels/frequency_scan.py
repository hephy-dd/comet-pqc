import logging

import comet

from ..utils import format_metric
from .matrix import MatrixPanel

__all__ = ["FrequencyScanPanel"]

class FrequencyScanPanel(MatrixPanel):
    """Frequency scan with log10 steps."""

    type = "frequency_scan"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Frequency Scan"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="CV Curve", layout=self.plot))

        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.vsrc_sense_mode = comet.ComboBox(items=["local", "remote"])
        self.vsrc_route_termination = comet.ComboBox(items=["front", "rear"])

        self.lcr_frequency_start = comet.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = comet.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = comet.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.enabled = enabled
            self.vsrc_filter_count_label.enabled = enabled
            self.vsrc_filter_type.enabled = enabled
            self.vsrc_filter_type_label.enabled = enabled

        self.vsrc_filter_enabled = comet.CheckBox(text="Enable", changed=toggle_vsrc_filter)
        self.vsrc_filter_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.vsrc_filter_count_label = comet.Label(text="Count")
        self.vsrc_filter_type = comet.ComboBox(items=["repeat", "moving"])
        self.vsrc_filter_type_label = comet.Label(text="Type")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_route_termination", self.vsrc_route_termination, "rear")
        self.bind("vsrc_filter_enabled", self.vsrc_filter_enabled, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

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
            comet.Spacer()
        )
        self.status_instruments.width = 240

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.GroupBox(
                        title="V Source",
                        layout=comet.Column(
                            comet.Label(text="Bias Voltage"),
                            self.bias_voltage,
                            comet.Label(text="Current Compliance"),
                            self.vsrc_current_compliance,
                            comet.Spacer()
                        )
                    ),
                    comet.GroupBox(
                        title="LCR",
                        layout=comet.Column(
                            comet.Label(text="AC Frequency Start"),
                            self.lcr_frequency_start,
                            comet.Label(text="AC Frequency Stop"),
                            self.lcr_frequency_stop,
                            comet.Label(text="AC Frequency Steps (log10)"),
                            self.lcr_frequency_steps,
                            comet.Label(text="AC Amplitude"),
                            self.lcr_amplitude,
                            comet.Spacer()
                        )
                    ),
                    comet.Spacer(),
                    stretch=(1, 1, 2)
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
                            self.vsrc_filter_enabled,
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
        super().state(state)

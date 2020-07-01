import logging

import comet

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import VSourceMixin
from .panel import LCRMixin
from .panel import EnvironmentMixin

__all__ = ["FrequencyScanPanel"]

class FrequencyScanPanel(MatrixPanel, VSourceMixin, LCRMixin, EnvironmentMixin):
    """Frequency scan with log10 steps."""

    type = "frequency_scan"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Frequency Scan"

        self.register_vsource()
        self.register_lcr()
        self.register_environment()

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="CV Curve", layout=self.plot))

        self.bias_voltage = comet.Number(decimals=3, suffix="V")

        self.vsrc_current_compliance = comet.Number(decimals=3, suffix="uA")

        self.lcr_frequency_start = comet.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = comet.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = comet.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        self.general_tab.layout = comet.Row(
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
            stretch=(1, 1, 1)
        )

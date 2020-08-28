import logging

import comet
from comet import ui

from ..utils import format_metric
from .matrix import MatrixPanel
from .mixins import HVSourceMixin
from .mixins import LCRMixin
from .mixins import EnvironmentMixin

__all__ = ["FrequencyScanPanel"]

class FrequencyScanPanel(MatrixPanel, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """Frequency scan with log10 steps."""

    type = "frequency_scan"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Frequency Scan"

        self.register_vsource()
        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.data_tabs.insert(0, ui.Tab(title="CV Curve", layout=self.plot))

        self.bias_voltage = ui.Number(decimals=3, suffix="V")

        self.hvsrc_current_compliance = ui.Number(decimals=3, suffix="uA")

        self.lcr_frequency_start = ui.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = ui.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = ui.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = ui.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        self.general_tab.layout = ui.Row(
            ui.GroupBox(
                title="HV Source",
                layout=ui.Column(
                    ui.Label(text="Bias Voltage"),
                    self.bias_voltage,
                    ui.Label(text="Current Compliance"),
                    self.hvsrc_current_compliance,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="LCR",
                layout=ui.Column(
                    ui.Label(text="AC Frequency Start"),
                    self.lcr_frequency_start,
                    ui.Label(text="AC Frequency Stop"),
                    self.lcr_frequency_stop,
                    ui.Label(text="AC Frequency Steps (log10)"),
                    self.lcr_frequency_steps,
                    ui.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    ui.Spacer()
                )
            ),
            ui.Spacer(),
            stretch=(1, 1, 1)
        )

import logging

import comet
from comet import ui

from ..utils import format_metric
from .matrix import MatrixPanel
from .panel import LCRMixin
from .panel import EnvironmentMixin

__all__ = ["CVRampAltPanel"]

class CVRampAltPanel(MatrixPanel, LCRMixin, EnvironmentMixin):
    """Panel for CV ramp (alternate) measurements."""

    type = "cv_ramp_alt"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (LCR)"

        self.register_lcr()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("lcr", "x", "y", text="LCR", color="blue")
        self.data_tabs.insert(0, ui.Tab(title="CV Curve", layout=self.plot))

        self.voltage_start = ui.Number(decimals=3, suffix="V")
        self.voltage_stop = ui.Number(decimals=3, suffix="V")
        self.voltage_step = ui.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = ui.Number(decimals=3, suffix="uA")

        self.lcr_frequency = ui.Number(value=1, minimum=0.020, maximum=20e3, decimals=3, suffix="kHz")
        self.lcr_amplitude = ui.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("lcr_frequency", self.lcr_frequency, 1, unit="kHz")
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        self.general_tab.layout = ui.Row(
            ui.GroupBox(
                title="LCR Ramp",
                layout=ui.Column(
                    ui.Label(text="Start"),
                    self.voltage_start,
                    ui.Label(text="Stop"),
                    self.voltage_stop,
                    ui.Label(text="Step"),
                    self.voltage_step,
                    ui.Label(text="Waiting Time"),
                    self.waiting_time,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="LCR",
                layout=ui.Column(
                    ui.Label(text="Compliance"),
                    self.current_compliance,
                    ui.Spacer()
                )
            ),
            ui.GroupBox(
                title="LCR Freq.",
                layout=ui.Column(
                    ui.Label(text="AC Frequency"),
                    self.lcr_frequency,
                    ui.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    ui.Spacer()
                )
            ),
            stretch=(1, 1, 1)
        )

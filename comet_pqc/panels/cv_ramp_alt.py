import logging

import comet

from ..utils import auto_unit
from .matrix import MatrixPanel

__all__ = ["CVRampAltPanel"]

class CVRampAltPanel(MatrixPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (LCR)"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("elm", "x", "y", text="LCR", color="blue")
        self.data_tabs.insert(0, comet.Tab(title="CV Curve", layout=self.plot))

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")

        self.lcr_frequency = comet.List(height=64)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("lcr_frequency", self.lcr_frequency, [])
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        # Instruments status

        self.status_lcr_model = comet.Label()
        self.bind("status_lcr_model", self.status_lcr_model, "Model: n/a")

        self.status_instruments = comet.Column(
            comet.FieldSet(
                title="LCR Status",
                layout=comet.Column(
                    self.status_lcr_model,
                )
            ),
            comet.Stretch()
        )

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
                    comet.FieldSet(
                        title="LCR Ramp",
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
                        title="LCR Compliance",
                        layout=comet.Column(
                            self.current_compliance,
                            comet.Stretch()
                        )
                    ),
                    comet.FieldSet(
                        title="LCR Freq.",
                        layout=comet.Column(
                            comet.Label(text="AC Frequencies"),
                            self.lcr_frequency,
                            comet.Label(text="AC Amplitude"),
                            self.lcr_amplitude,
                            comet.Stretch()
                        )
                    ),
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
            )
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

    def state(self, state):
        if 'lcr_model' in state:
            value = state.get('lcr_model', "n/a")
            self.status_lcr_model.text = f"Model: {value}"
        super().state(state)

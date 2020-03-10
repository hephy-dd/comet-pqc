import comet
from .matrix import MatrixPanel

__all__ = ["FrequencyScanPanel"]

class FrequencyScanPanel(MatrixPanel):
    """Frequency scan with log10 steps."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Frequency Scan"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.lcr_frequency_start = comet.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = comet.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = comet.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="SMU",
                layout=comet.Column(
                    comet.Label(text="Bias Voltage"),
                    self.bias_voltage,
                    comet.Label(text="Current Compliance"),
                    self.current_compliance,
                    comet.Label(text="Sense Mode"),
                    self.sense_mode,
                    comet.Stretch()
                )
            ),
            comet.FieldSet(
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
                    comet.Stretch()
                )
            ),
            comet.Stretch(),
            stretch=(1, 1, 2)
        ))

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("lcr_frequency_start", self.lcr_frequency_start, 0, unit="Hz")
        self.bind("lcr_frequency_stop", self.lcr_frequency_stop, 0, unit="MHz")
        self.bind("lcr_frequency_steps", self.lcr_frequency_steps, 1)
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

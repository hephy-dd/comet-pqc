import comet
from .matrix import MatrixPanel

__all__ = ["CVRampPanel"]

class CVRampPanel(MatrixPanel):
    """Panel for CV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (1 SMU)"

        self.plot = comet.Plot(height=300)
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

        self.lcr_frequency = comet.List(height=64)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.bind("bias_voltage_start", self.bias_voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.bias_voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.bias_voltage_step, 0, unit="V")
        self.bind("lcr_frequency", self.lcr_frequency, [])
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="SMU",
                layout=comet.Column(
                    comet.Label(text="Start"),
                    self.bias_voltage_start,
                    comet.Label(text="Stop"),
                    self.bias_voltage_stop,
                    comet.Label(text="Step"),
                    self.bias_voltage_step
                )
            ),
            comet.FieldSet(
                title="LCR",
                layout=comet.Column(
                    comet.Label(text="AC Frequencies"),
                    self.lcr_frequency,
                    comet.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    comet.Stretch()
                )
            ),
            comet.Stretch(),
            stretch=(1, 1, 2)
        ))

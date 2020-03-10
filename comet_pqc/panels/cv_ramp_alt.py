import comet
from .matrix import MatrixPanel

__all__ = ["CVRampAltPanel"]

class CVRampAltPanel(MatrixPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (2 SMU)"

        self.plot = comet.Plot(height=300)
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

        self.bind("bias_voltage_start", self.bias_voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.bias_voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.bias_voltage_step, 0, unit="V")

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
            comet.Stretch(),
            stretch=(1, 3)
        ))

        self.bind("bias_voltage_start", self.bias_voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.bias_voltage_stop, 0, unit="V")
        self.bind("bias_voltage_step", self.bias_voltage_step, 0, unit="V")

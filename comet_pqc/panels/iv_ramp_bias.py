import comet
from .matrix import MatrixPanel

__all__ = ["IVRampBiasPanel"]

class IVRampBiasPanel(MatrixPanel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Bias + IV Ramp"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.bias_current_compliance = comet.Number(decimals=3, suffix="uA")
        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_current_compliance", self.bias_current_compliance, 0, unit="uA")
        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="Bias",
                layout=comet.Column(
                    comet.Label(text="Voltage"),
                    self.bias_voltage,
                    comet.Label(text="Current Compliance"),
                    self.bias_current_compliance,
                    comet.Stretch()
                )
            ),
            comet.FieldSet(
                title="SMU",
                layout=comet.Column(
                    comet.Label(text="Start"),
                    self.voltage_start,
                    comet.Label(text="Stop"),
                    self.voltage_stop,
                    comet.Label(text="Step"),
                    self.voltage_step
                )
            ),
            comet.Stretch(),
            stretch=(1, 1, 2)
        ))
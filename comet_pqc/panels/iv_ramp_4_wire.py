import comet
from .matrix import MatrixPanel

__all__ = ["IVRamp4WirePanel"]

class IVRamp4WirePanel(MatrixPanel):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="uA")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="SMU",
                layout=comet.Column(
                    comet.Label(text="Start"),
                    self.current_start,
                    comet.Label(text="Stop"),
                    self.current_stop,
                    comet.Label(text="Step"),
                    self.current_step
                )
            ),
            comet.Stretch(),
            stretch=(1, 3)
        ))

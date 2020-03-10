import comet
from .matrix import MatrixPanel

__all__ = ["IVRampPanel"]

class IVRampPanel(MatrixPanel):
    """Panel for IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.table = comet.Table(header=["Voltage [V]", "Current [uA]", ""], stretch=True)
        self.table.fit()

        self.tabs = comet.Tabs()
        self.tabs.append(comet.Tab(title="Plot", layout=self.plot))
        self.tabs.append(comet.Tab(title="Table", layout=self.table))
        self.data.append(self.tabs)

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(decimals=1, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="SMU",
                layout=comet.Row(
                    comet.Column(
                        comet.Label(text="Start"),
                        self.voltage_start,
                        comet.Label(text="Stop"),
                        self.voltage_stop,
                        comet.Label(text="Step"),
                        self.voltage_step,
                        comet.Stretch()
                    ),
                    comet.Column(
                        comet.Label(text="Waiting Time"),
                        self.waiting_time,
                        comet.Label(text="Current Compliance"),
                        self.current_compliance,
                        comet.Label(text="Sense Mode"),
                        self.sense_mode,
                        comet.Stretch()
                    )
                )
            ),
            comet.Stretch(),
            stretch=(2, 2)
        ))

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()

    def append_reading(self, name, x, y):
        voltage = x * comet.ureg('V')
        current = y * comet.ureg('A')
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.plot.series.get(name).append(x, current.to('uA').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
            self.table.append([
                format(voltage.to('V').m, '.3f'),
                format(current.to('uA').m, '.3f'),
            ])

    def clear_readings(self):
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
        self.table.clear()

import comet

from ..logview import LogView
from .matrix import MatrixPanel

__all__ = ["IVRampPanel"]

class IVRampPanel(MatrixPanel):
    """Panel for IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="SMU", color="red")

        #self.table = comet.Table(header=["Voltage [V]", "Current [uA]", ""], stretch=True)
        #self.table.fit()

        self.logview = LogView()
        self._stream_handler.targets.append(lambda record: self.logview.append(record))

        self.tabs = comet.Tabs()
        self.tabs.append(comet.Tab(title="Plot", layout=self.plot))
        #self.tabs.append(comet.Tab(title="Table", layout=self.table))
        self.tabs.append(comet.Tab(title="Logs", layout=self.logview))
        self.data.append(self.tabs)

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.route_termination = comet.Select(values=["front", "rear"])

        def toggle_average(enabled):
            self.average_count.enabled = enabled
            self.average_count_label.enabled = enabled
            self.average_type.enabled = enabled
            self.average_type_label.enabled = enabled

        self.average_enabled = comet.CheckBox(text="Enable", changed=toggle_average)
        self.average_count = comet.Number(minimum=0, maximum=100, decimals=0)
        self.average_count_label = comet.Label(text="Count")
        self.average_type = comet.Select(values=["repeat", "moving"])
        self.average_type_label = comet.Label(text="Type")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("average_enabled", self.average_enabled, False)
        self.bind("average_count", self.average_count, 10)
        self.bind("average_type", self.average_type, "repeat")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="Ramp",
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
            comet.Column(
                comet.FieldSet(
                    title="Compliance",
                    layout=comet.Column(
                        comet.Label(text="Current"),
                        self.current_compliance,
                    )
                ),
                comet.FieldSet(
                    title="Options",
                    layout=comet.Column(
                        comet.Label(text="Sense Mode"),
                        self.sense_mode,
                        comet.Label(text="Route Termination"),
                        self.route_termination,
                        comet.Stretch()
                    )
                ),
                stretch=(0, 1)
            ),
            comet.FieldSet(
                title="Average",
                layout=comet.Column(
                    self.average_enabled,
                    self.average_count_label,
                    self.average_count,
                    self.average_type_label,
                    self.average_type,
                    comet.Stretch()
                )
            ),
            comet.Stretch(),
            stretch=(1, 1, 1, 1)
        ))

    def mount(self, measurement):
        super().mount(measurement)
        #self.table.clear()
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            for x, y in points:
                voltage = x * comet.ureg('V')
                current = y * comet.ureg('A')
                self.plot.series.get(name).append(x, current.to('uA').m)
                if self.plot.zoomed:
                    self.plot.update("x")
                else:
                    self.plot.fit()
                # self.table.append([
                #     format(voltage.to('V').m, '.3f'),
                #     format(current.to('uA').m, '.3f'),
                # ])
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
            # self.table.append([
            #     format(voltage.to('V').m, '.3f'),
            #     format(current.to('uA').m, '.3f'),
            # ])

    def clear_readings(self):
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
        #self.table.clear()
        self.logview.clear()

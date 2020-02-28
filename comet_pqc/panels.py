from PyQt5 import QtCore

import comet

__all__ = [
    "Panel",
    "IVRamp",
    "BiasIVRamp",
    "CVRamp",
    "CVRampAlt",
    "FourWireIVRamp"
]

class Label(comet.Label):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stylesheet = "font-size: 16px; font-weight: bold; background-color: white; height: 32px;"
        self.qt.setTextFormat(QtCore.Qt.RichText)

class Panel(comet.Widget):
    """Base class for measurement panels."""

    name = "Panel"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_item = None
        self.title_label = comet.Label(
            stylesheet="font-size: 16px; font-weight: bold; background-color: white; height: 32px;"
        )
        self.title_label.qt.setTextFormat(QtCore.Qt.RichText)
        self.description_label = comet.Label()
        self.content = comet.Widget()
        self.layout = comet.Column(
            self.title_label,
            self.description_label,
            self.content,
            comet.Stretch(),
            stretch=(0, 0, 0, 1)
        )

    def load(self, item):
        """Load UI from item and measurement configuration."""
        self.current_item = item
        self.title_label.text = f"{self.name} &rarr; {item.name}"
        self.description_label.text = item.description

class IVRamp(Panel):
    """Panel for IV ramp measurements."""

    name = "IV Ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.matrix = comet.Text()

        self.voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.waiting_time = comet.Number(maximum=2000, decimals=1, suffix="s")
        self.current_compliance = comet.Number(maximum=200000, suffix="uA")
        self.sense_mode = comet.Select(values=["local"])

        self.content.layout = comet.Column(
            self.plot,
            comet.Label(text="Matrix"),
            self.matrix,
            comet.Row(
                comet.Column(
                    comet.Label(text="Start"),
                    self.voltage_start,
                    comet.Label(text="Stop"),
                    self.voltage_stop,
                    comet.Label(text="Step"),
                    self.voltage_step,
                    comet.Label(text="Waiting Time"),
                    self.waiting_time,
                    comet.Stretch()
                ),
                comet.Column(
                    comet.Label(text="Current Compliance"),
                    self.current_compliance,
                    comet.Label(text="Sense Mode"),
                    self.sense_mode,
                    comet.Stretch()
                )
            )
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = item.parameters.get("matrix")
        self.voltage_start.value = item.parameters.get("voltage_start").to("V").m
        self.voltage_stop.value = item.parameters.get("voltage_stop").to("V").m
        self.voltage_step.value = item.parameters.get("voltage_step").to("V").m
        self.waiting_time.value = item.parameters.get("waiting_time").to("s").m
        self.current_compliance.value = item.parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = item.parameters.get("sense_mode")

class BiasIVRamp(Panel):
    """Panel for bias IV ramp measurements."""

    name = "Bias + IV Ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.matrix = comet.Text()

        self.content.layout = comet.Column(
            self.plot,
            comet.Label(text="Matrix"),
            self.matrix,
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = item.parameters.get("matrix")

class CVRamp(Panel):
    """Panel for CV ramp measurements."""

    name = "CV Ramp (1 SMU)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)

        self.matrix = comet.Text()

        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")

        self.content.layout = comet.Column(
            self.plot,
            comet.Label(text="Matrix"),
            self.matrix,
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = item.parameters.get("matrix")
        self.bias_voltage_start.value = item.parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = item.parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = item.parameters.get("bias_voltage_step").to("V").m

class CVRampAlt(Panel):
    """Panel for CV ramp (alternate) measurements."""

    name = "CV Ramp (2 SMU)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)

        self.matrix = comet.Text()

        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")

        self.content.layout = comet.Column(
            self.plot,
            comet.Label(text="Matrix"),
            self.matrix,
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = item.parameters.get("matrix")
        self.bias_voltage_start.value = item.parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = item.parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = item.parameters.get("bias_voltage_step").to("V").m

class FourWireIVRamp(Panel):
    """Panel for 4 wire IV ramp measurements."""

    name = "4 Wire IV Ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.matrix = comet.Text()

        self.current_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_step = comet.Number(maximum=200000, decimals=3, suffix="nA")

        self.content.layout = comet.Column(
            self.plot,
            comet.Label(text="Matrix"),
            self.matrix,
            comet.Label(text="Start"),
            self.current_start,
            comet.Label(text="Stop"),
            self.current_stop,
            comet.Label(text="Step"),
            self.current_step
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = item.parameters.get("matrix")
        self.current_start.value = item.parameters.get("current_start").to("uA").m
        self.current_stop.value = item.parameters.get("current_stop").to("uA").m
        self.current_step.value = item.parameters.get("current_step").to("nA").m

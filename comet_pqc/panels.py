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

def encode_matrix(values):
    return ", ".join(map(format, values))

def decode_matrix(value):
    return list(map(str.strip, value.split(",")))

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

    def save(self):
        pass

class IVRamp(Panel):
    """Panel for IV ramp measurements."""

    name = "IV Ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot = comet.Plot(legend="bottom", height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.matrix = comet.Text(changed=lambda value: self.save())

        self.voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V", changed=lambda value: self.save())
        self.voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V", changed=lambda value: self.save())
        self.voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V", changed=lambda value: self.save())
        self.waiting_time = comet.Number(maximum=2000, decimals=1, suffix="s", changed=lambda value: self.save())
        self.current_compliance = comet.Number(maximum=200000, suffix="uA", changed=lambda value: self.save())
        self.sense_mode = comet.Select(values=["local", "remote"], changed=lambda value: self.save())

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
            ),
            comet.Stretch(),
            comet.Row(
                comet.Button(text="Restore Defaults", clicked=self.restore),
                comet.Stretch()
            )
        )

    def load(self, item):
        super().load(item)
        for name, points in item.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        self.matrix.value = encode_matrix(item.parameters.get("matrix"))
        self.voltage_start.value = item.parameters.get("voltage_start").to("V").m
        self.voltage_stop.value = item.parameters.get("voltage_stop").to("V").m
        self.voltage_step.value = item.parameters.get("voltage_step").to("V").m
        self.waiting_time.value = item.parameters.get("waiting_time").to("s").m
        self.current_compliance.value = item.parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = item.parameters.get("sense_mode")

    def save(self):
        super().save()
        if self.current_item:
            self.current_item[0].bold = True
            self.current_item.parameters["matrix"] = decode_matrix(self.matrix.value)
            self.current_item.parameters["voltage_start"] = self.voltage_start.value * comet.ureg("V")
            self.current_item.parameters["voltage_stop"] = self.voltage_stop.value * comet.ureg("V")
            self.current_item.parameters["voltage_step"] = self.voltage_step.value * comet.ureg("V")
            self.current_item.parameters["waiting_time"] = self.waiting_time.value * comet.ureg("s")
            self.current_item.parameters["current_compliance"] = self.current_compliance.value * comet.ureg("uA")
            self.current_item.parameters["sense_mode"] = self.sense_mode.current

    def restore(self):
        if self.current_item:
            self.current_item[0].bold = True
            self.matrix.value = encode_matrix(self.current_item.default_parameters.get("matrix"))
            self.voltage_start.value = self.current_item.default_parameters.get("voltage_start").to("V").m
            self.voltage_stop.value = self.current_item.default_parameters.get("voltage_stop").to("V").m
            self.voltage_step.value = self.current_item.default_parameters.get("voltage_step").to("V").m
            self.waiting_time.value = self.current_item.default_parameters.get("waiting_time").to("s").m
            self.current_compliance.value = self.current_item.default_parameters.get("current_compliance").to("uA").m
            self.sense_mode.current = self.current_item.default_parameters.get("sense_mode")

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
        self.matrix.value = encode_matrix(item.parameters.get("matrix"))

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
        self.matrix.value = encode_matrix(item.parameters.get("matrix"))
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
        self.matrix.value = encode_matrix(item.parameters.get("matrix"))
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
        self.matrix.value = encode_matrix(item.parameters.get("matrix"))
        self.current_start.value = item.parameters.get("current_start").to("uA").m
        self.current_stop.value = item.parameters.get("current_stop").to("uA").m
        self.current_step.value = item.parameters.get("current_step").to("nA").m

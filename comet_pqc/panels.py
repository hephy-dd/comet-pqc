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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load(self, item, measurement):
        """Load UI from item and measurement configuration."""
        pass

class IVRamp(Panel):
    """Panel for IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = Label()
        self.voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.waiting_time = comet.Number(maximum=2000, decimals=1, suffix="s")
        self.current_compliance = comet.Number(maximum=200000, suffix="uA")
        self.sense_mode = comet.Select(values=["local"])
        self.layout = comet.Column(
            self.title_label,
            comet.Plot(),
            comet.Label(text="Start"),
            self.voltage_start,
            comet.Label(text="Stop"),
            self.voltage_stop,
            comet.Label(text="Step"),
            self.voltage_step,
            comet.Label(text="Waiting Time"),
            self.waiting_time,
            comet.Label(text="Current Compliance"),
            self.current_compliance,
            comet.Label(text="Sense Mode"),
            self.sense_mode,
            comet.Stretch()
        )

    def load(self, item, measurement):
        self.title_label.text = f"IV Ramp &rarr; {item.name} &rarr; {measurement.name}"
        self.voltage_start.value = measurement.parameters.get("voltage_start").to("V").m
        self.voltage_stop.value = measurement.parameters.get("voltage_stop").to("V").m
        self.voltage_step.value = measurement.parameters.get("voltage_step").to("V").m
        self.waiting_time.value = measurement.parameters.get("waiting_time").to("s").m
        self.current_compliance.value = measurement.parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = measurement.parameters.get("sense_mode")

class BiasIVRamp(Panel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = Label()
        self.layout = comet.Column(
            self.title_label,
            comet.Plot(),
            comet.Stretch()
        )

    def load(self, item, measurement):
        self.title_label.text = f"Bias + IV Ramp &rarr; {item.name} &rarr; {measurement.name}"

class CVRamp(Panel):
    """Panel for CV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = Label()
        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.layout = comet.Column(
            self.title_label,
            comet.Plot(),
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step,
            comet.Stretch()
        )

    def load(self, item, measurement):
        self.title_label.text = f"CV Ramp (1 SMU) &rarr; {item.name} &rarr; {measurement.name}"
        self.bias_voltage_start.value = measurement.parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = measurement.parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = measurement.parameters.get("bias_voltage_step").to("V").m

class CVRampAlt(Panel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = Label()
        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.layout = comet.Column(
            self.title_label,
            comet.Plot(),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step,
            comet.Stretch()
        )

    def load(self, item, measurement):
        self.title_label.text = f"CV Ramp (2 SMU) &rarr; {item.name} &rarr; {measurement.name}"
        self.bias_voltage_start.value = measurement.parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = measurement.parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = measurement.parameters.get("bias_voltage_step").to("V").m

class FourWireIVRamp(Panel):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = Label()
        self.current_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_step = comet.Number(maximum=200000, decimals=3, suffix="nA")
        self.layout = comet.Column(
            self.title_label,
            comet.Plot(),
            comet.Label(text="Start"),
            self.current_start,
            comet.Label(text="Stop"),
            self.current_stop,
            comet.Label(text="Step"),
            self.current_step,
            comet.Stretch()
        )

    def load(self, item, measurement):
        self.title_label.text = f"4 Wire IV Ramp &rarr; {item.name} &rarr; {measurement.name}"
        self.current_start.value = measurement.parameters.get("current_start").to("uA").m
        self.current_stop.value = measurement.parameters.get("current_stop").to("uA").m
        self.current_step.value = measurement.parameters.get("current_step").to("nA").m

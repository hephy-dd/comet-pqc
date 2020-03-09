import time
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
    """Base class for panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class MeasurementPanel(Panel):
    """Base class for measurement panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_label = comet.Label(
            stylesheet="font-size: 16px; font-weight: bold; background-color: white; height: 32px;"
        )
        self.title_label.qt.setTextFormat(QtCore.Qt.RichText)
        self.description_label = comet.Label()
        self.data = comet.Column()
        self.controls = comet.Column()
        self.layout = comet.Column(
            self.title_label,
            self.description_label,
            self.data,
            self.controls,
            comet.Stretch(),
            stretch=(0, 0, 0, 0, 1)
        )
        self.unmount()

    def mount(self, measurement):
        """Mount measurement to panel."""
        self.unmount()
        self.title_label.text = f"{self.title} &rarr; {measurement.name}"
        self.description_label.text = measurement.description
        self.measurement = measurement

    def unmount(self):
        """Unmount measurement from panel."""
        self.title_label.text = ""
        self.description_label.text = ""
        self.measurement = None

    def store(self):
        pass

    def restore(self):
        """Restore measurement defaults."""
        pass

    def append_reading(self, name, x, y):
        pass

    def clear_readings(self):
        pass

    @property
    def locked(self):
        """Returns True if panel controls are locked."""
        return self.controls.enabled

    @locked.setter
    def locked(self, locked):
        """Set lcoked state of panel controls."""
        self.controls.enabled = not locked

class MatrixPanel(MeasurementPanel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.matrix_enabled = comet.CheckBox(text="Enabled")
        self.matrix_channels = comet.Text(
            tooltip="Matrix card switching channels, comma separated list."
        )

        self.controls.append(comet.FieldSet(
            title="Matrix",
            layout=comet.Column(
                self.matrix_enabled,
                comet.Label(text="Channels"),
                comet.Row(
                    self.matrix_channels,
                    comet.Button(text="Load from Matrix", enabled=False)
                )
            )
        ))

    def mount(self, measurement):
        super().mount(measurement)
        parameters = measurement.parameters
        self.matrix_enabled.checked = parameters.get("matrix_enabled")
        self.matrix_channels.value = encode_matrix(parameters.get("matrix_channels"))

    def store(self):
        super().store()
        if self.measurement:
            parameters = self.measurement.parameters
            parameters["matrix_enabled"] = self.matrix_enabled.checked
            parameters["matrix_channels"] = decode_matrix(self.matrix_channels.value)

    def restore(self):
        super().restore()
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            self.matrix_enabled.checked = default_parameters.get("matrix_enabled")
            self.matrix_channels.value = encode_matrix(default_parameters.get("matrix_channels"))

class IVRamp(MatrixPanel):
    """Panel for IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "IV Ramp"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")

        self.table = comet.Table(header=["Time [s]", "Voltage [V]", "Current [uA]", ""], stretch=True)

        self.tabs = comet.Tabs()
        self.tabs.append(comet.Tab(title="Plot", layout=self.plot))
        self.tabs.append(comet.Tab(title="Table", layout=self.table))
        self.data.append(self.tabs)

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(decimals=3, suffix="V")
        self.waiting_time = comet.Number(decimals=1, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])

        self.controls.append(comet.Row(
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
        ))

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.get(name).replace(points)
                self.plot.fit()
        parameters = measurement.parameters
        self.voltage_start.value = parameters.get("voltage_start").to("V").m
        self.voltage_stop.value = parameters.get("voltage_stop").to("V").m
        self.voltage_step.value = parameters.get("voltage_step").to("V").m
        self.waiting_time.value = parameters.get("waiting_time").to("s").m
        self.current_compliance.value = parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = parameters.get("sense_mode")

    def store(self):
        super().store()
        if self.measurement:
            parameters = self.measurement.parameters
            parameters["voltage_start"] = self.voltage_start.value * comet.ureg("V")
            parameters["voltage_stop"] = self.voltage_stop.value * comet.ureg("V")
            parameters["voltage_step"] = self.voltage_step.value * comet.ureg("V")
            parameters["waiting_time"] = self.waiting_time.value * comet.ureg("s")
            parameters["current_compliance"] = self.current_compliance.value * comet.ureg("uA")
            parameters["sense_mode"] = self.sense_mode.current

    def restore(self):
        super().restore()
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            self.voltage_start.value = default_parameters.get("voltage_start").to("V").m
            self.voltage_stop.value = default_parameters.get("voltage_stop").to("V").m
            self.voltage_step.value = default_parameters.get("voltage_step").to("V").m
            self.waiting_time.value = default_parameters.get("waiting_time").to("s").m
            self.current_compliance.value = default_parameters.get("current_compliance").to("uA").m
            self.sense_mode.current = default_parameters.get("sense_mode")

    def append_reading(self, name, x, y):
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
            self.table.append([time.time(), x, current.to('uA').m, ""])

    def clear_readings(self):
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
        self.table.clear()

class BiasIVRamp(MatrixPanel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Bias + IV Ramp"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(decimals=3, suffix="V")

        self.controls.append(comet.Column(
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step
        ))

class CVRamp(MatrixPanel):
    """Panel for CV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (1 SMU)"

        self.plot = comet.Plot(height=300)
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(decimals=3, suffix="V")

        self.controls.append(comet.Column(
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step
        ))

class CVRampAlt(MatrixPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (2 SMU)"

        self.plot = comet.Plot(height=300)
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(decimals=3, suffix="V")

        self.controls.append(comet.Column(
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step
        ))

class FourWireIVRamp(MatrixPanel):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "4 Wire IV Ramp"

        self.plot = comet.Plot(legend="bottom", height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.current_start = comet.Number(decimals=3, suffix="uA")
        self.current_stop = comet.Number(decimals=3, suffix="uA")
        self.current_step = comet.Number(decimals=3, suffix="nA")

        self.controls.append(comet.Column(
            comet.Label(text="Start"),
            self.current_start,
            comet.Label(text="Stop"),
            self.current_stop,
            comet.Label(text="Step"),
            self.current_step
        ))

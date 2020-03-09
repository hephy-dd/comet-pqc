import time
from PyQt5 import QtCore
import logging

import comet

__all__ = [
    "Panel",
    "IVRamp",
    "BiasIVRamp",
    "CVRamp",
    "CVRampAlt",
    "FourWireIVRamp",
    "FrequencyScan"
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
        self.matrix_enabled.checked = parameters.get("matrix_enabled", False)
        self.matrix_channels.value = encode_matrix(parameters.get("matrix_channels", []))

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
        self.bias_voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

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

class CVRamp(MatrixPanel):
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

    def mount(self, measurement):
        super().mount(measurement)
        parameters = measurement.parameters
        self.lcr_frequency.values = parameters.get("lcr_frequency", [])
        self.lcr_amplitude.value = parameters.get("lcr_amplitude").to("mV").m

    def store(self):
        super().store()
        if self.measurement:
            parameters = self.measurement.parameters
            parameters["lcr_frequency"] = self.lcr_frequency.values
            parameters["lcr_amplitude"] = self.lcr_amplitude.value * comet.ureg("mV")

    def restore(self):
        super().restore()
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            self.lcr_frequency.values = default_parameters.get("lcr_frequency_start", [])
            self.lcr_amplitude.value = default_parameters.get("lcr_amplitude").to("mV").m

class CVRampAlt(MatrixPanel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (2 SMU)"

        self.plot = comet.Plot(height=300)
        self.data.append(self.plot)

        self.bias_voltage_start = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")

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

class FourWireIVRamp(MatrixPanel):
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
        self.current_step = comet.Number(minimum=0, decimals=3, suffix="nA")

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

class FrequencyScan(MatrixPanel):
    """Frequency scan with log10 steps."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Frequency Scan"

        self.plot = comet.Plot(height=300)
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("series", "x", "y", text="IV", color="red")
        self.data.append(self.plot)

        self.bias_voltage = comet.Number(decimals=3, suffix="V")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.lcr_frequency_start = comet.Number(minimum=0, decimals=3, suffix="Hz")
        self.lcr_frequency_stop = comet.Number(minimum=0, decimals=3, suffix="MHz")
        self.lcr_frequency_steps = comet.Number(minimum=1, maximum=1000, decimals=0)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

        self.controls.append(comet.Row(
            comet.FieldSet(
                title="SMU",
                layout=comet.Column(
                    comet.Label(text="Bias Voltage"),
                    self.bias_voltage,
                    comet.Label(text="Current Compliance"),
                    self.current_compliance,
                    comet.Label(text="Sense Mode"),
                    self.sense_mode,
                    comet.Stretch()
                )
            ),
            comet.FieldSet(
                title="LCR",
                layout=comet.Column(
                    comet.Label(text="AC Frequency Start"),
                    self.lcr_frequency_start,
                    comet.Label(text="AC Frequency Stop"),
                    self.lcr_frequency_stop,
                    comet.Label(text="AC Frequency Steps (log10)"),
                    self.lcr_frequency_steps,
                    comet.Label(text="AC Amplitude"),
                    self.lcr_amplitude,
                    comet.Stretch()
                )
            ),
            comet.Stretch(),
            stretch=(1, 1, 2)
        ))

    def mount(self, measurement):
        super().mount(measurement)
        parameters = measurement.parameters
        self.bias_voltage.value = parameters.get("bias_voltage").to("V").m
        self.current_compliance.value = parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = parameters.get("sense_mode")
        self.lcr_frequency_start.value = parameters.get("lcr_frequency_start").to("Hz").m
        self.lcr_frequency_stop.value = parameters.get("lcr_frequency_stop").to("MHz").m
        self.lcr_frequency_steps.value = parameters.get("lcr_frequency_steps")
        self.lcr_amplitude.value = parameters.get("lcr_amplitude").to("mV").m

    def store(self):
        super().store()
        if self.measurement:
            parameters = self.measurement.parameters
            parameters["bias_voltage"] = self.bias_voltage.value * comet.ureg("V")
            parameters["current_compliance"] = self.current_compliance.value * comet.ureg("uA")
            parameters["sense_mode"] = self.sense_mode.current
            parameters["lcr_frequency_start"] = self.lcr_frequency_start.value * comet.ureg("Hz")
            parameters["lcr_frequency_stop"] = self.lcr_frequency_stop.value * comet.ureg("MHz")
            parameters["lcr_frequency_steps"] = self.lcr_frequency_steps.value
            parameters["lcr_amplitude"] = self.lcr_amplitude.value * comet.ureg("mV")

    def restore(self):
        super().restore()
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            self.bias_voltage.value = default_parameters.get("voltage_start").to("V").m
            self.current_compliance.value = default_parameters.get("current_compliance").to("uA").m
            self.sense_mode.current = default_parameters.get("sense_mode")
            self.lcr_frequency_start.value = default_parameters.get("lcr_frequency_start").to("Hz").m
            self.lcr_frequency_stop.value = default_parameters.get("lcr_frequency_stop").to("MHz").m
            self.lcr_frequency_steps.value = default_parameters.get("lcr_frequency_steps")
            self.lcr_amplitude.value = default_parameters.get("lcr_amplitude").to("mV").m

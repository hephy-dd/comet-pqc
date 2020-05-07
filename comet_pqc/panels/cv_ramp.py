import logging

import comet

from ..logwindow import LogWidget
from .matrix import MatrixPanel

__all__ = ["CVRampPanel"]

class CVRampPanel(MatrixPanel):
    """Panel for CV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "CV Ramp (1 SMU)"

        self.plot = comet.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Cap.")
        self.plot.add_series("elm", "x", "y", text="LCR", color="blue")

        self.logwidget = LogWidget()

        tabs = comet.Tabs()
        tabs.append(comet.Tab(title="Plot", layout=self.plot))
        tabs.append(comet.Tab(title="Logs", layout=self.logwidget))
        self.data.append(tabs)

        self.voltage_start = comet.Number(decimals=3, suffix="V")
        self.voltage_stop = comet.Number(decimals=3, suffix="V")
        self.voltage_step = comet.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = comet.Number(minimum=0, decimals=2, suffix="s")
        self.current_compliance = comet.Number(decimals=3, suffix="uA")
        self.sense_mode = comet.Select(values=["local", "remote"])
        self.route_termination = comet.Select(values=["front", "rear"])

        self.lcr_frequency = comet.List(height=64)
        self.lcr_amplitude = comet.Number(minimum=0, decimals=3, suffix="mV")

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

        self.bind("bias_voltage_start", self.voltage_start, 0, unit="V")
        self.bind("bias_voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("bias_voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("current_compliance", self.current_compliance, 0, unit="uA")
        self.bind("sense_mode", self.sense_mode, "local")
        self.bind("route_termination", self.route_termination, "front")
        self.bind("average_enabled", self.average_enabled, False)
        self.bind("average_count", self.average_count, 10)
        self.bind("average_type", self.average_type, "repeat")
        self.bind("lcr_frequency", self.lcr_frequency, [])
        self.bind("lcr_amplitude", self.lcr_amplitude, 0, unit="mV")

        # Instruments status

        self.status_smu_model = comet.Label()
        self.bind("status_smu_model", self.status_smu_model, "Model: n/a")
        self.status_smu_voltage = comet.Text(value="---", readonly=True)
        self.bind("status_smu_voltage", self.status_smu_voltage, "n/a")
        self.status_smu_current = comet.Text(value="---", readonly=True)
        self.bind("status_smu_current", self.status_smu_current, "n/a")
        self.status_smu_output = comet.Text(value="---", readonly=True)
        self.bind("status_smu_output", self.status_smu_output, "n/a")

        self.status_lcr_model = comet.Label()
        self.bind("status_lcr_model", self.status_lcr_model, "Model: n/a")

        self.status_instruments = comet.Column(
            comet.FieldSet(
                title="SMU Status",
                layout=comet.Column(
                    self.status_smu_model,
                    comet.Row(
                        comet.Column(
                            comet.Label("Voltage"),
                            self.status_smu_voltage
                        ),
                        comet.Column(
                            comet.Label("Current"),
                            self.status_smu_current
                        ),
                        comet.Column(
                            comet.Label("Output"),
                            self.status_smu_output
                        )
                    )
                )
            ),
            comet.FieldSet(
                title="LCR Status",
                layout=comet.Column(
                    self.status_lcr_model,
                )
            ),
            comet.Stretch()
        )

        self.tabs = comet.Tabs(
            comet.Tab(
                title="General",
                layout=comet.Row(
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
                    comet.FieldSet(
                        title="SMU Compliance",
                        layout=comet.Column(
                            self.current_compliance,
                            comet.Stretch()
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
                    stretch=(1, 1, 1)
                )
            ),
            comet.Tab(
                title="Matrix",
                layout=comet.Column(
                    self.controls.children[0],
                    comet.Stretch(),
                    stretch=(0, 1)
                )
            ),
            comet.Tab(
                title="SMU",
                layout=comet.Row(
                    comet.FieldSet(
                        title="Filter",
                        layout=comet.Column(
                            self.average_enabled,
                            self.average_count_label,
                            self.average_count,
                            self.average_type_label,
                            self.average_type,
                            comet.Stretch()
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
                    comet.Stretch(),
                    stretch=(1, 1, 1)
                )
            )
        )

        self.controls.append(comet.Row(
            self.tabs,
            self.status_instruments,
            stretch=(2, 1)
        ))

    def lock(self):
        for tab in self.tabs.children:
            tab.enabled = False
        self.status_instruments.enabled = True
        self.tabs.current = 0

    def unlock(self):
        for tab in self.tabs.children:
            tab.enabled = True

    def mount(self, measurement):
        super().mount(measurement)
        self.logwidget.add_logger(logging.getLogger())

    def umount(self):
        self.logwidget.remove_logger(logging.getLogger())
        super().umount()

    def state(self, state):
        if 'smu_model' in state:
            value = state.get('smu_model', "n/a")
            self.status_smu_model.text = f"Model: {value}"
        if 'smu_voltage' in state:
            value = state.get('smu_voltage')
            self.status_smu_voltage.value = auto_unit(value, "V")
        if 'smu_current' in state:
            value = state.get('smu_current')
            self.status_smu_current.value = auto_unit(value, "A")
        if 'smu_output' in state:
            labels = {False: "OFF", True: "ON", None: "---"}
            self.status_smu_output.value = labels[state.get('smu_output')]
        if 'lcr_model' in state:
            value = state.get('lcr_model', "n/a")
            self.status_lcr_model.text = f"Model: {value}"
        super().state(state)

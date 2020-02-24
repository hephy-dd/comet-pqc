import comet

class Panel(comet.Widget):
    """Base class for measurement panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_parameters(self, parameters):
        pass

class IVRamp(Panel):
    """Panel for IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.waiting_time = comet.Number(maximum=2000, decimals=1, suffix="s")
        self.current_compliance = comet.Number(maximum=200000, suffix="uA")
        self.sense_mode = comet.Select(values=["local"])
        self.layout = comet.Column(
            comet.Label("IV Ramp"),
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

    def update_parameters(self, parameters):
        super().update_parameters(parameters)
        self.voltage_start.value = parameters.get("voltage_start").to("V").m
        self.voltage_stop.value = parameters.get("voltage_stop").to("V").m
        self.voltage_step.value = parameters.get("voltage_step").to("V").m
        self.waiting_time.value = parameters.get("waiting_time").to("s").m
        self.current_compliance.value = parameters.get("current_compliance").to("uA").m
        self.sense_mode.current = parameters.get("sense_mode")

class BiasIVRamp(Panel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("Bias + IV Ramp"),
            comet.Plot(),
            comet.Stretch()
        )

class CVRamp(Panel):
    """Panel for CV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.layout = comet.Column(
            comet.Label("CV Ramp (1 SMU)"),
            comet.Plot(),
            comet.Label(text="Start"),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step,
            comet.Stretch()
        )

    def update_parameters(self, parameters):
        super().update_parameters(parameters)
        self.bias_voltage_start.value = parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = parameters.get("bias_voltage_step").to("V").m

class CVRampAlt(Panel):
    """Panel for CV ramp (alternate) measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bias_voltage_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="V")
        self.bias_voltage_step = comet.Number(maximum=2000, decimals=3, suffix="V")
        self.layout = comet.Column(
            comet.Label("CV Ramp (2 SMU)"),
            comet.Plot(),
            self.bias_voltage_start,
            comet.Label(text="Stop"),
            self.bias_voltage_stop,
            comet.Label(text="Step"),
            self.bias_voltage_step,
            comet.Stretch()
        )

    def update_parameters(self, parameters):
        super().update_parameters(parameters)
        self.bias_voltage_start.value = parameters.get("bias_voltage_start").to("V").m
        self.bias_voltage_stop.value = parameters.get("bias_voltage_stop").to("V").m
        self.bias_voltage_step.value = parameters.get("bias_voltage_step").to("V").m

class FourWireIVRamp(Panel):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_start = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_stop = comet.Number(minimum=-2000, maximum=2000, decimals=3, suffix="uA")
        self.current_step = comet.Number(maximum=200000, decimals=3, suffix="nA")
        self.layout = comet.Column(
            comet.Label("4 Wire IV Ramp"),
            comet.Plot(),
            comet.Label(text="Start"),
            self.current_start,
            comet.Label(text="Stop"),
            self.current_stop,
            comet.Label(text="Step"),
            self.current_step,
            comet.Stretch()
        )

    def update_parameters(self, parameters):
        super().update_parameters(parameters)
        self.current_start.value = parameters.get("current_start").to("uA").m
        self.current_stop.value = parameters.get("current_stop").to("uA").m
        self.current_step.value = parameters.get("current_step").to("nA").m

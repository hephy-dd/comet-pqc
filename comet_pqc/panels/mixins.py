from comet import ui

from ..utils import format_metric

__all__ = [
    'HVSourceMixin',
    'VSourceMixin',
    'ElectrometerMixin',
    'LCRMixin',
    'EnvironmentMixin'
]

class HVSourceMixin:
    """Mixin class providing default controls and status for HV Source."""

    def register_vsource(self):
        self.hvsrc_sense_mode = ui.ComboBox(items=["local", "remote"])
        self.hvsrc_route_termination = ui.ComboBox(items=["front", "rear"])

        def toggle_hvsrc_filter(enabled):
            self.hvsrc_filter_count.enabled = enabled
            self.hvsrc_filter_count_label.enabled = enabled
            self.hvsrc_filter_type.enabled = enabled
            self.hvsrc_filter_type_label.enabled = enabled

        self.hvsrc_filter_enable = ui.CheckBox(text="Enable", changed=toggle_hvsrc_filter)
        self.hvsrc_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.hvsrc_filter_count_label = ui.Label(text="Count")
        self.hvsrc_filter_type = ui.ComboBox(items=["repeat", "moving"])
        self.hvsrc_filter_type_label = ui.Label(text="Type")

        def toggle_hvsrc_source_voltage_autorange(enabled):
            self.hvsrc_source_voltage_range.enabled = not enabled

        self.hvsrc_source_voltage_autorange_enable = ui.CheckBox(text="Autorange", changed=toggle_hvsrc_source_voltage_autorange)
        self.hvsrc_source_voltage_range = ui.Number(minimum=-1100, maximum=1100, decimals=1, suffix="V")

        toggle_hvsrc_filter(False)
        toggle_hvsrc_source_voltage_autorange(False)

        self.bind("hvsrc_sense_mode", self.hvsrc_sense_mode, "local")
        self.bind("hvsrc_route_termination", self.hvsrc_route_termination, "rear")
        self.bind("hvsrc_filter_enable", self.hvsrc_filter_enable, False)
        self.bind("hvsrc_filter_count", self.hvsrc_filter_count, 10)
        self.bind("hvsrc_filter_type", self.hvsrc_filter_type, "repeat")
        self.bind("hvsrc_source_voltage_autorange_enable", self.hvsrc_source_voltage_autorange_enable, True)
        self.bind("hvsrc_source_voltage_range", self.hvsrc_source_voltage_range, 20, unit="V")

        self.status_hvsrc_voltage = ui.Text(value="---", readonly=True)
        self.status_hvsrc_current = ui.Text(value="---", readonly=True)
        self.status_hvsrc_output = ui.Text(value="---", readonly=True)

        self.bind("status_hvsrc_voltage", self.status_hvsrc_voltage, "---")
        self.bind("status_hvsrc_current", self.status_hvsrc_current, "---")
        self.bind("status_hvsrc_output", self.status_hvsrc_output, "---")

        self.status_panel.append(ui.GroupBox(
            title="HV Source Status",
            layout=ui.Column(
                ui.Row(
                    ui.Column(
                        ui.Label("Voltage"),
                        self.status_hvsrc_voltage
                    ),
                    ui.Column(
                        ui.Label("Current"),
                        self.status_hvsrc_current
                    ),
                    ui.Column(
                        ui.Label("Output"),
                        self.status_hvsrc_output
                    )
                )
            )
        ))

        self.control_tabs.append(ui.Tab(
            title="HV Source",
            layout=ui.Row(
                ui.GroupBox(
                    title="Filter",
                    layout=ui.Column(
                        self.hvsrc_filter_enable,
                        self.hvsrc_filter_count_label,
                        self.hvsrc_filter_count,
                        self.hvsrc_filter_type_label,
                        self.hvsrc_filter_type,
                        ui.Spacer()
                    )
                ),
                ui.GroupBox(
                    title="Source Voltage Range",
                    layout=ui.Column(
                        self.hvsrc_source_voltage_autorange_enable,
                        ui.Label(text="Range"),
                        self.hvsrc_source_voltage_range,
                        ui.Spacer()
                    )
                ),
                ui.GroupBox(
                    title="Options",
                    layout=ui.Column(
                        ui.Label(text="Sense Mode"),
                        self.hvsrc_sense_mode,
                        ui.Label(text="Route Termination"),
                        self.hvsrc_route_termination,
                        ui.Spacer()
                    )
                ),
                stretch=(1, 1, 1)
            )
        ))

        def handler(state):
            if 'hvsrc_voltage' in state:
                value = state.get('hvsrc_voltage')
                self.status_hvsrc_voltage.value = format_metric(value, "V")
            if 'hvsrc_current' in state:
                value = state.get('hvsrc_current')
                self.status_hvsrc_current.value = format_metric(value, "A")
            if 'hvsrc_output' in state:
                labels = {False: "OFF", True: "ON", None: "---"}
                self.status_hvsrc_output.value = labels[state.get('hvsrc_output')]

        self.state_handlers.append(handler)

class VSourceMixin:
    """Mixin class providing default controls and status for V Source."""

    def register_hvsource(self):
        self.vsrc_sense_mode = ui.ComboBox(items=["local", "remote"])

        def toggle_vsrc_filter(enabled):
            self.vsrc_filter_count.enabled = enabled
            self.vsrc_filter_count_label.enabled = enabled
            self.vsrc_filter_type.enabled = enabled
            self.vsrc_filter_type_label.enabled = enabled

        self.vsrc_filter_enable = ui.CheckBox(text="Enable", changed=toggle_vsrc_filter)
        self.vsrc_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.vsrc_filter_count_label = ui.Label(text="Count")
        self.vsrc_filter_type = ui.ComboBox(items=["repeat", "moving"])
        self.vsrc_filter_type_label = ui.Label(text="Type")

        toggle_vsrc_filter(False)

        self.bind("vsrc_sense_mode", self.vsrc_sense_mode, "local")
        self.bind("vsrc_filter_enable", self.vsrc_filter_enable, False)
        self.bind("vsrc_filter_count", self.vsrc_filter_count, 10)
        self.bind("vsrc_filter_type", self.vsrc_filter_type, "repeat")

        self.status_vsrc_voltage = ui.Text(value="---", readonly=True)
        self.status_vsrc_current = ui.Text(value="---", readonly=True)
        self.status_vsrc_output = ui.Text(value="---", readonly=True)

        self.bind("status_vsrc_voltage", self.status_vsrc_voltage, "---")
        self.bind("status_vsrc_current", self.status_vsrc_current, "---")
        self.bind("status_vsrc_output", self.status_vsrc_output, "---")

        self.status_panel.append(ui.GroupBox(
            title="V Source Status",
            layout=ui.Column(
                ui.Row(
                    ui.Column(
                        ui.Label("Voltage"),
                        self.status_vsrc_voltage
                    ),
                    ui.Column(
                        ui.Label("Current"),
                        self.status_vsrc_current
                    ),
                    ui.Column(
                        ui.Label("Output"),
                        self.status_vsrc_output
                    )
                )
            )
        ))

        self.control_tabs.append(ui.Tab(
            title="V Source",
            layout=ui.Row(
                ui.GroupBox(
                    title="Filter",
                    layout=ui.Column(
                        self.vsrc_filter_enable,
                        self.vsrc_filter_count_label,
                        self.vsrc_filter_count,
                        self.vsrc_filter_type_label,
                        self.vsrc_filter_type,
                        ui.Spacer()
                    )
                ),
                ui.GroupBox(
                    title="Options",
                    layout=ui.Column(
                        ui.Label(text="Sense Mode"),
                        self.vsrc_sense_mode,
                        ui.Spacer()
                    )
                ),
                ui.Spacer(),
                stretch=(1, 1, 1)
            )
        ))

        def handler(state):
            if 'vsrc_voltage' in state:
                value = state.get('vsrc_voltage')
                self.status_vsrc_voltage.value = format_metric(value, "V")
            if 'vsrc_current' in state:
                value = state.get('vsrc_current')
                self.status_vsrc_current.value = format_metric(value, "A")
            if 'vsrc_output' in state:
                self.status_vsrc_output.value = state.get('vsrc_output') or '---'

        self.state_handlers.append(handler)

class ElectrometerMixin:
    """Mixin class providing default controls and status for Electrometer."""

    def register_electrometer(self):
        def toggle_elm_filter(enabled):
            self.elm_filter_count.enabled = enabled
            self.elm_filter_count_label.enabled = enabled
            self.elm_filter_type.enabled = enabled
            self.elm_filter_type_label.enabled = enabled

        self.elm_filter_enable = ui.CheckBox(text="Enable", changed=toggle_elm_filter)
        self.elm_filter_count = ui.Number(minimum=0, maximum=100, decimals=0)
        self.elm_filter_count_label = ui.Label(text="Count")
        self.elm_filter_type = ui.ComboBox(items=["repeat", "moving"])
        self.elm_filter_type_label = ui.Label(text="Type")

        self.elm_zero_correction = ui.CheckBox(text="Zero Correction")
        self.elm_integration_rate = ui.Number(minimum=0, maximum=100.0, decimals=2, suffix="Hz")

        def toggle_elm_current_autorange(enabled):
            self.elm_current_range.enabled = not enabled
            self.elm_current_autorange_minimum.enabled = enabled
            self.elm_current_autorange_maximum.enabled = enabled

        self.elm_current_range = ui.Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_enable = ui.CheckBox(text="Enable", changed=toggle_elm_current_autorange)
        self.elm_current_autorange_minimum = ui.Metric(minimum=0, decimals=3, prefixes='munp', unit="A")
        self.elm_current_autorange_maximum = ui.Metric(minimum=0, decimals=3, prefixes='munp', unit="A")

        toggle_elm_filter(False)
        toggle_elm_current_autorange(False)

        self.bind("elm_filter_enable", self.elm_filter_enable, False)
        self.bind("elm_filter_count", self.elm_filter_count, 10)
        self.bind("elm_filter_type", self.elm_filter_type, "repeat")
        self.bind("elm_zero_correction", self.elm_zero_correction, False)
        self.bind("elm_integration_rate", self.elm_integration_rate, 50.0)
        self.bind("elm_current_range", self.elm_current_range, 20e-12, unit="A")
        self.bind("elm_current_autorange_enable", self.elm_current_autorange_enable, False)
        self.bind("elm_current_autorange_minimum", self.elm_current_autorange_minimum, 2.0E-11, unit="A")
        self.bind("elm_current_autorange_maximum", self.elm_current_autorange_maximum, 2.0E-2, unit="A")

        self.status_elm_current = ui.Text(value="---", readonly=True)

        self.bind("status_elm_current", self.status_elm_current, "---")

        self.status_panel.append(ui.GroupBox(
            title="Electrometer Status",
            layout=ui.Column(
                ui.Row(
                    ui.Column(
                        ui.Label("Current"),
                        self.status_elm_current
                    ),
                    ui.Spacer(),
                    stretch=(1, 2)
                )
            )
        ))

        self.control_tabs.append(ui.Tab(
            title="Electrometer",
            layout=ui.Row(
                ui.GroupBox(
                    title="Filter",
                    layout=ui.Column(
                        self.elm_filter_enable,
                        self.elm_filter_count_label,
                        self.elm_filter_count,
                        self.elm_filter_type_label,
                        self.elm_filter_type,
                        ui.Spacer()
                    )
                ),
                ui.Column(
                    ui.GroupBox(
                        title="Range",
                        layout=ui.Column(
                            ui.Label(text="Current Range"),
                            self.elm_current_range,
                        )
                    ),
                    ui.GroupBox(
                        title="Auto Range",
                        layout=ui.Column(
                            self.elm_current_autorange_enable,
                            ui.Label(text="Minimum Current"),
                            self.elm_current_autorange_minimum,
                            ui.Label(text="Maximum Current"),
                            self.elm_current_autorange_maximum,
                            ui.Spacer()
                        )
                    )
                ),
                ui.GroupBox(
                    title="Options",
                    layout=ui.Column(
                        self.elm_zero_correction,
                        ui.Label(text="Integration Rate"),
                        self.elm_integration_rate,
                        ui.Spacer()
                    )
                ),
                ui.Spacer(),
                stretch=(1, 1, 1)
            )
        ))

        def handler(state):
            if 'elm_current' in state:
                value = state.get('elm_current')
                self.status_elm_current.value = format_metric(value, "A")
        self.state_handlers.append(handler)

class LCRMixin:
    """Mixin class providing default controls and status for LCR Meter."""

    def register_lcr(self):
        def change_lcr_open_correction_mode(mode):
            self.lcr_open_correction_channel.enabled = mode == "multi"

        self.lcr_integration_time = ui.ComboBox(items=["short", "medium", "long"])
        self.lcr_averaging_rate = ui.Number(minimum=1, maximum=256, decimals=0)
        self.lcr_auto_level_control = ui.CheckBox(text="Auto Level Control")
        self.lcr_soft_filter = ui.CheckBox(text="Filter STD/mean < 0.005")
        self.lcr_open_correction_mode = ui.ComboBox(items=["single", "multi"], changed=change_lcr_open_correction_mode)
        self.lcr_open_correction_channel = ui.Number(minimum=0, maximum=127, decimals=0)

        change_lcr_open_correction_mode(self.lcr_open_correction_mode.current)

        self.bind("lcr_integration_time", self.lcr_integration_time, "medium")
        self.bind("lcr_averaging_rate", self.lcr_averaging_rate, 1)
        self.bind("lcr_auto_level_control", self.lcr_auto_level_control, True)
        self.bind("lcr_soft_filter", self.lcr_soft_filter, True)
        self.bind("lcr_open_correction_mode", self.lcr_open_correction_mode, "single")
        self.bind("lcr_open_correction_channel", self.lcr_open_correction_channel, 0)

        self.status_lcr_voltage = ui.Text(value="---", readonly=True)
        self.status_lcr_current = ui.Text(value="---", readonly=True)
        self.status_lcr_output = ui.Text(value="---", readonly=True)

        self.bind("status_lcr_voltage", self.status_lcr_voltage, "---")
        self.bind("status_lcr_current", self.status_lcr_current, "---")
        self.bind("status_lcr_output", self.status_lcr_output, "---")

        self.status_panel.append(ui.GroupBox(
            title="LCR Status",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Voltage"),
                    self.status_lcr_voltage
                ),
                ui.Column(
                    ui.Label("Current"),
                    self.status_lcr_current
                ),
                ui.Column(
                    ui.Label("Output"),
                    self.status_lcr_output
                )
            )
        ))

        self.control_tabs.append(ui.Tab(
            title="LCR",
            layout=ui.Row(
                ui.GroupBox(
                    title="Open Correction",
                    layout=ui.Column(
                        ui.Label(text="Method"),
                        self.lcr_open_correction_mode,
                        ui.Label(text="Channel"),
                        self.lcr_open_correction_channel,
                        ui.Spacer()
                    )
                ),
                ui.GroupBox(
                    title="Options",
                    layout=ui.Column(
                        ui.Label(text="Integration Time"),
                        self.lcr_integration_time,
                        ui.Label(text="Averaging Rate"),
                        self.lcr_averaging_rate,
                        self.lcr_auto_level_control,
                        self.lcr_soft_filter,
                        ui.Spacer()
                    )
                ),
                ui.Spacer(),
                stretch=(1, 1, 1)
            )
        ))

        def handler(state):
            if 'lcr_voltage' in state:
                value = state.get('lcr_voltage')
                self.status_lcr_voltage.value = format_metric(value, "V")
            if 'lcr_current' in state:
                value = state.get('lcr_current')
                self.status_lcr_current.value = format_metric(value, "A")
            if 'lcr_output' in state:
                labels = {False: "OFF", True: "ON", None: "---"}
                self.status_lcr_output.value = labels[state.get('lcr_output')]

        self.state_handlers.append(handler)

class EnvironmentMixin:
    """Mixin class providing default controls and status for Environment box."""

    def register_environment(self):
        self.status_env_chuck_temperature = ui.Text(value="---", readonly=True)
        self.status_env_box_temperature = ui.Text(value="---", readonly=True)
        self.status_env_box_humidity = ui.Text(value="---", readonly=True)

        self.bind("status_env_chuck_temperature", self.status_env_chuck_temperature, "---")
        self.bind("status_env_box_temperature", self.status_env_box_temperature, "---")
        self.bind("status_env_box_humidity", self.status_env_box_humidity, "---")

        self.status_panel.append(ui.GroupBox(
            title="Environment Status",
            layout=ui.Column(
                ui.Row(
                    ui.Column(
                        ui.Label("Chuck temp."),
                        self.status_env_chuck_temperature
                    ),
                    ui.Column(
                        ui.Label("Box temp."),
                        self.status_env_box_temperature
                    ),
                    ui.Column(
                        ui.Label("Box humid."),
                        self.status_env_box_humidity
                    )
                )
            )
        ))

        def handler(state):
            if 'env_chuck_temperature' in state:
                value = state.get('env_chuck_temperature',)
                self.status_env_chuck_temperature.value = format_metric(value, "°C", decimals=2)
            if 'env_box_temperature' in state:
                value = state.get('env_box_temperature')
                self.status_env_box_temperature.value = format_metric(value, "°C", decimals=2)
            if 'env_box_humidity' in state:
                value = state.get('env_box_humidity')
                self.status_env_box_humidity.value = format_metric(value, "%rH", decimals=2)

        self.state_handlers.append(handler)

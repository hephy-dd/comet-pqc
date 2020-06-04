import copy
import logging
import os

import comet

from comet.process import ProcessMixin
from comet.settings import SettingsMixin
from comet.resource import ResourceMixin

from . import config

from .trees import SequenceTree
from .trees import ContactTreeItem
from .trees import MeasurementTreeItem

from .panels import IVRampPanel
from .panels import IVRampElmPanel
from .panels import IVRampBiasPanel
from .panels import IVRamp4WirePanel
from .panels import CVRampPanel
from .panels import CVRampAltPanel
from .panels import FrequencyScanPanel

from .driver import EnvironmentBox

class PanelStack(comet.Row):
    """Stack of measurement panels."""

    def __init__(self):
        super().__init__()
        self.append(IVRampPanel(visible=False))
        self.append(IVRampElmPanel(visible=False))
        self.append(IVRampBiasPanel(visible=False))
        self.append(CVRampPanel(visible=False))
        self.append(CVRampAltPanel(visible=False))
        self.append(IVRamp4WirePanel(visible=False))
        self.append(FrequencyScanPanel(visible=False))

    def store(self):
        for child in self.children:
            child.store()

    def unmount(self):
        for child in self.children:
            child.unmount()

    def clear_readings(self):
        for child in self.children:
            child.clear_readings()

    def hide(self):
        for child in self.children:
            child.visible = False

    def lock(self):
        for child in self.children:
            child.lock()

    def unlock(self):
        for child in self.children:
            child.unlock()

    def get(self, type):
        """Get panel by type."""
        for child in self.children:
            if child.type == type:
                return child
        return None

class Dashboard(comet.Row, ProcessMixin, SettingsMixin, ResourceMixin):

    def __init__(self):
        super().__init__()
        self.chuck_select = comet.ComboBox()
        self.sample_select = comet.ComboBox()
        self.sequence_select = comet.ComboBox(changed=self.on_load_sequence_tree)

        self.sample_text = comet.Text(
            value=self.settings.get("sample", "Unnamed"),
            changed=self.on_sample_changed
        )

        self.sample_fieldset = comet.GroupBox(
            title="Sample",
            layout=comet.Row(
                comet.Column(
                    comet.Label("Name"),
                    comet.Label("Chuck"),
                    comet.Label("Sample Type"),
                    comet.Label("Sequence")
                ),
                comet.Column(
                    self.sample_text,
                    self.chuck_select,
                    self.sample_select,
                    self.sequence_select
                ),
                stretch=(0, 1)
            )
        )

        self.sequence_tree = SequenceTree(selected=self.on_tree_selected)

        self.start_button = comet.Button(
            text="Start",
            tool_tip="Start measurement sequence.",
            clicked=self.on_sequence_start
        )

        self.autopilot_button = comet.Button(
            text="Autopilot",
            tool_tip="Run next measurement automatically.",
            checkable=True,
            checked=False,
            toggled=self.on_autopilot_toggled
        )

        self.continue_button = comet.Button(
            text="Continue",
            tool_tip="Run next measurement manually.",
            enabled=False
        )

        self.stop_button = comet.Button(
            text="Stop",
            tool_tip="Stop measurement sequence.",
            enabled=False,
            clicked=self.on_sequence_stop
        )

        self.sequence_fieldset = comet.GroupBox(
            title="Sequence",
            layout=comet.Column(
                self.sequence_tree,
                comet.Row(
                    self.start_button,
                    self.autopilot_button,
                    self.continue_button
                ),
                self.stop_button
            )
        )

        self.calibrate_button = comet.Button(
            text="Calibrate Table",
            tool_tip="Calibrate table.",
            clicked=self.on_calibrate_start
        )

        self.use_environ_checkbox = comet.CheckBox(
            text="Use Environment Box",
            tool_tip="Enable use of Environment Box controls and data.",
            changed=self.on_use_environ_changed,
            checked=self.settings.get("use_environ", True)
        )

        self.box_light_button = comet.Button(
            text="Box Light",
            enabled=self.use_environ_checkbox.checked,
            checkable=True,
            checked=False,
            clicked=self.on_box_light_clicked
        )

        self.microscope_light_button = comet.Button(
            text="Mic Light",
            enabled=self.use_environ_checkbox.checked,
            checkable=True,
            checked=False,
            toggled=self.on_microscope_light_toggled
        )

        self.probe_light_button = comet.Button(
            text="Probe Light",
            enabled=self.use_environ_checkbox.checked,
            checkable=True,
            checked=False,
            toggled=self.on_probe_light_toggled
        )

        self.controls_fieldset = comet.GroupBox(
            title="Controls",
            layout=comet.Column(
                self.use_environ_checkbox,
                comet.Row(
                    self.box_light_button,
                    self.microscope_light_button,
                    self.probe_light_button,
                    comet.Spacer(),
                    self.calibrate_button
                )
            )
        )

        self.output_text = comet.Text(
            value=self.settings.get("output_path", os.path.join(os.path.expanduser("~"), "PQC")),
            changed=self.on_output_changed
        )

        self.output_fieldset = comet.GroupBox(
            title="Output",
            layout=comet.Row(
                self.output_text,
                comet.Button(
                    text="...",
                    width=32,
                    clicked=self.on_select_output
                )
            )
        )

        self.control_widget = comet.Column(
            self.sample_fieldset,
            self.sequence_fieldset,
            self.controls_fieldset,
            self.output_fieldset,
            stretch=(0, 1, 0, 0)
        )

        self.panels = PanelStack()

        self.measure_restore_button = comet.Button(
            text="Restore Defaults",
            tool_tip="Restore default measurement parameters.",
            clicked=self.on_measure_restore
        )

        self.measure_run_button = comet.Button(
            text="Run",
            tool_tip="Run current measurement.",
            clicked=self.on_measure_run
        )

        self.measure_stop_button = comet.Button(
            text="Stop",
            tool_tip="Stop current measurement.",
            clicked=self.on_measure_stop,
            enabled=False
        )

        self.measure_controls = comet.Row(
            self.measure_restore_button,
            comet.Spacer(),
            self.measure_run_button,
            self.measure_stop_button,
            visible=False
        )

        self.measurement_tab = comet.Tab(
            title="Measurement",
            layout=comet.Column(
                self.panels,
                self.measure_controls,
                stretch=(1, 0)
            )
        )

        # self.environment_tab = comet.Tab(
        #     title="Environment",
        #     layout=comet.Column()
        # )

        self.matrix_model_text = comet.Text(readonly=True)
        self.matrix_channels_text = comet.Text(readonly=True)
        self.smu1_model_text = comet.Text(readonly=True)
        self.smu2_model_text = comet.Text(readonly=True)
        self.lcr_model_text = comet.Text(readonly=True)
        self.elm_model_text = comet.Text(readonly=True)
        self.env_model_text = comet.Text(readonly=True)
        self.env_box_temperature_text = comet.Text(readonly=True)
        self.env_box_humidity_text = comet.Text(readonly=True)
        self.env_chuck_temperature_text = comet.Text(readonly=True)
        self.env_lux_text = comet.Text(readonly=True)
        self.env_light_text = comet.Text(readonly=True)
        self.env_door_text = comet.Text(readonly=True)
        self.reload_status_button = comet.Button("&Reload", clicked=self.on_status_start)

        self.status_tab = comet.Tab(
            title="Status",
            layout=comet.Column(
                comet.GroupBox(
                    title="Matrix",
                    layout=comet.Column(
                        comet.Row(
                            comet.Label("Model:"),
                            self.matrix_model_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Closed channels:"),
                            self.matrix_channels_text,
                            stretch=(1, 7)
                        )
                    )
                ),
                comet.GroupBox(
                    title="SMU1",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.smu1_model_text,
                        stretch=(1, 7)
                    )
                ),
                comet.GroupBox(
                    title="SMU2",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.smu2_model_text,
                        stretch=(1, 7)
                    )
                ),
                comet.GroupBox(
                    title="LCRMeter",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.lcr_model_text,
                        stretch=(1, 7)
                    )
                ),
                comet.GroupBox(
                    title="Electrometer",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.elm_model_text,
                        stretch=(1, 7)
                    )
                ),
                comet.GroupBox(
                    title="Environment Box",
                    layout=comet.Column(
                        comet.Row(
                            comet.Label("Model:"),
                            self.env_model_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Box Temperat.:"),
                            self.env_box_temperature_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Box Humidity:"),
                            self.env_box_humidity_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Chuck Temperat.:"),
                            self.env_chuck_temperature_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Box Lux:"),
                            self.env_lux_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Box Light State:"),
                            self.env_light_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("Box Door State:"),
                            self.env_door_text,
                            stretch=(1, 7)
                        ),
                    )
                ),
                comet.Spacer(),
                self.reload_status_button
            )
        )

        self.summary_tab = comet.Tab(
            title="Summary",
            layout=comet.ScrollArea(
                layout=comet.Column(
                    comet.Spacer()
                )
            )
        )

        self.tab_widget = comet.Tabs(
            self.measurement_tab,
            # self.environment_tab,
            self.status_tab,
            self.summary_tab
        )

        self.append(self.control_widget)
        self.append(self.tab_widget)
        self.stretch = 4, 9


    def load_chucks(self):
        """Load available chuck configurations."""
        self.chuck_select.clear()
        for name, filename in sorted(config.list_configs(config.CHUCK_DIR)):
            self.chuck_select.append(config.load_chuck(filename))

    def load_samples(self):
        """Load available sample configurations."""
        self.sample_select.clear()
        for name, filename in sorted(config.list_configs(config.SAMPLE_DIR)):
            self.sample_select.append(config.load_sample(filename))

    def load_sequences(self):
        """Load available sequence configurations."""
        self.sequence_select.clear()
        for name, filename in sorted(config.list_configs(config.SEQUENCE_DIR)):
            self.sequence_select.append(config.load_sequence(filename))

    def create_output_dir(self, sample_name, sample_type):
        """Create new timestamp prefixed output directory."""
        base = self.output_text.value
        iso_timestamp = comet.make_iso()
        dirname = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}")
        output_dir = os.path.join(base, dirname)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    # Callbacks

    def on_sample_changed(self, value):
        self.settings["sample"] = value

    def on_load_sequence_tree(self, index):
        """Clears current sequence tree and loads new sequence tree from configuration."""
        self.panels.unmount()
        self.panels.hide()
        self.sequence_tree.clear()
        sequence = copy.deepcopy(self.sequence_select.current)
        for contact in sequence:
            self.sequence_tree.append(ContactTreeItem(contact))
        self.sequence_tree.fit()
        if len(self.sequence_tree):
            self.sequence_tree.current = self.sequence_tree[0]

    # Sequence control

    def on_tree_selected(self, item):
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        self.panels.hide()
        self.measure_controls.visible = False
        if isinstance(item, ContactTreeItem):
            pass
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            panel.visible = True
            panel.mount(item)
            self.measure_controls.visible = True
        # Show measurement tab
        self.tab_widget.current = self.measurement_tab

    def on_sequence_start(self):
        if not comet.show_question(
            title="Start sequence",
            text="Are you sure to start a measurement sequence?"
        ): return
        self.sample_fieldset.enabled = False
        self.calibrate_button.enabled = False
        self.use_environ_checkbox.enabled = False
        self.start_button.enabled = False
        self.autopilot_button.enabled = True
        self.continue_button.enabled = False
        self.stop_button.enabled = True
        self.measure_controls.enabled = False
        self.panels.lock()
        self.sequence_tree.lock()
        self.sequence_tree.reset()
        sample_name = self.sample_text.value
        sample_type = self.sample_select.current.name
        output_dir = self.create_output_dir(sample_name, sample_type)
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", sample_name)
        sequence.set("sample_type", sample_type)
        sequence.set("output_dir", output_dir)
        sequence.set("use_environ", self.use_environ_checkbox.checked)
        sequence.sequence_tree = self.sequence_tree
        sequence.start()

    def on_autopilot_toggled(self, state):
        sequence = self.processes.get("sequence")
        sequence.set("autopilot", state)

    def on_continue_measurement(self, measurement):
        def on_continue():
            if not comet.show_question(
                title="Continue sequence",
                text=f"Do you want to continue with {measurement.contact.name}, {measurement.name}?"
            ): return
            logging.info("Continuing sequence...")
            self.continue_button.enabled = False
            self.continue_button.clicked = None
            self.sequence_tree.current = measurement
            sequence = self.processes.get("sequence")
            sequence.set("continue_measurement", True)
        self.continue_button.enabled = True
        self.continue_button.clicked = on_continue

    def on_continue_contact(self, contact):
        comet.show_info(
            title=f"Contact {contact.name}",
            text=f"Please contact with {contact.name}."
        )
        sequence = self.processes.get("sequence")
        sequence.set("continue_contact", True)

    def on_measurement_state(self, item, state):
        item.state = state

    def on_sequence_stop(self):
        self.stop_button.enabled = False
        self.autopilot_button.enabled = False
        self.continue_button.enabled = False
        sequence = self.processes.get("sequence")
        sequence.stop()

    def on_sequence_finished(self):
        self.sample_fieldset.enabled = True
        self.calibrate_button.enabled = True
        self.use_environ_checkbox.enabled = True
        self.start_button.enabled = True
        self.autopilot_button.enabled = True
        self.continue_button.enabled = False
        self.stop_button.enabled = False
        self.measure_controls.enabled = True
        self.panels.unlock()
        self.sequence_tree.unlock()
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", None)
        sequence.set("output_dir", None)

    # Table calibration

    def on_calibrate_start(self):
        if not comet.show_question(
            title="Calibrate table",
            text="Are you sure to calibrate the table?"
        ): return
        self.sample_fieldset.enabled = False
        self.calibrate_button.enabled = False
        self.start_button.enabled = False
        self.autopilot_button.enabled = False
        self.continue_button.enabled = False
        self.stop_button.enabled = False
        self.enabled = False
        calibrate = self.processes.get("calibrate")
        calibrate.start()

    def on_calibrate_finished(self):
        calibrate = self.processes.get("calibrate")
        if calibrate.get("success", False):
            comet.show_info(title="Success", text="Calibrated table successfully.")
        self.sample_fieldset.enabled = True
        self.calibrate_button.enabled = True
        self.start_button.enabled = True
        self.autopilot_button.enabled = True
        self.continue_button.enabled = False
        self.stop_button.enabled = False
        self.enabled = True

    def on_use_environ_changed(self, state):
        self.settings["use_environ"] = state
        self.box_light_button.enabled = state
        self.microscope_light_button.enabled = state
        self.probe_light_button.enabled = state

    def on_box_light_clicked(self):
        # TODO run in thread
        self.enabled = False
        state = self.box_light_button.checked
        try:
            with self.resources.get("environ") as environ_resource:
                environ = EnvironmentBox(environ_resource)
                environ.box_light = state
        except Exception as exc:
            comet.show_exception(exc)
        self.enabled = True

    def on_microscope_light_toggled(self, state):
        # TODO run in thread
        self.enabled = False
        try:
            with self.resources.get("environ") as environ_resource:
                environ = EnvironmentBox(environ_resource)
                environ.microscope_light = state
        except Exception as exc:
            comet.show_exception(exc)
        self.enabled = True

    def on_probe_light_toggled(self, state):
        # TODO run in thread
        self.enabled = False
        try:
            with self.resources.get("environ") as environ_resource:
                environ = EnvironmentBox(environ_resource)
                environ.probecard_light = state
        except Exception as exc:
            comet.show_exception(exc)
        self.enabled = True

    def on_output_changed(self, value):
        self.settings["output_path"] = value

    def on_select_output(self):
        value = comet.directory_open(
            title="Output",
            path=self.output_text.value
        )
        if value:
            self.output_text.value = value

    # Measurement control

    def on_measure_restore(self):
        if not comet.show_question(
            title="Restore Defaults",
            text="Do you want to restore to default parameters?"
        ): return
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.restore()

    def on_measure_run(self):
        if not comet.show_question(
            title="Run Measurement",
            text="Do you want to run the current selected measurement?"
        ): return
        self.calibrate_button.enabled = False
        self.use_environ_checkbox.enabled = False
        self.measure_restore_button.enabled = False
        self.measure_run_button.enabled = False
        self.measure_stop_button.enabled = True
        self.sample_fieldset.enabled = False
        self.sequence_fieldset.enabled = False
        self.output_fieldset.enabled = False
        self.panels.lock()
        self.sequence_tree.lock()
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.store()
        # TODO
        panel.clear_readings()
        sample_name = self.sample_text.value
        sample_type = self.sample_select.current.name
        output_dir = self.output_text.value
        measure = self.processes.get("measure")
        measure.set("sample_name", sample_name)
        measure.set("sample_type", sample_type)
        measure.set("output_dir", output_dir)
        measure.set("use_environ", self.use_environ_checkbox.checked)
        measure.measurement_item = measurement
        measure.reading = panel.append_reading
        measure.update = panel.update_readings
        measure.state = panel.state
        # TODO
        measure.start()

    def on_measure_stop(self):
        self.measure_restore_button.enabled = False
        self.measure_run_button.enabled = False
        self.measure_stop_button.enabled = False
        measure = self.processes.get("measure")
        measure.stop()

    def on_measure_finished(self):
        self.calibrate_button.enabled = True
        self.use_environ_checkbox.enabled = True
        self.measure_restore_button.enabled = True
        self.measure_run_button.enabled = True
        self.measure_stop_button.enabled = False
        self.sample_fieldset.enabled = True
        self.sequence_fieldset.enabled = True
        self.output_fieldset.enabled = True
        self.panels.unlock()
        measure = self.processes.get("measure")
        measure.reading = lambda data: None
        self.sequence_tree.unlock()

    def on_status_start(self):
        self.enabled = False
        self.matrix_model_text.value = ""
        self.matrix_channels_text.value = ""
        self.smu1_model_text.value = ""
        self.smu2_model_text.value = ""
        self.lcr_model_text.value = ""
        self.elm_model_text.value = ""
        self.env_model_text.value = ""
        self.env_box_temperature_text.value = ""
        self.env_box_humidity_text.value = ""
        self.env_chuck_temperature_text.value = ""
        self.env_lux_text.value = ""
        self.env_light_text.value = ""
        self.env_door_text.value = ""
        self.reload_status_button.enabled = False
        status = self.processes.get("status")
        status.start()

    def on_status_finished(self):
        self.enabled = True
        self.reload_status_button.enabled = True
        status = self.processes.get("status")
        self.matrix_model_text.value = status.get("matrix_model") or "n/a"
        self.matrix_channels_text.value = status.get("matrix_channels")
        self.smu1_model_text.value = status.get("smu1_model") or "n/a"
        self.smu2_model_text.value = status.get("smu2_model") or "n/a"
        self.lcr_model_text.value = status.get("lcr_model") or "n/a"
        self.elm_model_text.value = status.get("elm_model") or "n/a"
        self.env_model_text.value = status.get("env_model") or "n/a"
        pc_data = status.get("env_pc_data")
        if pc_data:
            self.env_box_temperature_text.value = f"{pc_data.box_temperature:.1f} °C"
            self.env_box_humidity_text.value = f"{pc_data.box_humidity:.1f} %rH"
            self.env_chuck_temperature_text.value = f"{pc_data.chuck_block_temperature:.1f} °C"
            self.env_lux_text.value =  f"{pc_data.box_lux:.1f} lux"
            self.env_light_text.value = "ON" if pc_data.box_light_state else "OFF"
            self.env_door_text.value = "OPEN" if pc_data.box_door_state else "CLOSED"

    # Menu action callbacks

    def on_import_sequence(self):
        filename = comet.filename_open(
            title="Import Sequence",
            filter="YAML (*.yaml *.yml)"
        )
        if filename:
            try:
                sequence = config.load_sequence(filename)
            except Exception as e:
                logging.error(e)
                comet.show_error(
                    title="Import Sequence Error",
                    text=e.message if hasattr(e, "message") else format(e),
                    details=format(e)
                )
                return
            # backup callback
            on_changed = self.sequence_select.changed
            self.sequence_select.changed = None
            for item in self.sequence_select.values:
                if item.id == sequence.id or item.name == sequence.name:
                    result = comet.show_question(
                        title="Sequence already loaded",
                        text=f"Do you want to replace already loaded sequence '{sequence.name}'?"
                    )
                    if result:
                        self.sequence_select.remove(item)
                    else:
                        return
            self.sequence_select.append(sequence)
            # Restore callback
            self.sequence_select.changed = on_changed
            self.sequence_select.current = sequence

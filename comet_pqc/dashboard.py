import copy
import datetime
import logging
import os
import webbrowser

import yaml

from qutie.qutie import QtCore, QtGui
from qutie import Timer

import comet
from comet import ui

from comet.process import ProcessMixin
from comet.settings import SettingsMixin
from comet.resource import ResourceMixin
from comet.driver.corvus import Venus1

from . import config

from .sequence import SequenceTree
from .sequence import ContactTreeItem
from .sequence import MeasurementTreeItem
from .sequence import SequenceManager

from .components import ToggleButton
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .dialogs import TableControlDialog
from .dialogs import StartSequenceDialog

from .tabs import EnvironmentTab
from .tabs import MeasurementTab
from .tabs import StatusTab
from .tabs import SummaryTab
from .logwindow import LogWidget
from .formatter import CSVFormatter
from .utils import make_path, handle_exception

SUMMARY_FILENAME = "summary.csv"

TABLE_UNITS = {
    1: comet.ureg('um'),
    2: comet.ureg('mm'),
    3: comet.ureg('cm'),
    4: comet.ureg('m'),
    5: comet.ureg('inch'),
    6: comet.ureg('mil'),
}

class Dashboard(ui.Row, ProcessMixin, SettingsMixin, ResourceMixin):

    environment_poll_interval = 1.0

    def __init__(self):
        super().__init__()

        self.sample_name_text = ui.Text(
            editing_finished=self.on_sample_name_changed
        )
        self.sample_type_text = ui.Text(
            editing_finished=self.on_sample_type_changed
        )
        self.sequence_combobox = ui.ComboBox(
            changed=self.on_load_sequence_tree
        )
        self.sequence_manager_button = ui.Button(
            icon=make_path('assets', 'icons', 'gear.svg'),
            tool_tip="Open sequence manager",
            width=24,
            clicked=self.on_sequence_manager_clicked
        )

        self.sample_groupbox = ui.GroupBox(
            title="Sample",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Name"),
                    ui.Label("Type"),
                    ui.Label("Sequence")
                ),
                ui.Column(
                    self.sample_name_text,
                    self.sample_type_text,
                    ui.Row(
                        self.sequence_combobox,
                        self.sequence_manager_button,
                        stretch=(1, 0)
                    ),
                ),
                stretch=(0, 1)
            )
        )

        self.sequence_tree = SequenceTree(
            selected=self.on_tree_selected,
            double_clicked=self.on_tree_double_clicked
        )
        self.sequence_tree.qt.setExpandsOnDoubleClick(False)
        self.sequence_tree.minimum_width = 360

        self.start_button = ui.Button(
            text="Start",
            tool_tip="Start measurement sequence.",
            clicked=self.on_start,
            stylesheet="QPushButton:enabled{color:green;font-weight:bold;}"
        )

        self.stop_button = ui.Button(
            text="Stop",
            tool_tip="Stop measurement sequence.",
            enabled=False,
            clicked=self.on_stop,
            stylesheet="QPushButton:enabled{color:red;font-weight:bold;}"
        )

        self.reset_button = ui.Button(
            text="Reset",
            tool_tip="Reset measurement sequence state.",
            clicked=self.on_reset_sequence_state
        )

        self.sequence_groupbox = ui.GroupBox(
            title="Sequence",
            layout=ui.Column(
                self.sequence_tree,
                ui.Row(
                    self.start_button,
                    self.stop_button,
                    self.reset_button
                )
            )
        )

        # Environment Controls

        self.box_laser_button = ToggleButton(
            text="Laser",
            tool_tip="Toggle laser",
            checkable=True,
            checked=False,
            clicked=self.on_box_laser_clicked
        )

        self.box_light_button = ToggleButton(
            text="Box Light",
            tool_tip="Toggle box light",
            checkable=True,
            checked=False,
            clicked=self.on_box_light_clicked
        )

        self.microscope_light_button = ToggleButton(
            text="Mic Light",
            tool_tip="Toggle microscope light",
            checkable=True,
            checked=False,
            clicked=self.on_microscope_light_clicked
        )

        self.microscope_camera_button = ToggleButton(
            text="Mic Cam",
            tool_tip="Toggle microscope camera power",
            checkable=True,
            checked=False,
            clicked=self.on_microscope_camera_clicked
        )

        self.microscope_control_button = ToggleButton(
            text="Mic Ctrl",
            tool_tip="Toggle microscope control",
            checkable=True,
            checked=False,
            clicked=self.on_microscope_control_clicked
        )

        self.probecard_light_button = ToggleButton(
            text="PC Light",
            tool_tip="Toggle probe card light",
            checkable=True,
            checked=False,
            clicked=self.on_probecard_light_clicked
        )

        self.probecard_camera_button = ToggleButton(
            text="PC Cam",
            tool_tip="Toggle probe card camera power",
            checkable=True,
            checked=False,
            clicked=self.on_probecard_camera_clicked
        )

        self.pid_control_button = ToggleButton(
            text="PID Control",
            tool_tip="Toggle PID control",
            checkable=True,
            checked=False,
            clicked=self.on_pid_control_clicked
        )

        self.environment_groupbox = ui.GroupBox(
            title="Environment Box",
            checkable=True,
            toggled=self.on_environment_groupbox_toggled,
            layout=ui.Column(
                ui.Row(
                    self.box_laser_button,
                    self.box_light_button,
                    self.microscope_light_button,
                    self.probecard_light_button
                ),
                ui.Row(
                    self.microscope_camera_button,
                    self.probecard_camera_button,
                    self.microscope_control_button,
                    self.pid_control_button
                )
            )
        )

        # Table controls

        self.table_joystick_button = ToggleButton(
            text="Joystick",
            tool_tip="Toggle table joystick",
            checkable=True,
            checked=False,
            clicked=self.on_table_joystick_clicked
        )

        self.table_control_button = ui.Button(
            text="Control...",
            tool_tip="Virtual table joystick controls.",
            clicked=self.on_table_controls_start
        )

        self.table_groupbox = ui.GroupBox(
            title="Table",
            checkable=True,
            toggled=self.on_table_groupbox_toggled,
            layout=ui.Row(
                self.table_joystick_button,
                ui.Spacer(vertical=False),
                self.table_control_button
            )
        )

        # Operator

        self.operator_widget = OperatorWidget()
        self.operator_widget.load_settings()
        self.operator_groupbox = ui.GroupBox(
            title="Operator",
            layout=self.operator_widget
        )

        # Working directory

        self.output_widget = WorkingDirectoryWidget()

        self.output_groupbox = ui.GroupBox(
            title="Working Directory",
            layout=self.output_widget
        )

        # Controls

        self.control_widget = ui.Column(
            self.sample_groupbox,
            self.sequence_groupbox,
            self.environment_groupbox,
            self.table_groupbox,
            ui.Row(
                self.operator_groupbox,
                self.output_groupbox,
                stretch=(3, 7)
            ),
            stretch=(0, 1, 0, 0)
        )

        # Tabs

        self.measurement_tab = MeasurementTab(restore=self.on_measure_restore)
        self.environment_tab = EnvironmentTab()
        self.status_tab = StatusTab(reload=self.on_status_start)
        self.summary_tab = SummaryTab()

        self.panels = self.measurement_tab.panels

        self.log_widget = LogWidget()
        self.log_widget.add_logger(logging.getLogger())

        self.logging_tab = ui.Tab(
            title="Logs",
            layout=self.log_widget
        )

        # Tabs

        self.tab_widget = ui.Tabs(
            self.measurement_tab,
            self.environment_tab,
            self.status_tab,
            self.logging_tab,
            self.summary_tab
        )

        # Layout

        self.append(self.control_widget)
        self.append(self.tab_widget)
        self.stretch = 4, 9

        # Experimental

        # Install timer to update environment controls
        self.environment_timer = Timer(timeout=self.sync_environment_controls)
        self.environment_timer.start(self.environment_poll_interval)

    @handle_exception
    def load_settings(self):
        sample_name = self.settings.get("sample_name", "Unnamed")
        self.sample_name_text.value = sample_name
        sample_type = self.settings.get("sample_type", "")
        self.sample_type_text.value = sample_type
        use_environ = self.settings.get("use_environ", False)
        self.environment_groupbox.checked = use_environ
        use_table =  self.settings.get("use_table", False)
        self.table_groupbox.checked = use_table
        self.operator_widget.load_settings()
        self.output_widget.load_settings()


    @handle_exception
    def store_settings(self):
        self.settings["sample_name"] = self.sample_name()
        self.settings["sample_type"] = self.sample_type()
        self.settings["use_environ"] = self.use_environment()
        self.settings["use_table"] = self.use_table()
        self.operator_widget.store_settings()
        self.output_widget.store_settings()

    @handle_exception
    def load_sequences(self):
        """Load available sequence configurations."""
        # Mute events
        self.sequence_combobox.changed = None
        try:
            current_sequence_id = self.settings.get("current_sequence_id")
            self.sequence_combobox.clear()
            for name, filename in sorted(config.list_configs(config.SEQUENCE_DIR)):
                sequence = config.load_sequence(filename)
                sequence.name = f"{sequence.name} (built-in)"
                self.sequence_combobox.append(sequence)
            custom_sequences = []
            for filename in self.settings.get("custom_sequences") or []:
                if os.path.exists(filename):
                    try:
                        sequence = config.load_sequence(filename)
                    except yaml.parser.ParserError as exc:
                        raise RuntimeError(f"Failed to load configuration file {filename}:\n{exc}")
                    sequence.name = f"{sequence.name} (user)"
                    self.sequence_combobox.append(sequence)
                    custom_sequences.append(filename)
            self.settings["custom_sequences"] = custom_sequences
        finally:
            # Restore events
            self.sequence_combobox.changed=self.on_load_sequence_tree
            for sequence in self.sequence_combobox:
                if sequence.id == current_sequence_id:
                    self.sequence_combobox.current = sequence
                    self.on_load_sequence_tree(sequence.id)
                    break

    def sample_name(self):
        """Return sample name."""
        return self.sample_name_text.value.strip()

    def sample_type(self):
        """Return sample type."""
        return self.sample_type_text.value.strip()

    def table_position(self):
        """Return table position in millimeters as tuple. If table not available
        return (0., 0., 0.).
        """
        if self.use_table():
            try:
                with self.resources.get("table") as table_resource:
                    table = Venus1(table_resource)
                    x, y, z = table.pos
                    x *= TABLE_UNITS.get(table.x.unit)
                    y *= TABLE_UNITS.get(table.y.unit)
                    z *= TABLE_UNITS.get(table.z.unit)
                return x.to('mm').m, y.to('mm').m, z.to('mm').m
            except:
                logging.warning("Failed to read table position.")
        return (0., 0., 0.)

    def use_environment(self):
        """Return True if environment box enabled."""
        return self.environment_groupbox.checked

    def use_table(self):
        """Return True if table control enabled."""
        return self.table_groupbox.checked

    def operator(self):
        """Return current operator."""
        return self.operator_widget.operator_combo_box.qt.currentText().strip()

    def output_dir(self):
        """Return output path."""
        base = os.path.realpath(self.output_widget.current_location)
        sample_name = self.sample_name()
        return os.path.join(base, sample_name)

    def create_output_dir(self):
        """Create output directory for sample if not exists, return directory
        path.
        """
        output_dir = self.output_dir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def write_logfiles(self):
        return bool(self.settings.get("write_logfiles", True))

    def export_json(self):
        return bool(self.settings.get("export_json", True))

    def export_txt(self):
        return bool(self.settings.get("export_txt", True))

    # Callbacks

    def on_sample_name_changed(self):
        sample_name = self.sample_name()
        if self.settings.get("sample_name") != sample_name:
            self.settings["sample_name"] = sample_name
            self.on_reset_sequence_state()

    def on_sample_type_changed(self):
        sample_type = self.sample_type()
        if self.settings.get("sample_type") != sample_type:
            self.settings["sample_type"] = sample_type
            self.on_reset_sequence_state()

    def on_reset_sequence_state(self):
        # Reset tree
        sequence = self.sequence_combobox.current
        if sequence:
            self.on_load_sequence_tree(sequence.id)

    def on_load_sequence_tree(self, index):
        """Clears current sequence tree and loads new sequence tree from configuration."""
        self.panels.unmount()
        self.panels.hide()
        self.sequence_tree.clear()
        sequence = copy.deepcopy(self.sequence_combobox.current)
        for contact in sequence:
            self.sequence_tree.append(ContactTreeItem(contact))
        self.sequence_tree.fit()
        if len(self.sequence_tree):
            self.sequence_tree.current = self.sequence_tree[0]
        self.settings["current_sequence_id"] = sequence.id

    def on_sequence_manager_clicked(self):
        dialog = SequenceManager()
        custom_sequences = sorted(self.settings.get("custom_sequences"))
        dialog.load_settings()
        dialog.run()
        dialog.store_settings()
        # Re-load only on changes
        if custom_sequences != sorted(self.settings.get("custom_sequences")):
            self.load_sequences()

    def lock_controls(self):
        """Lock dashboard controls."""
        self.sample_groupbox.enabled = False
        self.environment_groupbox.enabled = False
        self.table_groupbox.enabled = False
        self.sequence_tree.double_clicked = None
        self.start_button.enabled = False
        self.stop_button.enabled = True
        self.reset_button.enabled = False
        self.output_groupbox.enabled = False
        self.operator_groupbox.enabled = False
        self.measurement_tab.lock()
        self.sequence_tree.lock()
        self.status_tab.lock()

    def unlock_controls(self):
        """Unlock dashboard controls."""
        self.sample_groupbox.enabled = True
        self.environment_groupbox.enabled = True
        self.table_groupbox.enabled = True
        self.sequence_tree.double_clicked = self.on_tree_double_clicked
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self.reset_button.enabled = True
        self.output_groupbox.enabled = True
        self.operator_groupbox.enabled = True
        self.measurement_tab.unlock()
        self.sequence_tree.unlock()
        self.status_tab.unlock()

    # Sequence control

    def on_tree_selected(self, item):
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        self.panels.hide()
        self.measurement_tab.measure_controls.visible = False
        if isinstance(item, ContactTreeItem):
            pass
        if isinstance(item, MeasurementTreeItem):
            self.panels.unmount()
            panel = self.panels.get(item.type)
            panel.visible = True
            panel.mount(item)
            self.measurement_tab.measure_controls.visible = True
        # Show measurement tab
        self.tab_widget.current = self.measurement_tab

    def on_tree_double_clicked(self, item, index):
        self.on_start()

    @handle_exception
    def on_start(self):
        # Create output directory
        self.create_output_dir()
        current_item = self.sequence_tree.current
        if isinstance(current_item, MeasurementTreeItem):
            contact_item = current_item.contact
            if not ui.show_question(
                title="Run Measurement",
                text=f"Are you sure to run measurement '{current_item.name}' for '{contact_item.name}'?"
            ): return
            self.on_measure_run()
        elif isinstance(current_item, ContactTreeItem):
            contact_item = current_item
            def verify_start():
                dialog = StartSequenceDialog(contact_item)
                self.operator_widget.store_settings()
                self.output_widget.store_settings()
                dialog.load_settings()
                if not dialog.run():
                    return False
                dialog.store_settings()
                self.operator_widget.load_settings()
                self.output_widget.load_settings()
                return True
            if verify_start():
                self.on_sequence_start(contact_item)

    def on_sequence_start(self, contact_item):
        self.switch_off_lights()
        self.sync_environment_controls()
        self.lock_controls()
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", self.sample_name())
        sequence.set("sample_type", self.sample_type())
        sequence.set("table_position", self.table_position())
        sequence.set("operator", self.operator())
        sequence.set("output_dir", self.output_dir())
        sequence.set("write_logfiles", self.write_logfiles())
        sequence.set("use_environ", self.use_environment())
        sequence.set("use_table", self.use_table())
        sequence.set("serialize_json", self.export_json())
        sequence.set("serialize_txt", self.export_txt())
        sequence.contact_item = contact_item
        # sequence.sequence_tree = self.sequence_tree
        def show_measurement(item):
            item.selectable = True
            item.series.clear()
            item[0].color = 'blue'
            self.panels.unmount()
            self.panels.hide()
            self.panels.clear_readings()
            panel = self.panels.get(item.type)
            panel.visible = True
            panel.mount(item)
            sequence.reading = panel.append_reading
            sequence.update = panel.update_readings
            sequence.append_analysis = panel.append_analysis
            sequence.state = panel.state
        def hide_measurement(item):
            item.selectable = False
            item[0].color = None
        sequence.show_measurement = show_measurement
        sequence.hide_measurement = hide_measurement
        sequence.push_summary = self.on_push_summary
        sequence.start()

    def on_measurement_state(self, item, state=None, quality=None):
        item.state = state
        item.quality = quality
        self.sequence_tree.fit()

    def on_save_to_image(self, item, filename):
        plot_png = self.settings.get("png_plots") or False
        panel = self.panels.get(item.type)
        if panel and plot_png:
            panel.save_to_image(filename)

    def on_stop(self):
        self.stop_button.enabled = False
        sequence = self.processes.get("sequence")
        sequence.stop()
        measure = self.processes.get("measure")
        measure.stop()

    def on_sequence_finished(self):
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", None)
        sequence.set("output_dir", None)
        sequence.set("contact_item", None)
        self.sync_environment_controls()
        self.unlock_controls()

    # Measurement control

    def on_measure_restore(self):
        if not ui.show_question(
            title="Restore Defaults",
            text="Do you want to restore to default parameters?"
        ): return
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.restore()

    def on_measure_run(self):
        self.switch_off_lights()
        self.sync_environment_controls()
        self.lock_controls()
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.store()
        # TODO
        panel.clear_readings()
        measure = self.processes.get("measure")
        # Set process parameters
        measure.set("sample_name", self.sample_name())
        measure.set("sample_type", self.sample_type())
        measure.set("table_position", self.table_position())
        measure.set("operator", self.operator())
        measure.set("output_dir", self.output_dir())
        measure.set("write_logfiles", self.write_logfiles())
        measure.set("use_environ", self.use_environment())
        measure.set("use_table", self.use_table())
        measure.set("serialize_json", self.export_json())
        measure.set("serialize_txt", self.export_txt())
        measure.measurement_item = measurement
        measure.reading = panel.append_reading
        measure.update = panel.update_readings
        measure.append_analysis = panel.append_analysis
        measure.state = panel.state
        measure.push_summary = self.on_push_summary
        # TODO
        measure.start()

    def on_measure_finished(self):
        self.sync_environment_controls()
        self.unlock_controls()
        measure = self.processes.get("measure")
        measure.reading = lambda data: None
        self.sequence_tree.unlock()

    def on_status_start(self):
        self.lock_controls()
        self.status_tab.reset()
        status = self.processes.get("status")
        status.set("use_environ", self.use_environment())
        status.set("use_table", self.use_table())
        status.start()
        # Fix: stay in status tab
        self.tab_widget.current = self.status_tab

    def on_status_finished(self):
        self.unlock_controls()
        status = self.processes.get("status")
        self.status_tab.update_status(status)

    # Table calibration

    @handle_exception
    def on_table_joystick_clicked(self):
        state = self.table_joystick_button.checked
        with self.resources.get("table") as table_resource:
            table = Venus1(table_resource)
            table.joystick = state

    @handle_exception
    def on_table_controls_start(self):
        table = self.processes.get("table")
        dialog = TableControlDialog(table)
        dialog.load_settings()
        if self.use_environment():
            with self.processes.get("environment") as environ:
                pc_data = environ.pc_data()
                dialog.update_safety(laser_sensor=pc_data.relay_states.laser_sensor)
        dialog.run()
        dialog.store_settings()
        self.sync_table_controls()

    @handle_exception
    def on_box_laser_clicked(self):
        state = self.box_laser_button.checked
        with self.processes.get("environment") as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_clicked(self):
        state = self.box_light_button.checked
        with self.processes.get("environment") as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_clicked(self):
        state = self.microscope_light_button.checked
        with self.processes.get("environment") as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_clicked(self):
        state = self.microscope_camera_button.checked
        with self.processes.get("environment") as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_clicked(self):
        state = self.microscope_control_button.checked
        with self.processes.get("environment") as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_clicked(self):
        state = self.probecard_light_button.checked
        with self.processes.get("environment") as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_clicked(self):
        state = self.probecard_camera_button.checked
        with self.processes.get("environment") as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_clicked(self):
        state = self.pid_control_button.checked
        with self.processes.get("environment") as environment:
            environment.set_pid_control(state)

    @handle_exception
    def switch_off_lights(self):
        if self.use_environment():
            with self.processes.get("environment") as environment:
                if environment.has_lights():
                    environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.use_environment():
            with self.processes.get("environment") as environment:
                environment.request_pc_data()

        else:
            self.environment_tab.enabled = False

    def on_pc_data_updated(self, pc_data):
        self.box_laser_button.checked = pc_data.relay_states.laser_sensor
        self.box_light_button.checked = pc_data.relay_states.box_light
        self.microscope_light_button.checked = pc_data.relay_states.microscope_light
        self.microscope_camera_button.checked = pc_data.relay_states.microscope_camera
        self.microscope_control_button.checked = pc_data.relay_states.microscope_control
        self.probecard_light_button.checked = pc_data.relay_states.probecard_light
        self.probecard_camera_button.checked = pc_data.relay_states.probecard_camera
        self.pid_control_button.checked = pc_data.pid_status
        self.environment_tab.enabled = True
        self.environment_tab.update_data(pc_data)

    @handle_exception
    def sync_table_controls(self):
        """Syncronize table controls."""
        # try:
        #     with self.resources.get("table") as table_resource:
        #         table = Venus1(table_resource)
        #         joystick_state = table.joystick
        # except:
        #     self.table_groupbox.checked = False
        #     raise
        # else:
        #     self.table_joystick_button.checked = joystick_state

    def on_environment_groupbox_toggled(self, state):
        if state:
            self.sync_environment_controls()

    def on_table_groupbox_toggled(self, state):
        if self.use_table():
            self.sync_table_controls()

    @handle_exception
    def on_push_summary(self, *args):
        """Push result to summary and write to summary file (experimantal)."""
        item = self.summary_tab.append_result(*args)
        output_path = self.output_widget.current_location
        if output_path and os.path.exists(output_path):
            filename = os.path.join(output_path, SUMMARY_FILENAME)
            has_header = os.path.exists(filename)
            with open(filename, 'a') as f:
                header = self.summary_tab.header()
                writer = CSVFormatter(f)
                for key in header:
                    writer.add_column(key)
                if not has_header:
                    writer.write_header()
                writer.write_row({header[i]: item[i].value for i in range(len(header))})

    def on_github(self):
        webbrowser.open(comet.app().window.github_url)

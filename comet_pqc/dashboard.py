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
from comet.driver.corvus import Venus1

from . import config

from .sequence import SequenceTree
from .sequence import SamplesItem
from .sequence import SampleTreeItem
from .sequence import ContactTreeItem
from .sequence import MeasurementTreeItem
from .sequence import SequenceManager

from .components import ToggleButton
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .tablecontrol import TableControlDialog
from .sequence import StartSequenceDialog

from .tabs import EnvironmentTab
from .tabs import MeasurementTab
from .tabs import StatusTab
from .tabs import SummaryTab
from .logwindow import LogWidget
from .formatter import CSVFormatter
from .settings import settings
from .utils import make_path, handle_exception

from .tablecontrol import safe_z_position

SUMMARY_FILENAME = "summary.csv"

TABLE_UNITS = {
    1: comet.ureg('um'),
    2: comet.ureg('mm'),
    3: comet.ureg('cm'),
    4: comet.ureg('m'),
    5: comet.ureg('inch'),
    6: comet.ureg('mil'),
}

class Dashboard(ui.Splitter, ProcessMixin, SettingsMixin):

    environment_poll_interval = 1.0

    sample_count = 4

    message_changed = None
    progress_changed = None

    def __init__(self, message_changed=None, progress_changed=None, **kwargs):
        super().__init__()
        # Properties
        self.collapsible = False
        # Callbacks
        self.message_changed = message_changed
        self.progress_changed = progress_changed
        # Layout
        self.sequence_tree = SequenceTree(
            selected=self.on_tree_selected,
            double_clicked=self.on_tree_double_clicked
        )
        self.sequence_tree.minimum_width = 360

        self.start_all_action = ui.Action(
            text="&All...",
            triggered=self.on_start_all
        )

        self.start_sample_action = ui.Action(
            text="&Sample...",
            triggered=self.on_start
        )
        self.start_sample_action.qt.setEnabled(False)

        self.start_contact_action = ui.Action(
            text="Contact...",
            triggered=self.on_start
        )
        self.start_contact_action.qt.setEnabled(False)

        self.start_measurement_action = ui.Action(
            text="&Measurement...",
            triggered=self.on_start
        )
        self.start_measurement_action.qt.setEnabled(False)

        self.start_menu = ui.Menu()
        self.start_menu.append(self.start_all_action)
        self.start_menu.append(self.start_sample_action)
        self.start_menu.append(self.start_contact_action)
        self.start_menu.append(self.start_measurement_action)

        self.start_button = ui.Button(
            text="Start",
            tool_tip="Start measurement sequence.",
            stylesheet="QPushButton:enabled{color:green;font-weight:bold;}"
        )
        self.start_button.qt.setMenu(self.start_menu.qt)

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

        self.add_sample_button = ui.Button(
            icon=make_path('assets', 'icons', 'add.svg'),
            tool_tip="Add new sample sequence.",
            width=24,
            clicked=self.on_add_sample_clicked
        )
        self.remove_sample_button = ui.Button(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove current sample sequence.",
            width=24,
            clicked=self.on_remove_sample_clicked
        )

        self.sequence_groupbox = ui.GroupBox(
            title="Sequence",
            layout=ui.Column(
                self.sequence_tree,
                ui.Row(
                    self.start_button,
                    self.stop_button,
                    self.reset_button,
                    self.add_sample_button,
                    self.remove_sample_button
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

        self.table_position_label = ui.Label()

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
                self.table_position_label,
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
            self.sequence_groupbox,
            self.table_groupbox,
            self.environment_groupbox,
            ui.Row(
                self.operator_groupbox,
                self.output_groupbox,
                stretch=(3, 7)
            ),
            stretch=(1, 0, 0)
        )

        # Tabs

        self.measurement_tab = MeasurementTab(restore=self.on_measure_restore)
        self.environment_tab = EnvironmentTab()
        self.status_tab = StatusTab(reload=self.on_status_start)
        self.summary_tab = SummaryTab()

        self.panels = self.measurement_tab.panels
        self.panels.sample_changed = self.on_sample_changed

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

        # Setup process callbacks

        self.environ_process = self.processes.get("environ")
        self.environ_process.pc_data_updated = self.on_pc_data_updated

        self.status_process = self.processes.get("status")
        self.status_process.finished = self.on_status_finished

        self.table_process = self.processes.get("table")
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed

        self.measure_process = self.processes.get("measure")
        self.measure_process.finished = self.on_measure_finished
        self.measure_process.measurement_state = self.on_measurement_state
        self.measure_process.save_to_image = self.on_save_to_image

        # Experimental

        # Install timer to update environment controls
        self.environment_timer = Timer(timeout=self.sync_environment_controls)
        self.environment_timer.start(self.environment_poll_interval)

    @handle_exception
    def load_settings(self):
        self.sizes = self.settings.get("dashboard_sizes") or (300, 500)
        samples = self.settings.get("sequence_samples") or []
        self.sequence_tree.clear()
        for kwargs in samples:
            item = SampleTreeItem()
            self.sequence_tree.append(item)
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logging.error(exc)
        if len(self.sequence_tree):
            self.sequence_tree.current = self.sequence_tree[0]
        self.sequence_tree.fit()
        use_environ = self.settings.get("use_environ", False)
        self.environment_groupbox.checked = use_environ
        use_table =  self.settings.get("use_table", False)
        self.table_groupbox.checked = use_table
        self.operator_widget.load_settings()
        self.output_widget.load_settings()

    @handle_exception
    def store_settings(self):
        self.settings["dashboard_sizes"] = self.sizes
        sequence_samples = [sample.to_settings() for sample in self.sequence_tree]
        self.settings["sequence_samples"] = sequence_samples
        self.settings["use_environ"] = self.use_environment()
        self.settings["use_table"] = self.use_table()
        self.operator_widget.store_settings()
        self.output_widget.store_settings()

    def sample_name(self):
        """Return sample name."""
        item = self.sequence_tree.current
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.name
        if isinstance(item, ContactTreeItem):
            return item.sample.name
        if isinstance(item, SampleTreeItem):
            return item.name
        return ""

    def sample_type(self):
        """Return sample type."""
        item = self.sequence_tree.current
        if isinstance(item, MeasurementTreeItem):
            return item.contact.sample.sample_type
        if isinstance(item, ContactTreeItem):
            return item.sample.sample_type
        if isinstance(item, SampleTreeItem):
            return item.sample_type
        return ""

    def table_position(self):
        """Return table position in millimeters as tuple. If table not available
        return (0., 0., 0.).
        """
        if self.use_table():
            return self.table_process.get_cached_position()
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
        """Return output base path."""
        return os.path.realpath(self.output_widget.current_location)

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

    def lock_controls(self):
        """Lock dashboard controls."""
        self.environment_groupbox.enabled = False
        self.table_groupbox.enabled = False
        self.sequence_tree.double_clicked = None
        self.start_button.enabled = False
        self.stop_button.enabled = True
        self.reset_button.enabled = False
        self.add_sample_button.enabled = False
        self.remove_sample_button.enabled = False
        self.output_groupbox.enabled = False
        self.operator_groupbox.enabled = False
        self.measurement_tab.lock()
        self.sequence_tree.lock()
        self.status_tab.lock()

    def unlock_controls(self):
        """Unlock dashboard controls."""
        self.environment_groupbox.enabled = True
        self.table_groupbox.enabled = True
        self.sequence_tree.double_clicked = self.on_tree_double_clicked
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self.reset_button.enabled = True
        self.add_sample_button.enabled = True
        self.remove_sample_button.enabled = True
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
        self.start_sample_action.qt.setEnabled(False)
        self.start_contact_action.qt.setEnabled(False)
        self.start_measurement_action.qt.setEnabled(False)
        if isinstance(item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.visible = True
            panel.mount(item)
            self.start_sample_action.qt.setEnabled(True)
        if isinstance(item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.visible = True
            panel.table_move_to = self.on_table_move_to
            panel.table_contact = self.on_table_contact
            panel.mount(item)
            self.start_contact_action.qt.setEnabled(True)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            panel.visible = True
            panel.mount(item)
            self.measurement_tab.measure_controls.visible = True
            self.start_measurement_action.qt.setEnabled(True)
        # Show measurement tab
        self.tab_widget.current = self.measurement_tab

    def on_tree_double_clicked(self, item, index):
        self.on_start()

    def on_sample_changed(self, item):
        self.sequence_tree.fit()

    # Contcat table controls

    @handle_exception
    def on_table_move_to(self, contact):
        x, y, z = contact.position
        z = safe_z_position(z)
        self.lock_controls()
        self.table_process.message_changed = lambda message: self.emit('message_changed', message)
        self.table_process.progress_changed = lambda a, b: self.emit('progress_changed', a, b)
        self.table_process.absolute_move_finished = self.on_table_finished
        self.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def on_table_contact(self, contact):
        self.lock_controls()
        x, y, z = contact.position
        self.table_process.message_changed = lambda message: self.emit('message_changed', message)
        self.table_process.progress_changed = lambda a, b: self.emit('progress_changed', a, b)
        self.table_process.absolute_move_finished = self.on_table_finished
        self.table_process.safe_absolute_move(x, y, z)

    def on_table_finished(self):
        self.table_process.absolute_move_finished = None
        current_item = self.sequence_tree.current
        if isinstance(current_item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.mount(current_item)
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.mount(current_item)
        self.unlock_controls()

    @handle_exception
    def on_start_all(self):
        sample_items = []
        for item in self.sequence_tree:
            sample_items.append(item)
        dialog = StartSequenceDialog(
            context=sample_items,
            table_enabled=self.use_table()
        )
        self.operator_widget.store_settings()
        self.output_widget.store_settings()
        dialog.load_settings()
        if not dialog.run():
            return
        dialog.store_settings()
        self.operator_widget.load_settings()
        self.output_widget.load_settings()
        self._on_start(
            SamplesItem(sample_items),
            move_to_contact=dialog.move_to_contact(),
            move_to_after_position=dialog.move_to_position()
        )

    @handle_exception
    def on_start(self):
        current_item = self.sequence_tree.current
        if isinstance(current_item, MeasurementTreeItem):
            contact_item = current_item.contact
            if not ui.show_question(
                title="Run Measurement",
                text=f"Are you sure to run measurement '{current_item.name}' for '{contact_item.name}'?"
            ): return
            self._on_start(current_item)
        elif isinstance(current_item, ContactTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.use_table()
            )
            self.operator_widget.store_settings()
            self.output_widget.store_settings()
            dialog.load_settings()
            if not dialog.run():
                return
            dialog.store_settings()
            self.operator_widget.load_settings()
            self.output_widget.load_settings()
            self._on_start(
                current_item,
                move_to_contact=dialog.move_to_contact(),
                move_to_after_position=dialog.move_to_position()
            )
        elif isinstance(current_item, SampleTreeItem):
            dialog = StartSequenceDialog(
                context=current_item,
                table_enabled=self.use_table()
            )
            self.operator_widget.store_settings()
            self.output_widget.store_settings()
            dialog.load_settings()
            if not dialog.run():
                return
            dialog.store_settings()
            self.operator_widget.load_settings()
            self.output_widget.load_settings()
            move_to_after_position = dialog.move_to_position()
            self._on_start(
                current_item,
                move_to_contact=dialog.move_to_contact(),
                move_to_after_position=dialog.move_to_position()
            )

    def _on_start(self, context, move_to_contact=False, move_to_after_position=None):
        # Create output directory
        self.create_output_dir()
        self.switch_off_lights()
        self.sync_environment_controls()
        self.lock_controls()
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        measure = self.measure_process
        measure.context = context
        measure.set("table_position", self.table_position())
        measure.set("operator", self.operator())
        measure.set("output_dir", self.output_dir())
        measure.set("write_logfiles", self.write_logfiles())
        measure.set("use_environ", self.use_environment())
        measure.set("use_table", self.use_table())
        measure.set("serialize_json", self.export_json())
        measure.set("serialize_txt", self.export_txt())
        measure.set("move_to_contact", move_to_contact)
        measure.set("move_to_after_position", move_to_after_position)
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
            measure.reading = panel.append_reading
            measure.update = panel.update_readings
            measure.append_analysis = panel.append_analysis
            measure.state = panel.state
        def hide_measurement(item):
            item.selectable = False
            item[0].color = None
        measure.show_measurement = show_measurement
        measure.hide_measurement = hide_measurement
        measure.push_summary = self.on_push_summary
        measure.finished = self.on_finished
        measure.start()

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
        self.measure_process.stop()

    def on_finished(self):
        self.sync_environment_controls()
        self.unlock_controls()

    def on_reset_sequence_state(self):
        if not ui.show_question(
            title="Reset State",
            text="Do you want to reset all sequence states?"
        ): return
        self.panels.unmount()
        self.panels.hide()
        for item in self.sequence_tree:
            if item.sequence:
                filename = item.sequence.filename
                sequence = config.load_sequence(filename)
                item.load_sequence(sequence)
        if self.sequence_tree:
            self.sequence_tree.current = self.sequence_tree[0]

    def on_add_sample_clicked(self):
        item = SampleTreeItem(
            name_prefix="",
            name_infix="Unnamed",
            name_suffix="",
            sample_type="",
            enabled=False
        )
        self.sequence_tree.append(item)
        self.sequence_tree.fit()
        self.sequence_tree.current = item

    def on_remove_sample_clicked(self):
        item = self.sequence_tree.current
        if item in self.sequence_tree:
            if ui.show_question(
                title="Remove Sample",
                text=f"Do you want to remove '{item.name}'?"
            ):
                self.sequence_tree.remove(item)

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
        # Set process parameters
        self.measure_process.set("table_position", self.table_position())
        self.measure_process.set("operator", self.operator())
        self.measure_process.set("output_dir", self.output_dir())
        self.measure_process.set("write_logfiles", self.write_logfiles())
        self.measure_process.set("use_environ", self.use_environment())
        self.measure_process.set("use_table", self.use_table())
        self.measure_process.set("serialize_json", self.export_json())
        self.measure_process.set("serialize_txt", self.export_txt())
        self.measure_process.measurement_item = measurement
        self.measure_process.reading = panel.append_reading
        self.measure_process.update = panel.update_readings
        self.measure_process.append_analysis = panel.append_analysis
        self.measure_process.state = panel.state
        self.measure_process.push_summary = self.on_push_summary
        # TODO
        self.measure_process.start()

    def on_measure_finished(self):
        self.sync_environment_controls()
        self.unlock_controls()
        self.measure_process.reading = lambda data: None
        self.sequence_tree.unlock()

    def on_status_start(self):
        self.lock_controls()
        self.status_tab.reset()
        self.status_process.set("use_environ", self.use_environment())
        self.status_process.set("use_table", self.use_table())
        self.status_process.start()
        # Fix: stay in status tab
        self.tab_widget.current = self.status_tab

    def on_status_finished(self):
        self.unlock_controls()
        self.status_tab.update_status(self.status_process)

    # Table calibration

    def on_table_joystick_clicked(self):
        state = self.table_joystick_button.checked
        self.table_process.enable_joystick(state)

    def on_table_joystick_changed(self, state):
        self.table_joystick_button.checked = state

    def on_table_position_changed(self, x, y, z):
        self.table_position_label.text = f"X={x:.3f} | Y={y:.3f} | Z={z:.3f} mm"

    @handle_exception
    def on_table_controls_start(self):
        dialog = TableControlDialog(self.table_process)
        dialog.load_settings()
        dialog.load_samples(list(self.sequence_tree)) # HACK
        if self.use_environment():
            with self.environ_process as environ:
                pc_data = environ.pc_data()
                dialog.update_safety(laser_sensor=pc_data.relay_states.laser_sensor)
        dialog.run()
        dialog.store_settings()
        dialog.update_samples()
        # Prevent glitch
        current_item = self.sequence_tree.current
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.mount(current_item)
        # Restore events
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.sync_table_controls()

    @handle_exception
    def on_box_laser_clicked(self):
        state = self.box_laser_button.checked
        with self.environ_process as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_clicked(self):
        state = self.box_light_button.checked
        with self.environ_process as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_clicked(self):
        state = self.microscope_light_button.checked
        with self.environ_process as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_clicked(self):
        state = self.microscope_camera_button.checked
        with self.environ_process as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_clicked(self):
        state = self.microscope_control_button.checked
        with self.environ_process as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_clicked(self):
        state = self.probecard_light_button.checked
        with self.environ_process as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_clicked(self):
        state = self.probecard_camera_button.checked
        with self.environ_process as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_clicked(self):
        state = self.pid_control_button.checked
        with self.environ_process as environment:
            environment.set_pid_control(state)

    @handle_exception
    def switch_off_lights(self):
        if self.use_environment():
            with self.environ_process as environment:
                if environment.has_lights():
                    environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.use_environment():
            with self.environ_process as environment:
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
        enabled = self.use_table()
        self.table_process.enabled = enabled
        self.on_table_position_changed(float('nan'), float('nan'), float('nan'))
        if enabled:
            self.table_process.status()

    def on_environment_groupbox_toggled(self, state):
        if state:
            self.environ_process.start()
            self.sync_environment_controls()
        else:
            self.environ_process.stop()

    def on_table_groupbox_toggled(self, state):
        if state:
            self.table_process.start()
            self.sync_table_controls()
        else:
            self.table_process.stop()

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

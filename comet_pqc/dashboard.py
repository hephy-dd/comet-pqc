import logging
import os
import webbrowser

from qutie import Timer

import comet
from comet import ui

from comet.process import ProcessMixin
from comet.settings import SettingsMixin

from . import config

from .sequence import SequenceTree
from .sequence import SamplesItem
from .sequence import SampleTreeItem
from .sequence import ContactTreeItem
from .sequence import MeasurementTreeItem

from .components import ToggleButton
from .components import PositionWidget
from .components import CalibrationWidget
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .tablecontrol import TableControlDialog, safe_z_position
from .sequence import StartSequenceDialog

from .tabs import EnvironmentTab
from .tabs import MeasurementTab
from .tabs import StatusTab
from .tabs import SummaryTab
from .logwindow import LogWidget
from .formatter import CSVFormatter
from .settings import settings
from .utils import make_path, handle_exception, caldone_valid
from .position import Position

SUMMARY_FILENAME = "summary.csv"

class TableControlWidget(ui.GroupBox, comet.SettingsMixin):

    joystick_toggled = None
    control_clicked = None

    def __init__(self, joystick_toggled=None, control_clicked=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "Table"
        self.checkable = True
        self._joystick_button = ToggleButton(
            text="Joystick",
            tool_tip="Toggle table joystick",
            checkable=True,
            toggled=self.on_joystick_toggled
        )
        self._position_widget = PositionWidget()
        self._calibration_widget = CalibrationWidget()
        self._control_button = ui.Button(
            text="Control...",
            tool_tip="Open table controls dialog.",
            clicked=self.on_control_clicked
        )
        self.layout=ui.Row(
            self._position_widget,
            self._calibration_widget,
            ui.Spacer(),
            ui.Column(
                ui.Spacer(),
                self._control_button,
                self._joystick_button,
                ui.Spacer()
            ),
            stretch=(0, 0, 1, 0)
        )
        # Callbacks
        self.joystick_toggled = joystick_toggled
        self.control_clicked = control_clicked
        self._joystick_limits = [0, 0, 0]
        self.calibration_valid = False

    def on_joystick_toggled(self, state):
        self.emit(self.joystick_toggled, state)

    def on_control_clicked(self):
        self.emit(self.control_clicked)

    def update_joystick_state(self, state):
        self._joystick_button.toggled = None
        self._joystick_button.checked = state
        self._joystick_button.toggled = self.on_joystick_toggled

    def update_position(self, position):
        self._position_widget.update_position(position)
        limits = self._joystick_limits
        enabled = position.x <= limits[0] and position.y <= limits[1] and position.z <= limits[2]
        self._joystick_button.enabled = enabled and self.calibration_valid

    def update_calibration(self, position):
        self._calibration_widget.update_calibration(position)
        self.calibration_valid = caldone_valid(position)

    def load_settings(self):
        use_table = self.settings.get("use_table") or False
        self.checked = use_table
        self._joystick_limits = settings.table_joystick_maximum_limits

class EnvironmentControlWidget(ui.GroupBox):

    laser_sensor_toggled = None
    box_light_toggled = None
    microscope_light_toggled = None
    microscope_camera_toggled = None
    microscope_control_toggled = None
    probecard_light_toggled = None
    probecard_camera_toggled = None
    pid_control_toggled = None

    def __init__(self, laser_sensor_toggled=None, box_light_toggled=None,
                 microscope_light_toggled=None, microscope_camera_toggled=None,
                 microscope_control_toggled=None, probecard_light_toggled=None,
                 probecard_camera_toggled=None, pid_control_toggled=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.title = "Environment Box"
        self.checkable = True
        self._laser_sensor_button = ToggleButton(
            text="Laser",
            tool_tip="Toggle laser",
            checkable=True,
            checked=False,
            toggled=self.on_laser_sensor_toggled
        )
        self._box_light_button = ToggleButton(
            text="Box Light",
            tool_tip="Toggle box light",
            checkable=True,
            checked=False,
            toggled=self.on_box_light_toggled
        )
        self._microscope_light_button = ToggleButton(
            text="Mic Light",
            tool_tip="Toggle microscope light",
            checkable=True,
            checked=False,
            toggled=self.on_microscope_light_toggled
        )
        self._microscope_camera_button = ToggleButton(
            text="Mic Cam",
            tool_tip="Toggle microscope camera power",
            checkable=True,
            checked=False,
            toggled=self.on_microscope_camera_toggled
        )
        self._microscope_control_button = ToggleButton(
            text="Mic Ctrl",
            tool_tip="Toggle microscope control",
            checkable=True,
            checked=False,
            toggled=self.on_microscope_control_toggled
        )
        self._probecard_light_button = ToggleButton(
            text="PC Light",
            tool_tip="Toggle probe card light",
            checkable=True,
            checked=False,
            toggled=self.on_probecard_light_toggled
        )
        self._probecard_camera_button = ToggleButton(
            text="PC Cam",
            tool_tip="Toggle probe card camera power",
            checkable=True,
            checked=False,
            toggled=self.on_probecard_camera_toggled
        )
        self._pid_control_button = ToggleButton(
            text="PID Control",
            tool_tip="Toggle PID control",
            checkable=True,
            checked=False,
            toggled=self.on_pid_control_toggled
        )
        self.layout=ui.Row(
            ui.Column(
                self._laser_sensor_button,
                self._microscope_camera_button,
            ),
            ui.Column(
                self._box_light_button,
                self._probecard_camera_button,
            ),
            ui.Column(
                self._microscope_light_button,
                self._microscope_control_button,
            ),
            ui.Column(
                self._probecard_light_button,
                self._pid_control_button
            ),
            stretch=(1, 1, 1, 1)
        )
        # Callbacks
        self.laser_sensor_toggled = laser_sensor_toggled
        self.box_light_toggled = box_light_toggled
        self.microscope_light_toggled = microscope_light_toggled
        self.microscope_camera_toggled = microscope_camera_toggled
        self.microscope_control_toggled = microscope_control_toggled
        self.probecard_light_toggled = probecard_light_toggled
        self.probecard_camera_toggled = probecard_camera_toggled
        self.pid_control_toggled = pid_control_toggled

    def on_laser_sensor_toggled(self, state):
        self.emit(self.laser_sensor_toggled, state)

    def on_box_light_toggled(self, state):
        self.emit(self.box_light_toggled, state)

    def on_microscope_light_toggled(self, state):
        self.emit(self.microscope_light_toggled, state)

    def on_microscope_camera_toggled(self, state):
        self.emit(self.microscope_camera_toggled, state)

    def on_microscope_control_toggled(self, state):
        self.emit(self.microscope_control_toggled, state)

    def on_probecard_light_toggled(self, state):
        self.emit(self.probecard_light_toggled, state)

    def on_probecard_camera_toggled(self, state):
        self.emit(self.probecard_camera_toggled, state)

    def on_pid_control_toggled(self, state):
        self.emit(self.pid_control_toggled, state)

    def update_laser_sensor_state(self, state):
        self._laser_sensor_button.checked = state

    def update_box_light_state(self, state):
        self._box_light_button.checked = state

    def update_microscope_light_state(self, state):
        self._microscope_light_button.checked = state

    def update_microscope_camera_state(self, state):
        self._microscope_camera_button.checked = state

    def update_microscope_control_state(self, state):
        self._microscope_control_button.checked = state

    def update_probecard_light_state(self, state):
        self._probecard_light_button.checked = state

    def update_probecard_camera_state(self, state):
        self._probecard_camera_button.checked = state

    def update_pid_control_state(self, state):
        self._pid_control_button.checked = state

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
            text="&All Samples",
            triggered=self.on_start_all
        )

        self.start_sample_action = ui.Action(
            text="&Sample",
            triggered=self.on_start
        )
        self.start_sample_action.qt.setEnabled(False)

        self.start_contact_action = ui.Action(
            text="&Contact",
            triggered=self.on_start
        )
        self.start_contact_action.qt.setEnabled(False)

        self.start_measurement_action = ui.Action(
            text="&Measurement",
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

        self.reload_config_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'reload.svg'),
            tool_tip="Reload sequence configurations from file.",
            clicked=self.on_reload_config_clicked
        )

        self.add_sample_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'add.svg'),
            tool_tip="Add new sample sequence.",
            clicked=self.on_add_sample_clicked
        )
        self.remove_sample_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove current sample sequence.",
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
                    self.reload_config_button,
                    self.add_sample_button,
                    self.remove_sample_button
                )
            )
        )

        # Environment Controls

        self.environment_control_widget = EnvironmentControlWidget(
            toggled=self.on_environment_groupbox_toggled,
            laser_sensor_toggled=self.on_laser_sensor_toggled,
            box_light_toggled=self.on_box_light_toggled,
            microscope_light_toggled=self.on_microscope_light_toggled,
            microscope_camera_toggled=self.on_microscope_camera_toggled,
            microscope_control_toggled=self.on_microscope_control_toggled,
            probecard_light_toggled=self.on_probecard_light_toggled,
            probecard_camera_toggled=self.on_probecard_camera_toggled,
            pid_control_toggled=self.on_pid_control_toggled
        )

        # Table controls

        self.table_control_widget = TableControlWidget(
            toggled=self.on_table_groupbox_toggled,
            joystick_toggled=self.on_table_joystick_toggled,
            control_clicked=self.on_table_control_clicked
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
            self.table_control_widget,
            self.environment_control_widget,
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
        self.table_process.caldone_changed = self.on_table_calibration_changed

        self.measure_process = self.processes.get("measure")
        self.measure_process.finished = self.on_finished
        self.measure_process.measurement_state = self.on_measurement_state
        self.measure_process.measurement_reset = self.on_measurement_reset
        self.measure_process.save_to_image = self.on_save_to_image

        self.contact_quality_process = self.processes.get("contact_quality")

        # Experimental

        # Install timer to update environment controls
        self.environment_timer = Timer(timeout=self.sync_environment_controls)
        self.environment_timer.start(self.environment_poll_interval)

        self.close_event = self.on_stop

    @handle_exception
    def load_settings(self):
        self.sizes = self.settings.get("dashboard_sizes") or (300, 500)
        samples = self.settings.get("sequence_samples") or []
        self.sequence_tree.clear()
        for kwargs in samples:
            item = SampleTreeItem()
            self.sequence_tree.append(item)
            item.expanded = False # do not expand
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logging.error(exc)
        if len(self.sequence_tree):
            self.sequence_tree.current = self.sequence_tree[0]
        self.sequence_tree.fit()
        use_environ = self.settings.get("use_environ", False)
        self.environment_control_widget.checked = use_environ
        self.table_control_widget.load_settings()
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
        return Position()

    def use_environment(self):
        """Return True if environment box enabled."""
        return self.environment_control_widget.checked

    def use_table(self):
        """Return True if table control enabled."""
        return self.table_control_widget.checked

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
        self.environment_control_widget.enabled = False
        self.table_control_widget.enabled = False
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
        self.environment_control_widget.enabled = True
        self.table_control_widget.enabled = True
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
            panel.table_move = self.on_table_contact
            panel.table_contact = self.on_table_move
            panel.mount(item)
            self.start_contact_action.qt.setEnabled(True)
        if isinstance(item, MeasurementTreeItem):
            panel = self.panels.get(item.type)
            if panel:
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
    def on_table_move(self, contact):
        if self.use_table():
            self.lock_controls()
            x, y, z = contact.position
            self.table_process.message_changed = lambda message: self.emit('message_changed', message)
            self.table_process.progress_changed = lambda a, b: self.emit('progress_changed', a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def on_table_contact(self, contact):
        if self.use_table():
            self.lock_controls()
            x, y, z = contact.position
            z = safe_z_position(z)
            self.table_process.message_changed = lambda message: self.emit('message_changed', message)
            self.table_process.progress_changed = lambda a, b: self.emit('progress_changed', a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    def on_table_finished(self):
        self.table_process.absolute_move_finished = None
        current_item = self.sequence_tree.current
        if isinstance(current_item, SampleTreeItem):
            panel = self.panels.get("sample")
            panel.visible = True
            panel.mount(current_item)
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.visible = True
            panel.mount(current_item)
        self.unlock_controls()

    @handle_exception
    def on_start_all(self):
        sample_items = SamplesItem(self.sequence_tree)
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
            sample_items,
            move_to_contact=dialog.move_to_contact(),
            move_to_after_position=dialog.move_to_position()
        )

    @handle_exception
    def on_start(self):
        # Store settings
        self.store_settings()
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
        measure.set("contact_delay", self.settings.get("table_contact_delay"))
        def show_measurement(item):
            item.selectable = True
            item.series.clear()
            item[0].color = 'blue'
            self.sequence_tree.scroll_to(item)
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
        measure.start()

    def on_measurement_state(self, item, state=None):
        item.state = state
        self.sequence_tree.fit()

    def on_measurement_reset(self, item):
        item.reset()
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

    @handle_exception
    def on_reset_sequence_state(self):
        if not ui.show_question(
            title="Reset State",
            text="Do you want to reset all sequence states?"
        ): return
        current_item = self.sequence_tree.current
        self.panels.unmount()
        self.panels.clear_readings()
        self.panels.hide()
        for sample_item in self.sequence_tree:
            sample_item.reset()
        if current_item is not None:
            panel = self.panels.get(current_item.type)
            panel.visible = True
            panel.mount(current_item)

    @handle_exception
    def on_reload_config_clicked(self):
        if not ui.show_question(
            title="Reload Configuration",
            text="Do you want to reload sequence configurations from file?"
        ): return
        for sample_item in self.sequence_tree:
            if sample_item.sequence:
                filename = sample_item.sequence.filename
                sequence = config.load_sequence(filename)
                sample_item.load_sequence(sequence)

    @handle_exception
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

    @handle_exception
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

    @handle_exception
    def on_table_joystick_toggled(self, state):
        self.table_process.enable_joystick(state)

    def on_table_joystick_changed(self, state):
        self.table_control_widget.update_joystick_state(state)

    def on_table_position_changed(self, position):
        self.table_control_widget.update_position(position)

    def on_table_calibration_changed(self, position):
        self.table_control_widget.update_calibration(position)
        panel = self.panels.get("contact")
        if panel:
            panel.update_use_table(self.use_table() and self.table_control_widget.calibration_valid)

    @handle_exception
    def on_table_control_clicked(self):
        self.table_process.enable_joystick(False)
        dialog = TableControlDialog(self.table_process, self.contact_quality_process)
        dialog.load_settings()
        dialog.load_samples(list(self.sequence_tree)) # HACK
        if self.use_environment():
            # TODO !!!
            with self.environ_process as environ:
                pc_data = environ.pc_data()
                dialog.update_safety(laser_sensor=pc_data.relay_states.laser_sensor)
                dialog.update_probecard_light(pc_data.relay_states.probecard_light)
                dialog.update_microscope_light(pc_data.relay_states.microscope_light)
                dialog.update_box_light(pc_data.relay_states.box_light)
            dialog.update_lights_enabled(True)
            def probecard_light_toggled(state):
                with self.environ_process as environ:
                    environ.set_probecard_light(state)
            def microscope_light_toggled(state):
                with self.environ_process as environ:
                    environ.set_microscope_light(state)
            def box_light_toggled(state):
                with self.environ_process as environ:
                    environ.set_box_light(state)
            dialog.probecard_light_toggled = probecard_light_toggled
            dialog.microscope_light_toggled = microscope_light_toggled
            dialog.box_light_toggled = box_light_toggled
        dialog.run()
        self.contact_quality_process.stop()
        self.contact_quality_process.join()
        dialog.store_settings()
        dialog.update_samples()
        # Prevent glitch
        current_item = self.sequence_tree.current
        if isinstance(current_item, ContactTreeItem):
            panel = self.panels.get("contact")
            panel.mount(current_item)
        # Restore events...
        self.table_process.joystick_changed = self.on_table_joystick_changed
        self.table_process.position_changed = self.on_table_position_changed
        self.table_process.caldone_changed = self.on_table_calibration_changed
        self.sync_table_controls()
        # Store settings
        self.store_settings()

    @handle_exception
    def on_laser_sensor_toggled(self, state):
        with self.environ_process as environment:
            environment.set_laser_sensor(state)

    @handle_exception
    def on_box_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_box_light(state)

    @handle_exception
    def on_microscope_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_light(state)

    @handle_exception
    def on_microscope_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_camera(state)

    @handle_exception
    def on_microscope_control_toggled(self, state):
        with self.environ_process as environment:
            environment.set_microscope_control(state)

    @handle_exception
    def on_probecard_light_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_light(state)

    @handle_exception
    def on_probecard_camera_toggled(self, state):
        with self.environ_process as environment:
            environment.set_probecard_camera(state)

    @handle_exception
    def on_pid_control_toggled(self, state):
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
        self.environment_control_widget.update_laser_sensor_state(pc_data.relay_states.laser_sensor)
        self.environment_control_widget.update_box_light_state(pc_data.relay_states.box_light)
        self.environment_control_widget.update_microscope_light_state(pc_data.relay_states.microscope_light)
        self.environment_control_widget.update_microscope_camera_state(pc_data.relay_states.microscope_camera)
        self.environment_control_widget.update_microscope_control_state(pc_data.relay_states.microscope_control)
        self.environment_control_widget.update_probecard_light_state(pc_data.relay_states.probecard_light)
        self.environment_control_widget.update_probecard_camera_state(pc_data.relay_states.probecard_camera)
        self.environment_control_widget.update_pid_control_state(pc_data.pid_status)
        self.environment_tab.enabled = True
        self.environment_tab.update_data(pc_data)

    @handle_exception
    def sync_table_controls(self):
        """Syncronize table controls."""
        enabled = self.use_table()
        self.table_process.enabled = enabled
        self.on_table_position_changed(Position())
        self.on_table_calibration_changed(Position())
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
            self.table_process.enable_joystick(False)
        else:
            self.table_process.stop()
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

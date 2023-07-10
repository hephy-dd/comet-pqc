import json
import logging
import math
import os
import time
import webbrowser

from PyQt5 import QtWidgets

import comet
from comet.process import ProcessMixin
from comet.settings import SettingsMixin
from comet import ui

from .components import (
    CalibrationWidget,
    OperatorWidget,
    PositionWidget,
    ToggleButton,
    WorkingDirectoryWidget,
)
from .core import config
from .core.position import Position
from .core.utils import make_path, user_home
from .sequence import (
    ContactTreeItem,
    EditSamplesDialog,
    MeasurementTreeItem,
    SamplesItem,
    SampleTreeItem,
    SequenceTree,
    StartSequenceDialog,
    load_all_sequences,
)
from .settings import settings
from .tablecontrol import TableControlDialog, safe_z_position
from .tabs import EnvironmentTab, MeasurementTab
from .utils import caldone_valid, handle_exception

logger = logging.getLogger(__name__)


class SequenceWidget(ui.GroupBox, SettingsMixin):

    config_version = 1

    def __init__(self, *, tree_selected, tree_double_clicked, start_all, start,
                 stop, reset_sequence_state, edit_sequence):
        super().__init__()
        self.current_path = user_home()
        self.title = "Sequence"
        self.tree_double_clicked = tree_double_clicked

        self._sequence_tree = SequenceTree(
            selected=tree_selected,
            double_clicked=self.tree_double_clicked
        )
        self._sequence_tree.minimum_width = 360

        self._start_all_action = ui.Action(
            text="&All Samples",
            triggered=start_all
        )

        self._start_sample_action = ui.Action(
            text="&Sample",
            triggered=start
        )
        self._start_sample_action.qt.setEnabled(False)

        self._start_contact_action = ui.Action(
            text="&Contact",
            triggered=start
        )
        self._start_contact_action.qt.setEnabled(False)

        self._start_measurement_action = ui.Action(
            text="&Measurement",
            triggered=start
        )
        self._start_measurement_action.qt.setEnabled(False)

        self._start_menu = ui.Menu()
        self._start_menu.append(self._start_all_action)
        self._start_menu.append(self._start_sample_action)
        self._start_menu.append(self._start_contact_action)
        self._start_menu.append(self._start_measurement_action)

        self._start_button = ui.Button(
            text="Start",
            tool_tip="Start measurement sequence.",
            stylesheet="QPushButton:enabled{color:green;font-weight:bold;}"
        )
        self._start_button.qt.setMenu(self._start_menu.qt)

        self._stop_button = ui.Button(
            text="Stop",
            tool_tip="Stop measurement sequence.",
            enabled=False,
            clicked=stop,
            stylesheet="QPushButton:enabled{color:red;font-weight:bold;}"
        )

        self._reset_button = ui.Button(
            text="Reset",
            tool_tip="Reset measurement sequence state.",
            clicked=reset_sequence_state
        )

        self._edit_button = ui.Button(
            text="Edit",
            tool_tip="Quick edit properties of sequence items.",
            clicked=edit_sequence
        )

        self._reload_config_button = ui.ToolButton(
            icon=make_path("assets", "icons", "reload.svg"),
            tool_tip="Reload sequence configurations from file.",
            clicked=self.on_reload_config_clicked
        )

        self._add_sample_button = ui.ToolButton(
            icon=make_path("assets", "icons", "add.svg"),
            tool_tip="Add new sample sequence.",
            clicked=self.on_add_sample_clicked
        )

        self._remove_sample_button = ui.ToolButton(
            icon=make_path("assets", "icons", "delete.svg"),
            tool_tip="Remove current sample sequence.",
            clicked=self.on_remove_sample_clicked
        )

        self._open_button = ui.ToolButton(
            icon=make_path("assets", "icons", "document_open.svg"),
            tool_tip="Open sequence tree from file.",
            clicked=self.on_open_clicked
        )

        self._save_button = ui.ToolButton(
            icon=make_path("assets", "icons", "document_save.svg"),
            tool_tip="Save sequence tree to file.",
            clicked=self.on_save_clicked
        )

        self.layout = ui.Column(
            self._sequence_tree,
            ui.Row(
                self._start_button,
                self._stop_button,
                self._reset_button,
                self._edit_button,
                self._reload_config_button,
                self._add_sample_button,
                self._remove_sample_button,
                self._open_button,
                self._save_button
            )
        )

    def load_settings(self):
        samples = self.settings.get("sequence_samples") or []
        self._sequence_tree.clear()
        for kwargs in samples:
            item = SampleTreeItem()
            self._sequence_tree.append(item)
            item.expanded = False # do not expand
            try:
                item.from_settings(**kwargs)
            except Exception as exc:
                logger.error(exc)
        if len(self._sequence_tree):
            self._sequence_tree.current = self._sequence_tree[0]
        self._sequence_tree.fit()
        self.current_path = self.settings.get("sequence_default_path") or user_home()

    def store_settings(self):
        sequence_samples = [sample.to_settings() for sample in self._sequence_tree]
        self.settings["sequence_samples"] = sequence_samples
        self.settings["sequence_default_path"] = self.current_path

    def lock(self):
        self._sequence_tree.double_clicked = None
        self._start_button.enabled = False
        self._stop_button.enabled = True
        self._reset_button.enabled = False
        self._edit_button.enabled = False
        self._reload_config_button.enabled = False
        self._add_sample_button.enabled = False
        self._remove_sample_button.enabled = False
        self._save_button.enabled = False
        self._open_button.enabled = False
        self._sequence_tree.lock()

    def unlock(self):
        self._sequence_tree.double_clicked = self.tree_double_clicked
        self._start_button.enabled = True
        self._stop_button.enabled = False
        self._reset_button.enabled = True
        self._edit_button.enabled = True
        self._reload_config_button.enabled = True
        self._add_sample_button.enabled = True
        self._remove_sample_button.enabled = True
        self._save_button.enabled = True
        self._open_button.enabled = True
        self._sequence_tree.unlock()

    def stop(self):
        self._stop_button.enabled = False

    @handle_exception
    def on_reload_config_clicked(self):
        if not ui.show_question(
            title="Reload Configuration",
            text="Do you want to reload sequence configurations from file?"
        ): return
        for sample_item in self._sequence_tree:
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
        self._sequence_tree.append(item)
        self._sequence_tree.fit()
        self._sequence_tree.current = item

    @handle_exception
    def on_remove_sample_clicked(self):
        item = self._sequence_tree.current
        if item in self._sequence_tree:
            if ui.show_question(
                title="Remove Sample",
                text=f"Do you want to remove {item.name!r}?"
            ):
                self._sequence_tree.remove(item)

    @handle_exception
    def on_open_clicked(self):
        filename = ui.filename_open(path=self.current_path, filter="JSON (*.json)")
        if filename:
            with open(filename) as f:
                logger.info("Reading sequence... %s", filename)
                data = json.load(f)
                logger.info("Reading sequence... done.")
            self.current_path = os.path.dirname(filename)
            version = data.get("version")
            if version is None:
                raise RuntimeError(f"Missing version information in sequence: {filename}")
            elif isinstance(version, int):
                if version != self.config_version:
                    raise RuntimeError(f"Invalid version in sequence: {filename}")
            else:
                raise RuntimeError(f"Invalid version information in sequence: {filename}")
            samples = data.get("sequence") or []
            self._sequence_tree.clear()
            for kwargs in samples:
                item = SampleTreeItem()
                self._sequence_tree.append(item)
                item.expanded = False # do not expand
                try:
                    item.from_settings(**kwargs)
                except Exception as exc:
                    logger.error(exc)
            if len(self._sequence_tree):
                self._sequence_tree.current = self._sequence_tree[0]
            self._sequence_tree.fit()

    @handle_exception
    def on_save_clicked(self):
        filename = ui.filename_save(path=self.current_path, filter="JSON (*.json)")
        if filename:
            samples = [sample.to_settings() for sample in self._sequence_tree]
            data = {
                "version": self.config_version,
                "sequence": samples
            }
            # Auto filename extension
            if os.path.splitext(filename)[-1] not in [".json"]:
                filename = f"{filename}.json"
                if os.path.exists(filename):
                    if not ui.show_question(f"Do you want to overwrite existing file {filename}?"):
                        return
            with open(filename, "w") as f:
                logger.info("Writing sequence... %s", filename)
                json.dump(data, f)
                logger.info("Writing sequence... done.")
            self.current_path = os.path.dirname(filename)


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


class Dashboard(ui.Column, ProcessMixin, SettingsMixin):

    sample_count = 4

    lock_state_changed = None
    message_changed = None
    progress_changed = None

    def __init__(self, lock_state_changed=None, message_changed=None, progress_changed=None, **kwargs):
        super().__init__()
        # Callbacks
        self.lock_state_changed = lock_state_changed
        self.message_changed = message_changed
        self.progress_changed = progress_changed
        # Layout
        self.temporary_z_limit_label = ui.Label(
            text="Temporary Probecard Z-Limit applied. "
                 "Revert after finishing current measurements.",
            stylesheet="QLabel{color: black; background-color: yellow; padding: 4px; border-radius: 4px;}",
            visible=False
        )
        self.sequence_widget = SequenceWidget(
            tree_selected=self.on_tree_selected,
            tree_double_clicked=self.on_tree_double_clicked,
            start_all=self.on_start_all,
            start=self.on_start,
            stop=self.on_stop,
            reset_sequence_state=self.on_reset_sequence_state,
            edit_sequence=self.on_edit_sequence
        )
        self.sequence_tree = self.sequence_widget._sequence_tree
        self.start_sample_action = self.sequence_widget._start_sample_action
        self.start_contact_action = self.sequence_widget._start_contact_action
        self.start_measurement_action = self.sequence_widget._start_measurement_action

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
            self.sequence_widget,
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

        self.panels = self.measurement_tab.panels
        self.panels.sample_changed = self.on_sample_changed

        # Tabs

        self.tab_widget = ui.Tabs(
            self.measurement_tab,
            self.environment_tab,
        )

        # Layout

        self.splitter = ui.Splitter()
        self.splitter.append(self.control_widget)
        self.splitter.append(self.tab_widget)
        self.splitter.stretch = 4, 9
        self.splitter.collapsible = False

        self.append(self.temporary_z_limit_label)
        self.append(self.splitter)
        self.stretch = 0, 1

        # Setup process callbacks

        self.environ_process = self.processes.get("environ")
        self.environ_process.pc_data_updated = self.on_pc_data_updated

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

        self.close_event = self.on_stop

    @handle_exception
    def load_settings(self):
        self.splitter.sizes = self.settings.get("dashboard_sizes") or (300, 500)
        self.sequence_widget.load_settings()
        use_environ = self.settings.get("use_environ", False)
        self.environment_control_widget.checked = use_environ
        self.table_control_widget.load_settings()
        self.operator_widget.load_settings()
        self.output_widget.load_settings()

    @handle_exception
    def store_settings(self):
        self.settings["dashboard_sizes"] = self.splitter.sizes
        self.sequence_widget.store_settings()
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
        self.sequence_widget.lock()
        self.output_groupbox.enabled = False
        self.operator_groupbox.enabled = False
        self.measurement_tab.lock()
        self.plugin_manager.handle("lock_controls", True)
        self.lock_state_changed(True)

    def unlock_controls(self):
        """Unlock dashboard controls."""
        self.environment_control_widget.enabled = True
        self.table_control_widget.enabled = True
        self.sequence_widget.unlock()
        self.output_groupbox.enabled = True
        self.operator_groupbox.enabled = True
        self.measurement_tab.unlock()
        self.plugin_manager.handle("lock_controls", False)
        self.lock_state_changed(False)

    def on_toggle_temporary_z_limit(self, enabled: bool) -> None:
        logger.info("Temporary Z-Limit enabled: %s", enabled)
        self.temporary_z_limit_label.visible = enabled

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
            self.table_process.message_changed = lambda message: self.emit("message_changed", message)
            self.table_process.progress_changed = lambda a, b: self.emit("progress_changed", a, b)
            self.table_process.absolute_move_finished = self.on_table_finished
            self.table_process.safe_absolute_move(x, y, z)

    @handle_exception
    def on_table_contact(self, contact):
        if self.use_table():
            self.lock_controls()
            x, y, z = contact.position
            z = safe_z_position(z)
            self.table_process.message_changed = lambda message: self.emit("message_changed", message)
            self.table_process.progress_changed = lambda a, b: self.emit("progress_changed", a, b)
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
                text=f"Are you sure to run measurement {current_item.name!r} for {contact_item.name!r}?"
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
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        self.create_output_dir()
        self.switch_off_lights()
        self.sync_environment_controls()
        self.lock_controls()
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
        measure.set("contact_delay", self.settings.get("table_contact_delay") or 0)
        measure.set("retry_contact_overdrive", settings.retry_contact_overdrive)
        def show_measurement(item):
            item.selectable = True
            item.series.clear()
            item[0].color = "blue"
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
        measure.measurements_finished = self.on_measurements_finished
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
        self.sequence_widget.stop()
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
    def on_edit_sequence(self):
        sequences = load_all_sequences(self.settings)
        dialog = EditSamplesDialog(self.sequence_tree, sequences)
        dialog.run()
        self.on_tree_selected(self.sequence_tree.current)

    # Measurement control

    def on_measure_restore(self):
        if not ui.show_question(
            title="Restore Defaults",
            text="Do you want to restore to default parameters?"
        ): return
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.restore()

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
            dialog.probecard_light_toggled = self.on_probecard_light_toggled
            dialog.microscope_light_toggled = self.on_microscope_light_toggled
            dialog.box_light_toggled = self.on_box_light_toggled
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
        t = time.time()
        # Note: occasional crashes due to `NaN` timestamp.
        if not math.isfinite(t):
            logger.error("invalid timestamp: %s", t)
            t = 0
        self.environment_tab.append_data(t, pc_data)

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
    def on_push_summary(self, data: dict) -> None:
        self.plugin_manager.handle("summary", data=data)

    @handle_exception
    def on_measurements_finished(self) -> None:
        message = "PQC measurements finished!"
        self.plugin_manager.handle("notification", message=message)

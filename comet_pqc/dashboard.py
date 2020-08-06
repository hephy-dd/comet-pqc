import copy
import datetime
import logging
import os
import traceback

from qutie.qt import QtCore, QtGui
from qutie import Timer

import comet

from comet.process import ProcessMixin
from comet.settings import SettingsMixin
from comet.resource import ResourceMixin
from comet.driver.corvus import Venus1

from . import config

from .trees import SequenceTree
from .trees import ContactTreeItem
from .trees import MeasurementTreeItem

from .panels import IVRampPanel
from .panels import IVRampElmPanel
from .panels import IVRampBiasPanel
from .panels import IVRampBiasElmPanel
from .panels import IVRamp4WirePanel
from .panels import CVRampPanel
from .panels import CVRampHVPanel
from .panels import CVRampAltPanel
from .panels import FrequencyScanPanel

from .dialogs import TableControlDialog
from .dialogs import TableMoveDialog
from .dialogs import TableCalibrateDialog

from .logwindow import LogWidget
from .summary import SummaryTree
from .formatter import CSVFormatter

from .driver import EnvironmentBox

SUMMARY_FILENAME = "summary.csv"

def create_icon(size, color):
    """Return circular colored icon."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor("transparent"))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setPen(QtGui.QColor(color))
    painter.setBrush(QtGui.QColor(color))
    painter.drawEllipse(1, 1, size-2, size-2)
    del painter
    return comet.Icon(qt=pixmap)

def handle_exception(func):
    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            tb = traceback.format_exc()
            logging.error(exc)
            logging.error(tb)
            comet.show_exception(exc, tb)
    return catch_exception_wrapper

class ToggleButton(comet.Button):
    """Colored checkable button."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icons = {False: create_icon(12, "grey"), True: create_icon(12, "green")}
        self.on_toggle_color(self.checked)
        self.qt.toggled.connect(self.on_toggle_color)

    def on_toggle_color(self, state):
        self.icon = self.icons[state]

class PanelStack(comet.Row):
    """Stack of measurement panels."""

    def __init__(self):
        super().__init__()
        self.append(IVRampPanel(visible=False))
        self.append(IVRampElmPanel(visible=False))
        self.append(IVRampBiasPanel(visible=False))
        self.append(IVRampBiasElmPanel(visible=False))
        self.append(CVRampPanel(visible=False))
        self.append(CVRampHVPanel(visible=False))
        self.append(CVRampAltPanel(visible=False))
        self.append(IVRamp4WirePanel(visible=False))
        self.append(FrequencyScanPanel(visible=False))

    def store(self):
        for child in self:
            child.store()

    def unmount(self):
        for child in self:
            child.unmount()

    def clear_readings(self):
        for child in self:
            child.clear_readings()

    def hide(self):
        for child in self:
            child.visible = False

    def lock(self):
        for child in self:
            child.lock()

    def unlock(self):
        for child in self:
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

        self.sample_name_text = comet.Text(
            value=self.settings.get("sample_name", "Unnamed"),
            changed=self.on_sample_name_changed
        )
        self.sample_type_text = comet.Text(
            value=self.settings.get("sample_type", ""),
            changed=self.on_sample_type_changed
        )
        self.sequence_combobox = comet.ComboBox(
            changed=self.on_load_sequence_tree
        )

        self.sample_groupbox = comet.GroupBox(
            title="Sample",
            layout=comet.Row(
                comet.Column(
                    comet.Label("Name"),
                    comet.Label("Type"),
                    comet.Label("Sequence")
                ),
                comet.Column(
                    self.sample_name_text,
                    self.sample_type_text,
                    self.sequence_combobox
                ),
                stretch=(0, 1)
            )
        )

        self.sequence_tree = SequenceTree(selected=self.on_tree_selected)
        self.sequence_tree.minimum_width = 360

        self.start_button = comet.Button(
            text="Start",
            tool_tip="Start measurement sequence.",
            clicked=self.on_sequence_start
        )

        self.stop_button = comet.Button(
            text="Stop",
            tool_tip="Stop measurement sequence.",
            enabled=False,
            clicked=self.on_sequence_stop
        )

        self.sequence_groupbox = comet.GroupBox(
            title="Sequence",
            layout=comet.Column(
                self.sequence_tree,
                comet.Row(
                    self.start_button,
                    self.stop_button
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

        self.environment_groupbox = comet.GroupBox(
            title="Environment Box",
            checkable=True,
            checked=self.settings.get("use_environ", True),
            toggled=self.on_environment_groupbox_toggled,
            layout=comet.Column(
                comet.Row(
                    self.box_laser_button,
                    self.box_light_button,
                    self.microscope_light_button,
                    self.probecard_light_button
                ),
                comet.Row(
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

        self.table_control_button = comet.Button(
            text="Control...",
            tool_tip="Virtual table joystick controls.",
            clicked=self.on_table_controls_start
        )

        self.table_move_button = comet.Button(
            text="Move to...",
            tool_tip="Move table to predefined positions.",
            clicked=self.on_table_move_start
        )

        self.table_calibrate_button = comet.Button(
            text="Calibrate...",
            tool_tip="Calibrate table.",
            clicked=self.on_table_calibrate_start
        )

        self.table_groupbox = comet.GroupBox(
            title="Table",
            checkable=True,
            checked=self.settings.get("use_table", False),
            toggled=self.on_table_groupbox_toggled,
            layout=comet.Row(
                self.table_joystick_button,
                comet.Spacer(vertical=False),
                self.table_control_button,
                self.table_move_button,
                self.table_calibrate_button
            )
        )

        # Output controls

        self.output_text = comet.Text(
            value=self.settings.get("output_path", os.path.join(os.path.expanduser("~"), "PQC")),
            changed=self.on_output_changed
        )

        self.output_groupbox = comet.GroupBox(
            title="Working Directory",
            layout=comet.Row(
                self.output_text,
                comet.Button(
                    text="...",
                    width=32,
                    clicked=self.on_select_output
                )
            )
        )

        # Controls

        self.control_widget = comet.Column(
            self.sample_groupbox,
            self.sequence_groupbox,
            self.environment_groupbox,
            self.table_groupbox,
            self.output_groupbox,
            stretch=(0, 1, 0, 0)
        )

        # Measurement panel stack

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

        # Measurement tab

        self.measurement_tab = comet.Tab(
            title="Measurement",
            layout=comet.Column(
                self.panels,
                self.measure_controls,
                stretch=(1, 0)
            )
        )

        # Status tab

        self.matrix_model_text = comet.Text(readonly=True)
        self.matrix_channels_text = comet.Text(readonly=True)
        self.hvsrc_model_text = comet.Text(readonly=True)
        self.vsrc_model_text = comet.Text(readonly=True)
        self.lcr_model_text = comet.Text(readonly=True)
        self.elm_model_text = comet.Text(readonly=True)
        self.table_model_text = comet.Text(readonly=True)
        self.table_state_text = comet.Text(readonly=True)
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
                    title="HVSource",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.hvsrc_model_text,
                        stretch=(1, 7)
                    )
                ),
                comet.GroupBox(
                    title="VSource",
                    layout=comet.Row(
                        comet.Label("Model:"),
                        self.vsrc_model_text,
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
                    title="Table",
                    layout=comet.Column(
                        comet.Row(
                            comet.Label("Model:"),
                            self.table_model_text,
                            stretch=(1, 7)
                        ),
                        comet.Row(
                            comet.Label("State:"),
                            self.table_state_text,
                            stretch=(1, 7)
                        )
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

        # Summary tab

        self.summary_tree = SummaryTree()

        self.summary_tab = comet.Tab(
            title="Summary",
            layout=self.summary_tree
        )

        self.log_widget = LogWidget()
        self.log_widget.add_logger(logging.getLogger())

        self.logging_tab = comet.Tab(
            title="Logs",
            layout=self.log_widget
        )

        # Tabs

        self.tab_widget = comet.Tabs(
            self.measurement_tab,
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
        self.environment_timer.start(1.0)

    def load_sequences(self):
        """Load available sequence configurations."""
        current_sequence_id = self.settings.get("current_sequence_id")
        self.sequence_combobox.clear()
        for name, filename in sorted(config.list_configs(config.SEQUENCE_DIR)):
            sequence = config.load_sequence(filename)
            self.sequence_combobox.append(sequence)
        custom_sequences = []
        for filename in self.settings.get("custom_sequences") or []:
            if os.path.exists(filename):
                sequence = config.load_sequence(filename)
                sequence.name = f"{sequence.name} (custom)"
                self.sequence_combobox.append(sequence)
                custom_sequences.append(filename)
        self.settings["custom_sequences"] = custom_sequences
        for sequence in self.sequence_combobox:
            if sequence.id == current_sequence_id:
                self.sequence_combobox.current = sequence
                break

    def output_dir(self):
        """Return output path."""
        base = os.path.realpath(self.output_text.value)
        sample_name = self.sample_name_text.value
        sample_type = self.sample_type_text.value
        dirname = comet.safe_filename(f"{sample_name}-{sample_type}")
        return os.path.join(base, dirname)

    def create_output_dir(self):
        """Create output directory for sample if not exists, return directory
        path.
        """
        output_dir = self.output_dir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    # Callbacks

    def on_sample_name_changed(self, value):
        self.settings["sample_name"] = value

    def on_sample_type_changed(self, value):
        self.settings["sample_type"] = value

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
            self.panels.unmount()
            panel = self.panels.get(item.type)
            panel.visible = True
            panel.mount(item)
            self.measure_controls.visible = True
        # Show measurement tab
        self.tab_widget.current = self.measurement_tab

    def on_sequence_start(self):
        if isinstance(self.sequence_tree.current, MeasurementTreeItem):
            contact_item = self.sequence_tree.current.contact
        else:
            contact_item = self.sequence_tree.current
        if not comet.show_question(
            title="Start sequence",
            text=f"Are you sure to start sequence '{contact_item.name}'?"
        ): return
        self.switch_off_lights()
        self.sync_environment_controls()
        self.sample_groupbox.enabled = False
        self.table_calibrate_button.enabled = False
        self.environment_groupbox.enabled = False
        self.table_groupbox.enabled = False
        self.start_button.enabled = False
        self.stop_button.enabled = True
        self.reload_status_button.enabled = False
        self.measure_controls.enabled = False
        self.output_groupbox.enabled = False
        self.panels.lock()
        self.panels.store()
        self.panels.unmount()
        self.panels.clear_readings()
        # HACK oh dear...
        for measurement_item in contact_item.children:
            measurement_item.series.clear()
        self.sequence_tree.lock()
        self.sequence_tree.reset()
        sample_name = self.sample_name_text.value
        sample_type = self.sample_type_text.value
        output_dir = self.create_output_dir()
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", sample_name)
        sequence.set("sample_type", sample_type)
        sequence.set("output_dir", output_dir)
        sequence.set("use_environ", self.environment_groupbox.checked)
        sequence.set("use_table", self.table_groupbox.checked)
        sequence.contact_item = contact_item
        # sequence.sequence_tree = self.sequence_tree
        def show_measurement(prev, next):
            if prev:
                prev.selectable = False
            next.selectable = True
            self.panels.unmount()
            self.panels.hide()
            self.panels.clear_readings()
            panel = self.panels.get(next.type)
            panel.visible = True
            panel.mount(next)
            sequence.reading = panel.append_reading
            sequence.update = panel.update_readings
            sequence.state = panel.state
        sequence.show_measurement = show_measurement
        sequence.push_summary = self.on_push_summary
        sequence.start()

    def on_measurement_state(self, item, state):
        item.state = state

    def on_sequence_stop(self):
        self.stop_button.enabled = False
        sequence = self.processes.get("sequence")
        sequence.stop()

    def on_sequence_finished(self):
        self.sample_groupbox.enabled = True
        self.table_calibrate_button.enabled = True
        self.environment_groupbox.enabled = True
        self.table_groupbox.enabled = True
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self.reload_status_button.enabled = True
        self.measure_controls.enabled = True
        self.output_groupbox.enabled = True
        self.panels.unlock()
        self.sequence_tree.unlock()
        sequence = self.processes.get("sequence")
        sequence.set("sample_name", None)
        sequence.set("output_dir", None)
        sequence.set("contact_item", None)
        self.sync_environment_controls()

    # Table calibration

    @handle_exception
    def on_table_joystick_clicked(self):
        state = self.table_joystick_button.checked
        with self.resources.get("table") as table_resource:
            table = Venus1(table_resource)
            table.joystick = state

    @handle_exception
    def on_table_controls_start(self):
        TableControlDialog().run()
        self.sync_table_controls()

    @handle_exception
    def on_table_move_start(self):
        TableMoveDialog().run()
        self.sync_table_controls()

    @handle_exception
    def on_table_calibrate_start(self):
        TableCalibrateDialog().run()
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

    def switch_off_lights(self):
        with self.processes.get("environment") as environment:
            if environment.has_lights():
                environment.dim_lights()

    @handle_exception
    def sync_environment_controls(self):
        """Syncronize environment controls."""
        if self.environment_groupbox.checked:
            try:
                with self.processes.get("environment") as environment:
                    pc_data = environment.pc_data()
            except:
                self.environment_groupbox.checked = False
                raise
            else:
                self.box_laser_button.checked = pc_data.relay_states.laser_sensor
                self.box_light_button.checked = pc_data.relay_states.box_light
                self.microscope_light_button.checked = pc_data.relay_states.microscope_light
                self.microscope_camera_button.checked = pc_data.relay_states.microscope_camera
                self.microscope_control_button.checked = pc_data.relay_states.microscope_control
                self.probecard_light_button.checked = pc_data.relay_states.probecard_light
                self.probecard_camera_button.checked = pc_data.relay_states.probecard_camera
                self.pid_control_button.checked = pc_data.pid_status

    @handle_exception
    def sync_table_controls(self):
        """Syncronize table controls."""
        try:
            with self.resources.get("table") as table_resource:
                table = Venus1(table_resource)
                joystick_state = table.joystick
        except:
            self.table_groupbox.checked = False
            raise
        else:
            self.table_joystick_button.checked = joystick_state

    def on_environment_groupbox_toggled(self, state):
        self.settings["use_environ"] = state
        if state:
            self.sync_environment_controls()

    def on_table_groupbox_toggled(self, state):
        self.settings["use_table"] = state
        if self.table_groupbox.checked:
            self.sync_table_controls()

    def on_output_changed(self, value):
        self.settings["output_path"] = value

    def on_select_output(self):
        value = comet.directory_open(
            title="Select working directory",
            path=self.output_text.value
        )
        if value:
            self.output_text.value = value

    @handle_exception
    def on_push_summary(self, *args):
        """Push rsult to summary and write to sumamry file (experimantal)."""
        item = self.summary_tree.append_result(*args)
        output_path = self.settings.get("output_path")
        if output_path and os.path.exists(output_path):
            filename = os.path.join(output_path, SUMMARY_FILENAME)
            has_header = os.path.exists(filename)
            with open(filename, 'a') as f:
                header = self.summary_tree.header_items
                writer = CSVFormatter(f)
                for key in header:
                    writer.add_column(key)
                if not has_header:
                    writer.write_header()
                writer.write_row({header[i]: item[i].value for i in range(len(header))})

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
        self.switch_off_lights()
        self.sync_environment_controls()
        self.table_calibrate_button.enabled = False
        self.environment_groupbox.enabled = False
        self.table_groupbox.enabled = False
        self.measure_restore_button.enabled = False
        self.measure_run_button.enabled = False
        self.measure_stop_button.enabled = True
        self.sample_groupbox.enabled = False
        self.sequence_groupbox.enabled = False
        self.output_groupbox.enabled = False
        self.reload_status_button.enabled = False
        self.panels.lock()
        self.sequence_tree.lock()
        measurement = self.sequence_tree.current
        panel = self.panels.get(measurement.type)
        panel.store()
        # TODO
        panel.clear_readings()
        sample_name = self.sample_name_text.value
        sample_type = self.sample_type_text.value
        output_dir = self.create_output_dir()
        measure = self.processes.get("measure")
        measure.set("sample_name", sample_name)
        measure.set("sample_type", sample_type)
        measure.set("output_dir", output_dir)
        measure.set("use_environ", self.environment_groupbox.checked)
        measure.set("use_table", self.table_groupbox.checked)
        measure.measurement_item = measurement
        measure.reading = panel.append_reading
        measure.update = panel.update_readings
        measure.state = panel.state
        measure.push_summary = self.on_push_summary
        # TODO
        measure.start()

    def on_measure_stop(self):
        self.measure_restore_button.enabled = False
        self.measure_run_button.enabled = False
        self.measure_stop_button.enabled = False
        measure = self.processes.get("measure")
        measure.stop()

    def on_measure_finished(self):
        self.sync_environment_controls()
        self.table_calibrate_button.enabled = True
        self.environment_groupbox.enabled = True
        self.table_groupbox.enabled = True
        self.measure_restore_button.enabled = True
        self.measure_run_button.enabled = True
        self.measure_stop_button.enabled = False
        self.sample_groupbox.enabled = True
        self.sequence_groupbox.enabled = True
        self.output_groupbox.enabled = True
        self.reload_status_button.enabled = True
        self.panels.unlock()
        measure = self.processes.get("measure")
        measure.reading = lambda data: None
        self.sequence_tree.unlock()

    def on_status_start(self):
        self.enabled = False
        self.matrix_model_text.value = ""
        self.matrix_channels_text.value = ""
        self.hvsrc_model_text.value = ""
        self.vsrc_model_text.value = ""
        self.lcr_model_text.value = ""
        self.elm_model_text.value = ""
        self.table_model_text.value = ""
        self.table_state_text.value = ""
        self.env_model_text.value = ""
        self.env_box_temperature_text.value = ""
        self.env_box_humidity_text.value = ""
        self.env_chuck_temperature_text.value = ""
        self.env_lux_text.value = ""
        self.env_light_text.value = ""
        self.env_door_text.value = ""
        self.reload_status_button.enabled = False
        status = self.processes.get("status")
        status.set("use_environ", self.environment_groupbox.checked)
        status.set("use_table", self.table_groupbox.checked)
        status.start()

    def on_status_finished(self):
        self.enabled = True
        self.reload_status_button.enabled = True
        status = self.processes.get("status")
        self.matrix_model_text.value = status.get("matrix_model") or "n/a"
        self.matrix_channels_text.value = status.get("matrix_channels")
        self.hvsrc_model_text.value = status.get("hvsrc_model") or "n/a"
        self.vsrc_model_text.value = status.get("vsrc_model") or "n/a"
        self.lcr_model_text.value = status.get("lcr_model") or "n/a"
        self.elm_model_text.value = status.get("elm_model") or "n/a"
        self.table_model_text.value = status.get("table_model") or "n/a"
        self.table_state_text.value = status.get("table_state") or "n/a"
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
        if not filename:
            return
        try:
            sequence = config.load_sequence(filename)
        except Exception as e:
            logging.error(e)
            comet.show_exception(e)
            return
        # backup callback
        on_changed = self.sequence_combobox.changed
        self.sequence_combobox.changed = None
        for item in self.sequence_combobox:
            if item.id == sequence.id or item.name == sequence.name:
                result = comet.show_question(
                    title="Sequence already loaded",
                    text=f"Do you want to replace already loaded sequence '{sequence.name}'?"
                )
                if result:
                    self.sequence_combobox.remove(item)
                    break
                else:
                    self.sequence_combobox.changed = on_changed
                    return
        sequence.name = f"{sequence.name} (custom)"
        self.sequence_combobox.append(sequence)
        # Restore callback
        self.sequence_combobox.changed = on_changed
        self.sequence_combobox.current = sequence
        custom_sequences = self.settings.get("custom_sequences") or []
        if filename not in custom_sequences:
            custom_sequences.append(filename)
        self.settings["custom_sequences"] = custom_sequences
        self.settings["current_sequence_id"] = sequence.id

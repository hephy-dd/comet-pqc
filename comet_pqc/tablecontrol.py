"""Table control widgets and dialogs."""

import math

import comet
import comet.ui as ui
from comet.settings import SettingsMixin

from comet_pqc.utils import format_table_unit
from comet_pqc.utils import from_table_unit, to_table_unit
from comet_pqc.utils import format_metric

from .components import PositionLabel
from .components import ToggleButton
from .settings import settings, TablePosition
from .utils import format_switch

from qutie.qutie import Qt

import logging

def safe_z_position(z):
    z_limit = settings.table_z_limit
    if z > z_limit:
        ui.show_warning(
            title="Z Warning",
            text=f"Limiting Z movement to {z_limit:.3f} mm to protect probe card."
        )
        z = z_limit
    return z

class LinearTransform:
    """Linear transformation of n coordinates between two points."""

    def calculate(self, a, b, n):
        diff_x = (a[0] - b[0]) / n
        diff_y = (a[1] - b[1]) / n
        diff_z = (a[2] - b[2]) / n
        return [(a[0] - diff_x * i, a[1] - diff_y * i, a[2] - diff_z * i) for i in range(n + 1)]

class TableSampleItem(ui.TreeItem):

    def __init__(self, sample_item):
        super().__init__()
        for i in range(1, 4):
            self[i].qt.setTextAlignment(i, Qt.AlignTrailing|Qt.AlignVCenter)
        self.sample_item = sample_item
        self.name = sample_item.name
        for contact_item in sample_item.children:
            self.append(TableContactItem(contact_item))

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    def update_contacts(self):
        for contact_item in self.children:
            contact_item.update_contact()
            logging.info("updated contact position: %s %s %s", self.name, contact_item.name, contact_item.position)

    def calculate_positions(self):
        tr = LinearTransform()
        count = len(self.children)
        if count > 2:
            first = self.children[0].position
            last = list(self.children)[-1].position
            for i, position in enumerate(tr.calculate(first, last, count - 1)):
                self.children[i].position = position

class TableContactItem(ui.TreeItem):

    def __init__(self, contact_item):
        super().__init__()
        for i in range(1, 4):
            self[i].qt.setTextAlignment(i, Qt.AlignTrailing|Qt.AlignVCenter)
        self.contact_item = contact_item
        self.name = contact_item.name
        self.position = contact_item.position

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        x, y, z = value
        self.__position = x, y, z
        self[1].value = format(x, '.3f') if x is not None else None
        self[2].value = format(y, '.3f') if y is not None else None
        self[3].value = format(z, '.3f') if z is not None else None

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.__position))

    def update_contact(self):
        self.contact_item.position = self.position

    def reset_position(self):
        self.__position = float('nan'), float('nan'), float('nan')

class TableContactsWidget(ui.Row):

    def __init__(self, position_picked=None, absolute_move=None):
        super().__init__()
        self.position_picked = position_picked
        self.absolute_move = absolute_move
        self.contacts_tree = ui.Tree(
            header=("Contact", "X", "Y", "Z", None),
            selected=self.on_contacts_selected
        )
        self.contacts_tree.fit()
        self.pick_button = ui.Button(
            text="Assign &Position",
            tool_tip="Assign current table position to selected position item",
            clicked=self.on_pick_position,
            enabled=False
        )
        self.calculate_button= ui.Button(
            text="&Calculate",
            clicked=self.on_calculate,
            enabled=False
        )
        self.move_button= ui.Button(
            text="&Move",
            tool_tip="Move to selected position",
            clicked=self.on_move,
            enabled=False
        )
        self.reset_button = ui.Button(
            text="&Reset",
            clicked=self.on_reset,
            enabled=False
        )
        self.reset_all_button = ui.Button(
            text="Reset &All",
            clicked=self.on_reset_all
        )
        self.append(self.contacts_tree)
        self.append(ui.Column(
            self.pick_button,
            self.move_button,
            self.calculate_button,
            ui.Spacer(),
            self.reset_button,
            self.reset_all_button
        ))
        self.stretch = 1, 0

    def append_sample(self, sample_item):
        self.contacts_tree.append(TableSampleItem(sample_item))

    def on_contacts_selected(self, item):
        self.update_button_states(item)

    def update_button_states(self, item=None):
        if item is None:
            item = self.contacts_tree.current
        is_contact = isinstance(item, TableContactItem)
        self.pick_button.enabled = is_contact
        self.move_button.enabled = item.has_position if is_contact else False
        self.calculate_button.enabled = not is_contact
        self.reset_button.enabled = is_contact

    def on_pick_position(self):
        item = self.contacts_tree.current
        if isinstance(item, TableContactItem):
            def callback(x, y, z):
                item.position = x, y, z
                self.contacts_tree.fit()
            self.emit(self.position_picked, callback)

    def on_reset(self):
        item = self.contacts_tree.current
        if isinstance(item, TableContactItem):
            item.position = float('nan'), float('nan'), float('nan')
            self.contacts_tree.fit()

    def on_reset_all(self):
        if ui.show_question("Do you want to reset all contact positions?"):
            for sample_item in self.contacts_tree:
                for contact_item in sample_item.children:
                    contact_item.position = float('nan'), float('nan'), float('nan')
            self.contacts_tree.fit()

    def on_move(self):
        current_item = self.contacts_tree.current
        if isinstance(current_item, TableContactItem):
            if current_item.has_position:
                if ui.show_question(f"Do you want to move tabel to contact {current_item.name}?"):
                    x, y, z = current_item.position
                    self.emit(self.absolute_move, x, y, z)

    def on_calculate(self):
        current_item = self.contacts_tree.current
        if isinstance(current_item, TableSampleItem):
            current_item.calculate_positions()

    def load_samples(self, sample_items):
        self.contacts_tree.clear()
        for sample_item in sample_items:
            self.append_sample(sample_item)
        self.contacts_tree.fit()

    def update_samples(self):
        for sample_item in self.contacts_tree:
            sample_item.update_contacts()

    def lock(self):
        self.pick_button.enabled = False
        self.move_button.enabled = False
        self.calculate_button.enabled = False
        self.reset_button.enabled = False
        self.reset_all_button.enabled = False

    def unlock(self):
        self.update_button_states()
        self.reset_all_button.enabled = True

class TablePositionItem(ui.TreeItem):

    def __init__(self, name, x, y, z, comment=None):
        super().__init__()
        for i in range(1, 4):
            self[i].qt.setTextAlignment(i, Qt.AlignTrailing|Qt.AlignVCenter)
        self.name = name
        self.position = x, y, z
        self.comment = comment or ''

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        x, y, z = value
        self.__position = x, y, z
        self[1].value = format(x, '.3f')
        self[2].value = format(y, '.3f')
        self[3].value = format(z, '.3f')

    @property
    def comment(self):
        return self[4].value

    @comment.setter
    def comment(self, value):
        self[4].value = value

class PositionDialog(ui.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_text = ui.Text(value="Unnamed")
        self.x_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.y_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.z_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.comment_text = ui.Text()
        self.button_box = ui.DialogButtonBox(buttons=("ok", "cancel"), accepted=self.accept, rejected=self.reject)
        self.layout = ui.Column(
            ui.Label("Name", tool_tip="Position name"),
            self.name_text,
            ui.Label("X", tool_tip="Position X coordinate"),
            self.x_number,
            ui.Label("Y", tool_tip="Position Y coordinate"),
            self.y_number,
            ui.Label("Z", tool_tip="Position Z coordinate"),
            self.z_number,
            ui.Label("Comment", tool_tip="Optional position comment"),
            self.comment_text,
            self.button_box
        )

    @property
    def name(self):
        return self.name_text.value

    @name.setter
    def name(self, value):
        self.name_text.value = value

    @property
    def position(self):
        x = self.x_number.value
        y = self.y_number.value
        z = self.z_number.value
        return x, y, z

    @position.setter
    def position(self, value):
        x, y, z = value
        self.x_number.value = x
        self.y_number.value = y
        self.z_number.value = z

    @property
    def comment(self):
        return self.comment_text.value

    @comment.setter
    def comment(self, value):
        self.comment_text.value = value

class TablePositionsWidget(ui.Row, SettingsMixin):

    def __init__(self, position_picked=None, absolute_move=None):
        super().__init__()
        self.position_picked = position_picked
        self.absolute_move = absolute_move
        self.positions_tree = ui.Tree(
            header=("Name", "X", "Y", "Z", "Comment"),
            root_is_decorated=False,
            selected=self.on_position_selected,
            double_clicked=self.on_position_double_clicked
        )
        self.pick_button = ui.Button(
            text="Assign &Position",
            tool_tip="Assign current table position to selected position item",
            clicked=self.on_pick_position,
            enabled=False
        )
        self.add_button = ui.Button(
            text="&Add",
            tool_tip="Add new position item",
            clicked=self.on_add_position
        )
        self.edit_button = ui.Button(
            text="&Edit",
            tool_tip="Edit selected position item",
            clicked=self.on_edit_position,
            enabled=False
        )
        self.remove_button = ui.Button(
            text="&Remove",
            tool_tip="Remove selected position item",
            clicked=self.on_remove_position,
            enabled=False
        )
        self.move_button= ui.Button(
            text="&Move",
            tool_tip="Move to selected position",
            clicked=self.on_move,
            enabled=False
        )
        self.append(self.positions_tree)
        self.append(ui.Column(
            self.pick_button,
            self.move_button,
            ui.Spacer(),
            self.add_button,
            self.edit_button,
            self.remove_button
        ))
        self.stretch = 1, 0

    def load_settings(self):
        self.positions_tree.clear()
        for position in settings.table_positions:
            self.positions_tree.append(TablePositionItem(
                name=position.name,
                x=position.x,
                y=position.y,
                z=position.z,
                comment=position.comment,
            ))
        self.positions_tree.fit()

    def store_settings(self):
        positions = []
        for position in self.positions_tree:
            x, y, z = position.position
            positions.append(TablePosition(
                name=position.name,
                x=x,
                y=y,
                z=z,
                comment=position.comment
            ))
        settings.table_positions = positions

    def lock(self):
        self.pick_button.enabled = False
        self.add_button.enabled = False
        self.edit_button.enabled = False
        self.remove_button.enabled = False
        self.move_button.enabled = False
        # Remove event
        self.positions_tree.double_clicked = None

    def unlock(self):
        enabled = self.positions_tree.current is not None
        self.pick_button.enabled = enabled
        self.add_button.enabled = True
        self.edit_button.enabled = enabled
        self.remove_button.enabled = enabled
        self.move_button.enabled = enabled
        # Restore event
        self.positions_tree.double_clicked = self.on_position_double_clicked

    def on_position_selected(self, item):
        enabled = item is not None
        self.pick_button.enabled = True
        self.edit_button.enabled = True
        self.remove_button.enabled = True
        self.move_button.enabled = True

    def on_position_double_clicked(self, *args):
        self.on_move()

    def on_pick_position(self):
        item = self.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to assign current position to '{item.name}'?"):
                def callback(x, y, z):
                    item.position = x, y, z
                    self.positions_tree.fit()
                self.emit(self.position_picked, callback)

    def on_add_position(self):
        dialog = PositionDialog()
        if dialog.run():
            name = dialog.name
            x, y, z = dialog.position
            comment = dialog.comment
            self.positions_tree.append(TablePositionItem(name, x, y, z, comment))
            self.positions_tree.fit()

    def on_edit_position(self):
        item = self.positions_tree.current
        if item:
            dialog = PositionDialog()
            dialog.name = item.name
            dialog.position = item.position
            dialog.comment = item.comment
            if dialog.run():
                item.name = dialog.name
                item.position = dialog.position
                item.comment = dialog.comment
                self.positions_tree.fit()

    def on_remove_position(self):
        item = self.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to remove position '{item.name}'?"):
                self.positions_tree.remove(item)
                if not len(self.positions_tree):
                    self.pick_button.enabled = False
                    self.edit_button.enabled = False
                    self.remove_button.enabled = False
                self.positions_tree.fit()

    def on_move(self):
        item = self.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to move table to position '{item.name}'?"):
                x, y ,z = item.position
                self.emit(self.absolute_move, x, y, z)

class TableControlDialog(ui.Dialog, SettingsMixin):

    process = None

    default_steps = [
        {"step_size": 1.0, "step_color": "green"}, # microns!
        {"step_size": 10.0, "step_color": "orange"},
        {"step_size": 100.0, "step_color": "red"},
    ]

    maximum_z_step_size = 0.025 # mm
    z_limit = 0.0

    probecard_light_toggled = None
    microscope_light_toggled = None
    box_light_toggled = None

    def __init__(self, process):
        super().__init__()
        self.mount(process)
        self.resize(640, 480)
        self.title = "Table Control"
        self.add_x_button = KeypadButton(
            text="+X",
            clicked=self.on_add_x
        )
        self.sub_x_button = KeypadButton(
            text="-X",
            clicked=self.on_sub_x
        )
        self.add_y_button = KeypadButton(
            text="+Y",
            clicked=self.on_add_y
        )
        self.sub_y_button = KeypadButton(
            text="-Y",
            clicked=self.on_sub_y
        )
        self.add_z_button = KeypadButton(
            text="+Z",
            clicked=self.on_add_z
        )
        self.sub_z_button = KeypadButton(
            text="-Z",
            clicked=self.on_sub_z
        )
        self.control_buttons = (
            self.add_x_button,
            self.sub_x_button,
            self.add_y_button,
            self.sub_y_button,
            self.add_z_button,
            self.sub_z_button
        )
        self.probecard_light_button = ToggleButton(
            text="PC Light",
            tool_tip="Toggle probe card light",
            checkable=True,
            checked=False,
            enabled=False,
            toggled=self.on_probecard_light_clicked
        )
        self.microscope_light_button = ToggleButton(
            text="Mic Light",
            tool_tip="Toggle microscope light",
            checkable=True,
            checked=False,
            enabled=False,
            toggled=self.on_microscope_light_clicked
        )
        self.box_light_button = ToggleButton(
            text="Box Light",
            tool_tip="Toggle box light",
            checkable=True,
            checked=False,
            enabled=False,
            toggled=self.on_box_light_clicked
        )
        # Create movement radio buttons
        self.step_width_buttons = ui.Column()
        for item in self.load_table_step_sizes():
            step_size = item.get('step_size') * comet.ureg('um')
            step_color = item.get('step_color')
            step_size_label = format_metric(step_size.to('m').m, 'm', decimals=1)
            button = ui.RadioButton(
                text=step_size_label,
                tool_tip=f"Move in {step_size_label} steps.",
                stylesheet=f"QRadioButton:enabled{{color:{step_color};}}",
                checked=len(self.step_width_buttons) == 0,
                toggled=self.on_step_toggled
            )
            button.movement_width = step_size.to('mm').m
            button.movement_color = step_color
            self.step_width_buttons.append(button)
        self.control_layout = ui.Column(
            ui.Row(
                ui.Row(
                    ui.Column(
                        KeypadSpacer(),
                        self.sub_y_button,
                        KeypadSpacer()
                    ),
                    ui.Column(
                        self.sub_x_button,
                        KeypadSpacer(),
                        self.add_x_button,
                    ),
                    ui.Column(
                        KeypadSpacer(),
                        self.add_y_button,
                        KeypadSpacer(),
                    ),
                    KeypadSpacer(),
                    ui.Column(
                        self.add_z_button,
                        KeypadSpacer(),
                        self.sub_z_button
                    )
                ),
                ui.Spacer(),
                stretch=(0, 1)
            ),
            ui.Spacer(),
            stretch=(0, 1)
        )
        self.positions_widget = TablePositionsWidget(
            position_picked=self.on_position_picked,
            absolute_move=self.on_absolute_move
        )
        self.contacts_widget = TableContactsWidget(
            position_picked=self.on_position_picked,
            absolute_move=self.on_absolute_move
        )
        self.pos_x_label = PositionLabel()
        self.pos_y_label = PositionLabel()
        self.pos_z_label = PositionLabel()
        self.cal_x_label = CalibrationLabel("cal")
        self.cal_y_label = CalibrationLabel("cal")
        self.cal_z_label = CalibrationLabel("cal")
        self.rm_x_label = CalibrationLabel("rm")
        self.rm_y_label = CalibrationLabel("rm")
        self.rm_z_label = CalibrationLabel("rm")
        self.z_limit_label = PositionLabel()
        self.laser_label = SwitchLabel()
        self.calibrate_button = ui.Button(
            text="Calibrate",
            clicked=self.on_calibrate
        )
        self.update_interval_number = ui.Number(
            value = self.settings.get("table_control_update_interval") or 1.0,
            minimum=.5,
            maximum=10.0,
            decimals=2,
            step=0.25,
            suffix="s",
            changed=self.on_update_interval_changed
        )
        self.progress_bar = ui.ProgressBar(
            visible=False
        )
        self.message_label = ui.Label()
        self.stop_button = ui.Button(
            text="&Stop",
            default=False,
            auto_default=False,
            enabled=False,
            clicked=self.on_stop
        )
        self.close_button = ui.Button(
            text="&Close",
            default=False,
            auto_default=False,
            clicked=self.on_close
        )
        self.layout = ui.Column(
            ui.Row(
                ui.Column(
                    ui.Row(
                        ui.GroupBox(
                            title="Control",
                            layout=ui.Column(
                                ui.Spacer(horizontal=False),
                                self.control_layout,
                                ui.Spacer(horizontal=False)
                            )
                        ),
                        ui.GroupBox(
                            title="Step Width",
                            layout=self.step_width_buttons
                        ),
                        ui.GroupBox(
                            title="Lights",
                            layout=ui.Column(
                                self.probecard_light_button,
                                self.microscope_light_button,
                                self.box_light_button,
                                ui.Spacer()
                            )
                        ),
                        stretch=(0, 1)
                    ),
                    ui.Tabs(
                        ui.Tab(
                            title="Move",
                            layout=self.positions_widget
                        ),
                        ui.Tab(
                            title="Contacts",
                            layout=self.contacts_widget
                        ),
                        ui.Tab(
                            title="Calibrate",
                            layout=ui.Column(
                                    ui.GroupBox(
                                    title="Table Calibration",
                                    layout=ui.Column(
                                        ui.Row(
                                            self.calibrate_button,
                                            ui.Label("Calibrate table by moving into cal/rm switches\nof every axis in" \
                                                     " a safe manner to protect the probe card."),
                                            stretch=(0, 1)
                                        )
                                    )
                                ),
                                ui.Spacer(),
                                stretch=(0, 1)
                            )
                        ),
                        ui.Tab(
                            title="Options",
                            layout=ui.Column(
                                ui.GroupBox(
                                    title="Update Interval",
                                    layout=ui.Row(
                                        self.update_interval_number,
                                        ui.Spacer(),
                                        stretch=(0, 1)
                                    )
                                ),
                                ui.Spacer(),
                                stretch=(0, 1)
                            )
                        )
                    ),
                    stretch=(0, 1)
                ),
                ui.Column(
                    ui.GroupBox(
                        title="Position",
                        layout=ui.Row(
                            ui.Column(
                                ui.Label("X"),
                                ui.Label("Y"),
                                ui.Label("Z")
                            ),
                            ui.Column(
                                self.pos_x_label,
                                self.pos_y_label,
                                self.pos_z_label
                            )
                        )
                    ),
                    ui.GroupBox(
                        title="Calibration",
                        layout=ui.Row(
                            ui.Column(
                                ui.Label("X"),
                                ui.Label("Y"),
                                ui.Label("Z")
                            ),
                            ui.Column(
                                self.cal_x_label,
                                self.cal_y_label,
                                self.cal_z_label
                            ),
                            ui.Column(
                                self.rm_x_label,
                                self.rm_y_label,
                                self.rm_z_label
                            ),
                            stretch=(1, 1)
                        )
                    ),
                    ui.GroupBox(
                        title="Limits",
                        layout=ui.Row(
                            ui.Column(
                                ui.Label("Z")
                            ),
                            ui.Column(
                                self.z_limit_label
                            )
                        )
                    ),
                    ui.GroupBox(
                        title="Safety",
                        layout=ui.Row(
                            ui.Label(
                                text="Laser Sensor"
                            ),
                            self.laser_label
                        )
                    ),
                    ui.Spacer()
                ),
                stretch=(1, 0)
            ),
            ui.Row(
                self.progress_bar,
                self.message_label,
                ui.Spacer(),
                self.stop_button,
                self.close_button
            ),
            stretch=(1, 0)
        )
        self.close_event = self.on_close_event
        self.reset_position()
        self.reset_caldone()
        self.update_limits()
        self.reset_safety()
        self.update_control_buttons()

    @property
    def step_width(self):
        for button in self.step_width_buttons:
            if button.checked:
                return abs(button.movement_width)
        return 0

    @property
    def step_color(self):
        for button in self.step_width_buttons:
            if button.checked:
                return button.movement_color
        return "black"

    def load_table_step_sizes(self):
        return self.settings.get("table_step_sizes") or self.default_steps

    def reset_position(self):
        self.update_position(float('nan'), float('nan'), float('nan'))

    def update_position(self, x, y ,z):
        self.current_position = x, y, z
        self.pos_x_label.value = x
        self.pos_y_label.value = y
        self.pos_z_label.value = z
        self.update_limits()
        self.update_control_buttons()

    def reset_caldone(self):
        self.cal_x_label.value = None
        self.cal_y_label.value = None
        self.cal_z_label.value = None
        self.rm_x_label.value = None
        self.rm_y_label.value = None
        self.rm_z_label.value = None

    def update_caldone(self, x, y ,z):
        self.current_caldone = x, y, z
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value >> 1) & 0x1
        self.cal_x_label.value = getcal(x)
        self.cal_y_label.value = getcal(y)
        self.cal_z_label.value = getcal(z)
        self.rm_x_label.value = getrm(x)
        self.rm_y_label.value = getrm(y)
        self.rm_z_label.value = getrm(z)

    def update_limits(self):
        x, y, z = self.current_position
        self.z_limit_label.stylesheet = ""
        if not math.isnan(z):
            if z >= self.z_limit:
                self.z_limit_label.stylesheet = "QLabel:enabled{color:red;}"

    def reset_safety(self):
        self.laser_label.value = None

    def update_safety(self, laser_sensor):
        self.laser_label.value = laser_sensor

    def update_control_buttons(self):
        x, y, z = self.current_position
        self.update_x_buttons(x)
        self.update_y_buttons(y)
        self.update_z_buttons(z)
        for button in self.control_buttons:
            button.stylesheet = f"QPushButton:enabled{{color:{self.step_color or 'black'}}}"

    def update_x_buttons(self, x):
        x_enabled = True
        if not math.isnan(x):
            if (x - self.step_width) < 0:
                x_enabled = False
        self.sub_x_button.enabled = x_enabled

    def update_y_buttons(self, y):
        y_enabled = True
        if not math.isnan(y):
            if (y - self.step_width) < 0:
                y_enabled = False
        self.sub_y_button.enabled = y_enabled

    def update_z_buttons(self, z):
        # Disable move up button for large step sizes
        z_enabled = False
        if not math.isnan(z):
            if (z + self.step_width) <= self.z_limit:
                z_enabled = True
            else:
                z_enabled = self.step_width <= self.maximum_z_step_size
        self.add_z_button.enabled = z_enabled

    def on_add_x(self):
        self.lock()
        self.process.relative_move(+self.step_width, 0, 0)

    def on_sub_x(self):
        self.lock()
        self.process.relative_move(-self.step_width, 0, 0)

    def on_add_y(self):
        self.lock()
        self.process.relative_move(0, +self.step_width, 0)

    def on_sub_y(self):
        self.lock()
        self.process.relative_move(0, -self.step_width, 0)

    def on_add_z(self):
        self.lock()
        self.process.relative_move(0, 0, +self.step_width)

    def on_sub_z(self):
        self.lock()
        self.process.relative_move(0, 0, -self.step_width)

    def on_step_toggled(self, state):
        logging.info("set table step width to %.3f mm", self.step_width)
        self.update_control_buttons()

    def on_probecard_light_clicked(self, state):
        self.emit(self.probecard_light_toggled, state)

    def on_microscope_light_clicked(self, state):
        self.emit(self.microscope_light_toggled, state)

    def on_box_light_clicked(self, state):
        self.emit(self.box_light_toggled, state)

    def update_probecard_light(self, state):
        self.probecard_light_button.checked = state

    def update_microscope_light(self, state):
        self.microscope_light_button.checked = state

    def update_box_light(self, state):
        self.box_light_button.checked = state

    def update_lights_enabled(self, state):
        self.probecard_light_button.enabled = state
        self.microscope_light_button.enabled = state
        self.box_light_button.enabled = state

    def on_move_finished(self):
        self.progress_bar.visible = False
        self.stop_button.enabled = False
        self.unlock()

    def on_calibration_finished(self):
        self.progress_bar.visible = False
        self.stop_button.enabled = False
        self.unlock()

    def on_message_changed(self, message):
        self.message_label.text = message
        logging.info(message)

    def on_progress_changed(self, a, b):
        self.progress_bar.value = a
        self.progress_bar.maximum = b
        self.progress_bar.visible = True

    def on_update_interval_changed(self, value):
        self.process.update_interval = value

    def on_position_picked(self, callback):
        x, y, z = self.current_position
        callback(x, y, z)

    def on_absolute_move(self, x, y, z):
        z = safe_z_position(z)
        self.lock()
        self.stop_button.enabled = True
        self.process.safe_absolute_move(x, y, z)

    def on_calibrate(self):
        self.lock()
        self.stop_button.enabled = True
        self.process.calibrate_table()

    def on_stop(self):
        self.stop_button.enabled = False
        self.process.stop_current_action()

    def on_close(self):
        self.close()

    def on_close_event(self):
        self.process.wait()
        return True

    def load_samples(self, sample_items):
        self.contacts_widget.load_samples(sample_items)

    def update_samples(self):
        self.contacts_widget.update_samples()

    def load_settings(self):
        width, height = self.settings.get('tablecontrol_dialog_size', (640, 480))
        self.resize(width, height)
        self.positions_widget.load_settings()
        self.z_limit = settings.table_z_limit
        self.z_limit_label.value = self.z_limit

    def store_settings(self):
        self.settings['tablecontrol_dialog_size'] = self.width, self.height
        self.positions_widget.store_settings()

    def lock(self):
        self.control_layout.enabled = False
        self.positions_widget.lock()
        self.contacts_widget.lock()
        self.close_button.enabled = False
        self.progress_bar.visible = True
        self.progress_bar.minimum = 0
        self.progress_bar.maximum = 0
        self.progress_bar.value = 0

    def unlock(self):
        self.control_layout.enabled = True
        self.positions_widget.unlock()
        self.contacts_widget.unlock()
        self.close_button.enabled = True
        self.progress_bar.visible = False

    def mount(self, process):
        """Mount table process."""
        self.unmount()
        self.process = process
        self.process.message_changed = self.on_message_changed
        self.process.progress_changed = self.on_progress_changed
        self.process.position_changed = self.update_position
        self.process.caldone_changed = self.update_caldone
        self.process.relative_move_finished = self.on_move_finished
        self.process.absolute_move_finished = self.on_move_finished
        self.process.calibration_finished = self.on_calibration_finished
        self.process.stopped = self.on_calibration_finished

    def unmount(self):
        """Unmount table process."""
        if self.process:
            self.process.message_changed = None
            self.process.progress_changed = None
            self.process.position_changed = None
            self.process.caldone_changed = None
            self.process.relative_move_finished = None
            self.process.absolute_move_finished = None
            self.process.stopped = None
            self.process = None

class CalibrationLabel(ui.Label):

    def __init__(self, prefix, value=None):
        super().__init__()
        self.prefix = prefix
        self.value = value

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value
        if value is None:
            self.text = format(float('nan'))
            self.qt.setStyleSheet("")
        else:
            self.text = f"{self.prefix} {self.__value}"
            self.qt.setStyleSheet("QLabel:enabled{color:green}" if value else "QLabel:enabled{color:red}")

class SwitchLabel(ui.Label):

    def __init__(self, value=None):
        super().__init__()
        self.value = value

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value
        if value is None:
            self.text = float('nan')
            self.qt.setStyleSheet("")
        else:
            self.text = format_switch(value)
            self.qt.setStyleSheet("QLabel:enabled{color:green}" if value else "QLabel:enabled{color:red}")

class KeypadSpacer(ui.Spacer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qt.setFixedSize(30, 30)

class KeypadButton(ui.Button):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qt.setFixedSize(32, 32)

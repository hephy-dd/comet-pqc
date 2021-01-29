import os

from comet import ui
from comet.settings import SettingsMixin

from .settings import settings
from .utils import make_path, create_icon
from .utils import format_table_unit

from comet_pqc.utils import format_table_unit
from comet_pqc.utils import from_table_unit, to_table_unit

from qutie.qutie import Qt

__all__ = [
    'ToggleButton',
    'PositionLabel',
    'DirectoryWidget',
    'OperatorComboBox',
    'CalibrationGroupBox',
    'PositionGroupBox',
    'CalibrationGroupBox'
]

class ToggleButton(ui.Button):
    """Colored checkable button."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icons = {False: create_icon(12, "grey"), True: create_icon(12, "green")}
        self.on_toggle_color(self.checked)
        self.qt.toggled.connect(self.on_toggle_color)

    def on_toggle_color(self, state):
        self.icon = self.icons[state]

class PositionLabel(ui.Label):

    def __init__(self, value=None):
        super().__init__()
        self.value = value
        self.qt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value
        if value is None:
            self.text = format(float('nan'))
        else:
            self.text = format_table_unit(to_table_unit(value))

class DirectoryWidget(ui.Row):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_combo_box = ui.ComboBox(
            editable=True,
            focus_out=self.update_locations,
            changed=self.on_location_changed,
        )
        self.location_combo_box.duplicates_enabled = False
        self.select_button = ui.Button(
            icon=make_path('assets', 'icons', 'search.svg'),
            tool_tip="Select a directory.",
            width=24,
            clicked=self.on_select_clicked
        )
        self.remove_button = ui.Button(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove directory from list.",
            width=24,
            clicked=self.on_remove_clicked
        )
        self.append(self.location_combo_box)
        self.append(self.select_button)
        self.append(self.remove_button)

    @property
    def current_location(self):
        return self.location_combo_box.qt.currentText().strip()

    @property
    def locations(self):
        locations = []
        self.update_locations()
        for i in range(len(self.location_combo_box)):
            location = self.location_combo_box.qt.itemText(i).strip()
            locations.append(self.location_combo_box.qt.itemText(i).strip())
        return locations

    def clear_locations(self):
        changed = self.location_combo_box.changed
        self.location_combo_box.changed = None
        self.location_combo_box.clear()
        self.update_locations()
        self.location_combo_box.changed = changed

    def append_location(self, value):
        self.location_combo_box.append(value)

    def on_location_changed(self, _):
        location = self.current_location
        self.remove_button.enabled = len(self.location_combo_box) > 1

    def on_select_clicked(self):
        value = ui.directory_open(
            title="Select directory",
            path=self.current_location
        )
        if value:
            for i in range(self.location_combo_box.qt.count()):
                location = self.location_combo_box.qt.itemText(i).strip()
                if location == value:
                    self.location_combo_box.qt.setCurrentIndex(i)
                    return
            self.update_locations()
            self.location_combo_box.qt.insertItem(0, value)
            self.location_combo_box.qt.setCurrentIndex(0)

    def on_remove_clicked(self):
        self.update_locations()
        if len(self.location_combo_box) > 1:
            index = self.location_combo_box.qt.currentIndex()
            if index >= 0:
                if ui.show_question(
                    title="Remove directory",
                    text=f"Do you want to remove directory '{self.location_combo_box.qt.currentText()}' from the list?"
                ):
                    self.location_combo_box.qt.removeItem(index)

    def update_locations(self):
        self.remove_button.enabled = len(self.location_combo_box) > 1
        current_text = self.location_combo_box.qt.currentText().strip()
        for i in range(self.location_combo_box.qt.count()):
            if self.location_combo_box.qt.itemText(i).strip() == current_text:
                return
        if current_text:
            self.location_combo_box.qt.insertItem(0, current_text)
            self.location_combo_box.qt.setCurrentIndex(0)

class WorkingDirectoryWidget(DirectoryWidget, SettingsMixin):

    def load_settings(self):
        self.clear_locations()
        locations = settings.output_path
        if not locations:
            locations = [os.path.join(os.path.expanduser("~"), "PQC")]
        for location in locations:
            self.append_location(location)
        self.location_combo_box.current = settings.current_output_path
        self.update_locations()

    def store_settings(self):
        self.update_locations()
        settings.output_path = self.locations
        settings.current_output_path = self.location_combo_box.current

class OperatorComboBox(ui.ComboBox, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duplicates_enabled = False

    def load_settings(self):
        self.clear()
        for operator in settings.operators:
            self.append(operator)
        self.current = settings.current_operator

    def store_settings(self):
        settings.current_operator = self.current
        operators = []
        for index in range(len(self)):
            operators.append(self.qt.itemText(index))
        settings.operators = operators

class OperatorWidget(ui.Row, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operator_combo_box = OperatorComboBox()
        self.add_button = ui.Button(
            icon=make_path('assets', 'icons', 'add.svg'),
            tool_tip="Add new operator.",
            width=24,
            clicked=self.on_add_clicked
        )
        self.remove_button = ui.Button(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove current operator from list.",
            width=24,
            clicked=self.on_remove_clicked
        )
        self.append(self.operator_combo_box)
        self.append(self.add_button)
        self.append(self.remove_button)

    def on_add_clicked(self):
        operator = ui.get_text(
            text="",
            title="Add operator",
            label="Enter name of operator to add."
        )
        if operator:
            if operator not in self.operator_combo_box:
                self.operator_combo_box.append(operator)
            self.operator_combo_box.current = operator

    def on_remove_clicked(self):
        index = self.operator_combo_box.qt.currentIndex()
        if index >= 0:
            if ui.show_question(
                title="Remove operator",
                text=f"Do you want to remove operator '{self.operator_combo_box.qt.currentText()}' from the list?"
            ):
                self.operator_combo_box.qt.removeItem(index)

    def load_settings(self):
        self.operator_combo_box.load_settings()

    def store_settings(self):
        self.operator_combo_box.store_settings()

# Table components

class PositionGroupBox(ui.GroupBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, title="Position", **kwargs)
        self.pos_x_label = ui.Label()
        self.pos_y_label = ui.Label()
        self.pos_z_label = ui.Label()
        self.layout = ui.Row(
            ui.Column(
                ui.Label("X"),
                ui.Label("Y"),
                ui.Label("Z"),
            ),
            ui.Column(
                self.pos_x_label,
                self.pos_y_label,
                self.pos_z_label
            ),
        )
        self.value = 0, 0, 0

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        x, y, z = value[:3]
        self.__value = x, y, z
        self.pos_x_label.text = format_table_unit(x)
        self.pos_y_label.text = format_table_unit(y)
        self.pos_z_label.text = format_table_unit(z)

class CalibrationGroupBox(ui.GroupBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, title="Calibration", **kwargs)
        self.cal_x_label = ui.Label()
        self.cal_y_label = ui.Label()
        self.cal_z_label = ui.Label()
        self.rm_x_label = ui.Label()
        self.rm_y_label = ui.Label()
        self.rm_z_label = ui.Label()
        self.layout = ui.Row(
            ui.Column(
                ui.Label("X"),
                ui.Label("Y"),
                ui.Label("Z"),
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
            )
        )
        self.value = 0, 0, 0

    @property
    def valid(self):
        return self.value == (3, 3, 3)

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        x, y, z = value[:3]
        self.__value = x, y, z
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value >> 1) & 0x1
        self.cal_x_label.text = "cal {}".format(getcal(x))
        self.cal_x_label.stylesheet = "color: green" if getcal(x) else "color: red"
        self.cal_y_label.text = "cal {}".format(getcal(y))
        self.cal_y_label.stylesheet = "color: green" if getcal(y) else "color: red"
        self.cal_z_label.text = "cal {}".format(getcal(z))
        self.cal_z_label.stylesheet = "color: green" if getcal(z) else "color: red"
        self.rm_x_label.text = "rm {}".format(getrm(x))
        self.rm_x_label.stylesheet = "color: green" if getrm(x) else "color: red"
        self.rm_y_label.text = "rm {}".format(getrm(y))
        self.rm_y_label.stylesheet = "color: green" if getrm(y) else "color: red"
        self.rm_z_label.text = "rm {}".format(getrm(z))
        self.rm_z_label.stylesheet = "color: green" if getrm(z) else "color: red"

class PositionsComboBox(ui.ComboBox, SettingsMixin):

    def load_settings(self):
        self.clear()
        for position in settings.table_positions:
            self.append(position)
        index = self.settings.get('current_table_position') or 0
        if 0 <= index < len(self):
            self.current = self[index]

    def store_settings(self):
        index = self.index(self.current or 0)
        self.settings['current_table_position'] = index

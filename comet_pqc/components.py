import os

from comet import ui
from comet.settings import SettingsMixin

from .utils import make_path, create_icon
from .utils import format_table_unit

__all__ = [
    'ToggleButton',
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
        self.location_combo_box.clear()
        self.update_locations()

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
        locations = self.settings.get('output_path')
        if not locations:
            locations = [os.path.join(os.path.expanduser("~"), "PQC")]
        elif isinstance(locations, str):
            locations = [locations]
        for location in locations:
            self.append_location(location)
        try:
            index = int(self.settings.get("current_output_path", 0))
        except:
            index = 0
        self.location_combo_box.qt.setCurrentIndex(index)
        self.update_locations()

    def store_settings(self):
        self.update_locations()
        self.settings['output_path'] = self.locations
        self.settings['current_output_path'] = max(0, self.location_combo_box.qt.currentIndex())

class OperatorComboBox(ui.ComboBox, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editable = True
        self.duplicates_enabled = False
        self.items = self.settings.get("operators") or []
        # Set current operator
        try:
            index = int(self.settings.get("current_operator", 0))
        except:
            index = 0
        index = max(0, min(index, len(self)))
        self.current = self[index]
        def on_operator_changed(_):
            self.settings["current_operator"] = max(0, self.qt.currentIndex())
            operators = []
            for index in range(len(self)):
                operators.append(self.qt.itemText(index))
            self.settings["operators"] = operators
        self.qt.editTextChanged.connect(on_operator_changed)
        self.qt.currentIndexChanged.connect(on_operator_changed)

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

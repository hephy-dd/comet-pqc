import math
import os

from comet import ui
from comet.settings import SettingsMixin

from .settings import settings
from .position import Position
from .utils import make_path, create_icon
from .utils import format_table_unit
from .utils import getcal, getrm

from qutie.qutie import Qt

__all__ = [
    'ToggleButton',
    'PositionLabel',
    'CalibrationLabel',
    'CalibrationWidget',
    'DirectoryWidget',
    'OperatorComboBox',
    'PositionsComboBox'
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
            self.text = format_table_unit(value)

class PositionWidget(ui.GroupBox):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Position"
        self._pos_x_label = PositionLabel()
        self._pos_y_label = PositionLabel()
        self._pos_z_label = PositionLabel()
        self.layout = ui.Row(
            ui.Column(
                ui.Label(
                    text="X",
                    tool_tip="X axis position."
                ),
                ui.Label(
                    text="Y",
                    tool_tip="Y axis position."
                ),
                ui.Label(
                    text="Z",
                    tool_tip="Z axis position."
                )
            ),
            ui.Column(
                self._pos_x_label,
                self._pos_y_label,
                self._pos_z_label
            ),
            stretch=(1, 1)
        )

    def reset_position(self):
        self.update_position(Position())

    def update_position(self, position):
        self._pos_x_label.value = position.x
        self._pos_y_label.value = position.y
        self._pos_z_label.value = position.z

class CalibrationLabel(ui.Label):

    def __init__(self, prefix, value=None):
        super().__init__()
        self.prefix = prefix
        self.value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value or float('nan')
        self.text = f"{self.prefix} {self._value}"
        if math.isnan(self._value) or not self._value:
            self.qt.setStyleSheet("QLabel:enabled{color:red}")
        else:
            self.qt.setStyleSheet("QLabel:enabled{color:green}")

class CalibrationWidget(ui.GroupBox):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Calibration"
        self._cal_x_label = CalibrationLabel("cal")
        self._cal_y_label = CalibrationLabel("cal")
        self._cal_z_label = CalibrationLabel("cal")
        self._rm_x_label = CalibrationLabel("rm")
        self._rm_y_label = CalibrationLabel("rm")
        self._rm_z_label = CalibrationLabel("rm")
        self.layout = ui.Row(
            ui.Column(
                ui.Label(
                    text="X",
                    tool_tip="X axis calibration state."
                ),
                ui.Label(
                    text="Y",
                    tool_tip="Y axis calibration state."
                ),
                ui.Label(
                    text="Z",
                    tool_tip="Z axis calibration state."
                )
            ),
            ui.Column(
                self._cal_x_label,
                self._cal_y_label,
                self._cal_z_label
            ),
            ui.Column(
                self._rm_x_label,
                self._rm_y_label,
                self._rm_z_label
            ),
            stretch=(1, 1, 1)
        )

    def reset_calibration(self):
        self.update_calibration(Position())

    def update_calibration(self, position):
        self._update_cal(position)
        self._update_rm(position)

    def _update_cal(self, position):
        self._cal_x_label.value = getcal(position.x)
        self._cal_y_label.value = getcal(position.y)
        self._cal_z_label.value = getcal(position.z)

    def _update_rm(self, position):
        self._rm_x_label.value = getrm(position.x)
        self._rm_y_label.value = getrm(position.y)
        self._rm_z_label.value = getrm(position.z)

class DirectoryWidget(ui.Row):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_combo_box = ui.ComboBox(
            editable=True,
            focus_out=self.update_locations,
            changed=self.on_location_changed,
        )
        self.location_combo_box.duplicates_enabled = False
        self.select_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'search.svg'),
            tool_tip="Select a directory.",
            clicked=self.on_select_clicked
        )
        self.remove_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove directory from list.",
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
        self.add_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'add.svg'),
            tool_tip="Add new operator.",
            clicked=self.on_add_clicked
        )
        self.remove_button = ui.ToolButton(
            icon=make_path('assets', 'icons', 'delete.svg'),
            tool_tip="Remove current operator from list.",
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

class PositionsComboBox(ui.ComboBox, SettingsMixin):

    def load_settings(self):
        self.clear()
        for position in settings.table_positions:
            self.append(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index = self.settings.get('current_table_position') or 0
        if 0 <= index < len(self):
            self.current = self[index]

    def store_settings(self):
        index = self.index(self.current or 0)
        self.settings['current_table_position'] = index

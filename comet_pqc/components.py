import os

from comet import ui
from comet.settings import SettingsMixin

from .utils import make_path, create_icon

__all__ = [
    'ToggleButton',
    'EditComboBox',
    'DirectoryWidget',
    'OperatorComboBox'
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

class EditComboBox(ui.ComboBox):

    focus_in = None
    focus_out = None

    def __init__(self, *args, editable=True, focus_in=None, focus_out=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editable = editable

        self.focus_in = focus_in
        focusInEvent = self.qt.focusInEvent
        def focus_in_event(event):
            focusInEvent(event)
            if callable(self.focus_in):
                self.focus_in()
        self.qt.focusInEvent = focus_in_event

        self.focus_out = focus_out
        focusOutEvent = self.qt.focusOutEvent
        def focus_out_event(event):
            focusOutEvent(event)
            if callable(self.focus_out):
                self.focus_out()
        self.qt.focusOutEvent = focus_out_event


class DirectoryWidget(ui.Row):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_combo_box = EditComboBox(
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

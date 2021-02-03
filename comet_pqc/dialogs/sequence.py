from comet import ui
from comet.settings import SettingsMixin

from ..components import PositionsComboBox
from ..components import OperatorWidget
from ..components import WorkingDirectoryWidget

from ..settings import settings
from ..utils import from_table_unit

__all__ = ['StartSequenceDialog', 'StartSampleDialog']

class StartSequenceDialog(ui.Dialog, SettingsMixin):

    def __init__(self, contact_item, table_enabled=False):
        super().__init__()
        self.title = "Start Sequence"
        self.contact_checkbox = ui.CheckBox(
            text="Move table and contact with Probe Card",
            checked=contact_item.has_position,
            enabled=contact_item.has_position
        )
        self.position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            changed=self.on_position_checkbox_toggled
        )
        self.positions_combobox = PositionsComboBox(
            enabled=False
        )
        self.operator_combobox = OperatorWidget()
        self.output_combobox = WorkingDirectoryWidget()
        self.button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self.button_box.qt.button(self.button_box.QtClass.Yes).setAutoDefault(False)
        self.button_box.qt.button(self.button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=f"<b>Are you sure to start sequence '{contact_item.name}'?</b>"
            ),
            ui.GroupBox(
                title="Table",
                enabled=table_enabled,
                layout=ui.Column(
                    self.contact_checkbox,
                    ui.Row(
                        self.position_checkbox,
                        self.positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self.operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self.output_combobox
                )
            ),
            self.button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self.position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self.positions_combobox.load_settings()
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self.position_checkbox.checked
        self.positions_combobox.store_settings()
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

    def move_to_position(self):
        if self.position_checkbox.checked:
            current = self.positions_combobox.current
            if current:
                index = self.positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def on_position_checkbox_toggled(self, state):
        self.positions_combobox.enabled = state

class StartSampleDialog(ui.Dialog, SettingsMixin):

    def __init__(self, sample_item, table_enabled=False):
        super().__init__()
        self.title = "Start Sequences"
        self.position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            changed=self.on_position_checkbox_toggled
        )
        self.positions_combobox = PositionsComboBox(
            enabled=False
        )
        self.operator_combobox = OperatorWidget()
        self.output_combobox = WorkingDirectoryWidget()
        self.button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self.button_box.qt.button(self.button_box.QtClass.Yes).setAutoDefault(False)
        self.button_box.qt.button(self.button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=f"<b>Are you sure to start all enabled sequences for '{sample_item.name}'?</b>"
            ),
            ui.GroupBox(
                title="Table",
                enabled=table_enabled,
                layout=ui.Column(
                    ui.Row(
                        self.position_checkbox,
                        self.positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self.operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self.output_combobox
                )
            ),
            self.button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self.position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self.positions_combobox.load_settings()
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self.position_checkbox.checked
        self.positions_combobox.store_settings()
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

    def move_to_position(self):
        if self.position_checkbox.checked:
            current = self.positions_combobox.current
            if current:
                index = self.positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def on_position_checkbox_toggled(self, state):
        self.positions_combobox.enabled = state

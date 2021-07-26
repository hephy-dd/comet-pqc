import math

import comet
from comet import ui

from .panel import BasicPanel
from ..components import PositionWidget
from ..position import Position

__all__ = ["ContactPanel"]

class ContactPanel(BasicPanel):

    type = "contact"

    def __init__(self, *args, table_move=None, table_contact=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_move = table_move
        self.table_contact = table_contact
        self.use_table = False
        self._position_valid = False
        self.title = "Contact"
        self._position_widget = PositionWidget()
        self._position_widget.title = "Contact Position"
        self._move_button = ui.Button(
            text="Move",
            tool_tip="Move table to position with safe Z position.",
            clicked=self.on_move,
            enabled=False
        )
        self._contact_button = ui.Button(
            text="Contact",
            tool_tip="Move table to position and contact with sample.",
            clicked=self.on_contact,
            enabled=False
        )
        self.layout.insert(2, ui.Row(
            self._position_widget,
            ui.GroupBox(
                title="Table Control",
                layout=ui.Column(
                    self._move_button,
                    self._contact_button,
                    ui.Spacer()
                )
            ),
            ui.Spacer(vertical=False),
            stretch=(0, 0, 1)
        ))
        self.layout.insert(3, ui.Spacer())
        self.layout.stretch = 0, 0, 0, 1

    def update_use_table(self, enabled):
        self.use_table = enabled
        self._move_button.enabled = self._position_valid and self.use_table
        self._contact_button.enabled = self._position_valid and self.use_table

    def update_position(self):
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self._position_widget.update_position(position)
        self._position_valid = not math.isnan(position.z)
        self._move_button.enabled = self._position_valid and self.use_table
        self._contact_button.enabled = self._position_valid and self.use_table

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.title_label.text = f"{self.title} &rarr; {context.name}"
        self.description_label.text = context.description
        self.update_position()

    def on_move(self):
        self._move_button.enabled = False
        self.emit(self.table_move, self.context)

    def on_contact(self):
        self._contact_button.enabled = False
        self.emit(self.table_contact, self.context)

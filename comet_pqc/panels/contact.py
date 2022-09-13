import math

from comet import ui
from PyQt5 import QtCore, QtWidgets

from ..components import PositionWidget
from ..core.position import Position
from .panel import BasicPanel

__all__ = ["ContactPanel"]


class ContactPanel(BasicPanel):

    type = "contact"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.table_move = None
        self.table_contact = None
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
        self._table_control = ui.Row(
            self._position_widget,
            ui.GroupBox(
                title="Table Control",
                layout=ui.Column(
                    self._move_button,
                    self._contact_button,
                )
            ),
            ui.Spacer(vertical=False),
            stretch=(0, 0, 1)
        )
        self.rootLayout.addWidget(self._table_control.qt, 0)
        self.rootLayout.addStretch()

    def update_use_table(self, enabled):
        self.use_table = enabled
        isLocked = self.isLocked()
        self._move_button.enabled = self._position_valid and self.use_table and not isLocked
        self._contact_button.enabled = self._position_valid and self.use_table and not isLocked

    def update_position(self):
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self._position_widget.update_position(position)
        self._position_valid = not math.isnan(position.z)
        isLocked = self.isLocked()
        self._move_button.enabled = self._position_valid and self.use_table and not isLocked
        self._contact_button.enabled = self._position_valid and self.use_table and not isLocked

    def lock(self):
        super().lock()
        self._move_button.enabled = False
        self._contact_button.enabled = False

    def unlock(self):
        super().unlock()
        self._move_button.enabled = True
        self._contact_button.enabled = True

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.titleLabel.setText(f"{self.title} &rarr; {context.name}")
        self.descriptionLabel.setText(context.description)
        self.update_position()

    def on_move(self):
        self._move_button.enabled = False
        self.emit(self.table_move, self.context)

    def on_contact(self):
        self._contact_button.enabled = False
        self.emit(self.table_contact, self.context)

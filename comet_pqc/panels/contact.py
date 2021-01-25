import logging
import math

import comet
from comet import ui

from .panel import BasicPanel
from ..components import PositionLabel

__all__ = ["ContactPanel"]

class ContactPanel(BasicPanel):

    type = "contact"

    def __init__(self, *args, table_move_to=None, table_contact=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_move_to = table_move_to
        self.table_contact = table_contact
        self.title = "Contact"
        self.pos_x_label = PositionLabel()
        self.pos_y_label = PositionLabel()
        self.pos_z_label = PositionLabel()
        self.move_to_button = ui.Button(
            text="Move to",
            tool_tip="Move table to position with safe Z distance.",
            clicked=self.on_move_to,
            enabled=False
        )
        self.contact_button = ui.Button(
            text="Contact",
            tool_tip="Move table to position and contact.",
            clicked=self.on_contact,
            enabled=False
        )
        self.layout.insert(2, ui.Row(
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
                        self.pos_z_label,
                    )
                )
            ),
            ui.GroupBox(
                title="Actions",
                layout=ui.Column(
                    self.move_to_button,
                    self.contact_button
                )
            ),
            ui.Spacer(vertical=False),
        ))

    def update_position(self):
        if self.context is None:
            x, y, z = float('nan'), float('nan'), float('nan')
        else:
            x, y, z = self.context.position
        self.pos_x_label.value = x
        self.pos_y_label.value = y
        self.pos_z_label.value = z
        enabled = not (math.isnan(z) or z is None)
        self.move_to_button.enabled = enabled
        self.contact_button.enabled = enabled

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.title_label.text = f"{self.title} &rarr; {context.name}"
        self.description_label.text = context.description
        self.update_position()

    def on_move_to(self):
        self.move_to_button.enabled = False
        self.contact_button.enabled = False
        self.emit('table_move_to', self.context)

    def on_contact(self):
        self.move_to_button.enabled = False
        self.contact_button.enabled = False
        self.emit('table_contact', self.context)

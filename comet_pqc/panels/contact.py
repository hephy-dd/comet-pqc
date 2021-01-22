import logging

import comet
from comet import ui

from .panel import PanelStub
from ..components import PositionLabel

__all__ = ["ContactPanel"]

class ContactPanel(PanelStub):

    type = "contact"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Contact"
        self.pos_x_label = PositionLabel()
        self.pos_y_label = PositionLabel()
        self.pos_z_label = PositionLabel()
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
            ui.Spacer(vertical=False),
        ))

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.title_label.text = f"{self.title} &rarr; {context.name}"
        self.description_label.text = context.description
        x, y, z = context.position
        self.pos_x_label.value = x
        self.pos_y_label.value = y
        self.pos_z_label.value = z

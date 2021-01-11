from comet import ui

from ..components import OperatorWidget
from ..components import WorkingDirectoryWidget

__all__ = ['StartSequenceDialog']

class StartSequenceDialog(ui.Dialog):

    def __init__(self, contact_item):
        super().__init__()
        self.title = "Start Sequence"
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
            stretch=(1, 0)
        )

    def load_settings(self):
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

import logging
import math

import comet
from comet import ui
from comet.settings import SettingsMixin

from .panel import BasicPanel
from ..utils import make_path
from ..sequence import SequenceManager

__all__ = ["SamplePanel"]

class SamplePanel(BasicPanel, SettingsMixin):

    type = "sample"

    sample_changed = None

    def __init__(self, sample_changed=None, **kwargs):
        super().__init__(**kwargs)
        # Properties
        self.title = "Sample"
        # Callbacks
        self.sample_changed = sample_changed
        # Layout
        self._sample_name_prefix_text = ui.Text(
            tool_tip="Sample name prefix",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_name_infix_text = ui.Text(
            tool_tip="Sample name",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_name_suffix_text = ui.Text(
            tool_tip="Sample name suffix",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_type_text = ui.Text(
            tool_tip="Sample type",
            clearable=True,
            editing_finished=self.on_sample_type_edited
        )
        self._sequence_text = ui.Text(
            readonly=True
        )
        self._sample_comment_text = ui.Text(
            tool_tip="Sample comment (optional)",
            clearable=True,
            editing_finished=self.on_sample_comment_edited
        )
        self._sequence_manager_button = ui.Button(
            icon=make_path('assets', 'icons', 'gear.svg'),
            tool_tip="Open sequence manager",
            width=24,
            clicked=self.on_sequence_manager_clicked
        )
        self._sample_groupbox = ui.GroupBox(
            title="Sample",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Name"),
                    ui.Label("Type"),
                    ui.Label("Comment"),
                    ui.Label("Sequence")
                ),
                ui.Column(
                    ui.Row(
                        self._sample_name_prefix_text,
                        self._sample_name_infix_text,
                        self._sample_name_suffix_text,
                        stretch=(3, 7, 3)
                    ),
                    self._sample_type_text,
                    self._sample_comment_text,
                    ui.Row(
                        self._sequence_text,
                        self._sequence_manager_button,
                        stretch=(1, 0)
                    )
                ),
                stretch=(0, 1)
            )
        )
        self.layout.insert(2, self._sample_groupbox)

    def on_sample_name_edited(self):
        if self.context:
            self.context.name_infix = self._sample_name_infix_text.value
            self.context.name_prefix = self._sample_name_prefix_text.value
            self.context.name_suffix = self._sample_name_suffix_text.value
            self.title_label.text = f"{self.title} &rarr; {self.context.name}"
            self.emit(self.sample_changed, self.context)

    def on_sample_type_edited(self):
        if self.context:
            self.context.sample_type = self._sample_type_text.value

    def on_sample_comment_edited(self):
        if self.context:
            self.context.comment = self._sample_comment_text.value

    def on_sequence_manager_clicked(self):
        dialog = SequenceManager()
        dialog.load_settings()
        if dialog.run():
            dialog.store_settings()
            self._sequence_text.clear()
            sequence = dialog.current_sequence
            if sequence is not None:
                # Store contact positions
                sample_contacts = {}
                for contact in self.context.children:
                    if contact.has_position:
                        sample_contacts[contact.id] = contact.position
                self._sequence_text.value = f"{sequence.name}"
                self._sequence_text.tool_tip = f"{sequence.filename}"
                self.context.load_sequence(sequence)
                # Restore contact positions
                for contact in self.context.children:
                    if contact.id in sample_contacts:
                        contact.position = sample_contacts.get(contact.id)
                self.emit(self.sample_changed, self.context)

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.title_label.text = f"{self.title} &rarr; {context.name}"
        self.description_label.text = "Current halfmoon sample"
        self._sample_name_prefix_text.value = context.name_prefix
        self._sample_name_infix_text.value = context.name_infix
        self._sample_name_suffix_text.value = context.name_suffix
        self._sample_type_text.value = context.sample_type
        self._sample_comment_text.value = context.comment
        if context.sequence:
            self._sequence_text.value = context.sequence.name
        else:
            self._sequence_text.value = ""

    def unmount(self):
        self._sample_name_prefix_text.clear()
        self._sample_name_infix_text.clear()
        self._sample_name_suffix_text.clear()
        self._sample_type_text.clear()
        self._sample_comment_text.clear()
        self._sequence_text.clear()
        super().unmount()

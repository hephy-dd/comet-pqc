import logging
import math

import comet
from comet import ui

from .panel import BasicPanel

__all__ = ["SamplePanel"]

class SamplePanel(BasicPanel):

    type = "sample"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Sample"

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.title_label.text = f"{self.title} &rarr; {context.name}"
        self.description_label.text = "Current halfmoon sample"

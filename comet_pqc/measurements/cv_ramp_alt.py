import logging
import random
import datetime
import time
import os

import comet
from comet.driver.keysight import E4980A

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

__all__ = ["CVRampAltMeasurement"]

class CVRampAltMeasurement(MatrixMeasurement):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def initialize(self, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 1)
        self.process.emit("progress", 1, 1)

    def measure(self, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def run(self):
        with self.resources.get("lcr") as lcr_resource:
            super().run(
                lcr=E4980A(lcr_resource)
            )

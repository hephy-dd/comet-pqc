import logging
import random
import datetime
import time
import os

import comet
from comet.driver.keysight import E4980A

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["CVRampAltMeasurement"]

class CVRampAltMeasurement(MatrixMeasurement):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def initialize(self, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 1)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]

        self.process.emit("state", dict(
            lcr_model=lcr_model
        ))

        self.process.emit("progress", 1, 1)

    def measure(self, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def code(self, *args, **kwargs):
        with self.resources.get("lcr") as lcr_resource:
            lcr = E4980A(lcr_resource)
            try:
                self.initialize(lcr)
                self.measure(lcr)
            finally:
                self.finalize(lcr)

import logging
import datetime
import random
import time
import os
import re

import comet
from comet.driver.keithley import K2410
from comet.driver.keysight import E4980A

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement):
    """Frequency scan."""

    type = "frequency_scan"

    def initialize(self, vsrc, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 2)

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.voltage.level,
            vsrc_current=None,
            vsrc_output=vsrc.output
        ))

        self.process.emit("progress", 2, 2)

    def measure(self, vsrc, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, vsrc, lcr):
        self.process.emit("progress", 0, 0)

        vsrc.output = False

        self.process.emit("progress", 1, 1)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            with self.resources.get("lcr") as lcr_res:
                vsrc = K2410(vsrc_res)
                lcr = E4980A(lcr_res)
                try:
                    self.initialize(vsrc, lcr)
                    self.measure(vsrc, lcr)
                finally:
                    self.finalize(vsrc, lcr)

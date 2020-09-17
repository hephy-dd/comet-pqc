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
from .measurement import format_estimate

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement):
    """Frequency scan."""

    type = "frequency_scan"

    def initialize(self, hvsrc, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 2)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.voltage.level,
            hvsrc_current=None,
            hvsrc_output=hvsrc.output
        ))

        self.process.emit("progress", 2, 2)

    def measure(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)

        hvsrc.output = False

        self.process.emit("progress", 1, 1)

    def run(self):
        with self.resources.get("hvsrc") as hvsrc_res:
            with self.resources.get("lcr") as lcr_res:
                super().run(
                    hvsrc=K2410(hvsrc_res),
                    lcr=E4980A(lcr_res)
                )

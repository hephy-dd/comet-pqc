import contextlib
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
from .mixins import AnalysisMixin
from .measurement import format_estimate

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement, AnalysisMixin):
    """Frequency scan."""

    type = "frequency_scan"

    def initialize(self, hvsrc, lcr):
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
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=K2410(es.enter_context(self.resources.get("hvsrc"))),
                lcr=E4980A(es.enter_context(self.resources.get("lcr")))
            )

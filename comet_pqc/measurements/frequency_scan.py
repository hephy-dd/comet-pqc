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

        vsrc_idn = vsrc.resource.query("*IDN?")
        logging.info("Detected VSrc: %s", vsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', vsrc_idn, re.IGNORECASE).groups()
        vsrc_model = ''.join(result) or None

        self.process.emit("progress", 1, 2)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]

        self.process.emit("state", dict(
            vsrc_model=vsrc_model,
            vsrc_voltage=vsrc.source.voltage.level,
            vsrc_current=None,
            vsrc_output=vsrc.output,
            lcr_model=lcr_model
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

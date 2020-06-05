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

    def initialize(self, smu, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 2)

        smu_idn = smu.resource.query("*IDN?")
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        self.process.emit("progress", 1, 2)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]

        self.process.emit("state", dict(
            smu_model=smu_model,
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output,
            lcr_model=lcr_model
        ))

        self.process.emit("progress", 2, 2)

    def measure(self, smu, lcr):
        pass

    def finalize(self, smu, lcr):
        self.process.emit("progress", 0, 0)

        smu.output = False

        self.process.emit("progress", 1, 1)

    def code(self, *args, **kwargs):
        with self.resources.get("smu1") as smu1_res:
            with self.resources.get("lcr") as lcr_res:
                smu1 = K2410(smu1_res)
                lcr = E4980A(lcr_res)
                try:
                    self.initialize(smu1, lcr)
                    self.measure(smu1, lcr)
                finally:
                    self.finalize(smu1, lcr)

import logging
import datetime
import random
import time
import os
import re

import comet

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement):
    """Frequency scan."""

    type = "frequency_scan"

    def initialize(self, smu, lcr):
        self.process.events.message("Initialize...")
        self.process.events.progress(0, 2)

        smu_idn = smu.resource.query("*IDN?")
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        self.process.events.progress(1, 2)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]

        self.process.events.state(dict(
            smu_model=smu_model,
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output,
            lcr_model=lcr_model
        ))

        self.process.events.progress(2, 2)

    def measure(self, smu, lcr):
        pass

    def finalize(self, smu, lcr):
        self.process.events.progress(0, 0)

        smu.output = False

        self.process.events.progress(1, 1)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("lcr") as lcr:
                try:
                    self.initialize(smu, lcr)
                    self.measure(smu, lcr)
                finally:
                    self.finalize(smu, lcr)

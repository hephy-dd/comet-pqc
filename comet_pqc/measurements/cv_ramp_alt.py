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
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        bias_voltage_start = parameters.get("bias_voltage_start").to("V").m
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        bias_voltage_stop = parameters.get("bias_voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("current", "E")
            fmt.add_column("temperature", "E")
            fmt.add_column("humidity", "E")

            # Write meta data
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("bias_voltage_start", f"{bias_voltage_start:E} V")
            fmt.write_meta("bias_voltage_stop", f"{bias_voltage_stop:E} V")
            fmt.write_meta("bias_voltage_step", f"{bias_voltage_step:E} V")
            fmt.write_meta("current_compliance", f"{current_compliance:E} A")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

    def finalize(self, lcr):
        pass

    def code(self, *args, **kwargs):
        with self.resources.get("lcr") as lcr_resource:
            lcr = E4980A(lcr_resource)
            try:
                self.initialize(lcr)
                self.measure(lcr)
            finally:
                self.finalize(lcr)

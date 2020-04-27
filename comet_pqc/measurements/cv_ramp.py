import random
import time
import os

from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["CVRampMeasurement"]

class CVRampMeasurement(MatrixMeasurement):
    """CV ramp measurement."""

    type = "cv_ramp"

    def measure(self):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name =  self.measurement_item.contact.name
        measurement_name =  self.measurement_item.name

        filename = comet.safe_filename(f"{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
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
            f.flush()

    def code(self, *args, **kwargs):
        self.measure()
        time.sleep(random.uniform(2.5, 4.0))

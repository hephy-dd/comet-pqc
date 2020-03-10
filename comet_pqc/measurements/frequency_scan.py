import random
import time

from .matrix import MatrixMeasurement

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement):
    """Frequency scan."""

    type = "frequency_scan"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

import random
import time

from .matrix import MatrixMeasurement

__all__ = ["CVRampAltMeasurement"]

class CVRampAltMeasurement(MatrixMeasurement):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

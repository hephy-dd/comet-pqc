import random
import time

from .matrix import MatrixMeasurement

__all__ = ["CVRampMeasurement"]

class CVRampMeasurement(MatrixMeasurement):
    """CV ramp measurement."""

    type = "cv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

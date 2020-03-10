import random
import time

from .matrix import MatrixMeasurement

__all__ = ["IVRamp4WireMeasurement"]

class IVRamp4WireMeasurement(MatrixMeasurement):
    """4 wire IV ramp measurement."""

    type = "4wire_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

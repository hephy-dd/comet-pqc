import random
import time

from .matrix import MatrixMeasurement

__all__ = ["IVRampBiasMeasurement"]

class IVRampBiasMeasurement(MatrixMeasurement):
    """Bias IV ramp measurement."""

    type = "bias_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

import logging
import random
import time

import comet

__all__ = [
    "measurement_factory",
    "Measurement",
    "MatrixSwitch",
    "IVRamp",
    "BiasIVRamp",
    "CVRamp",
    "CVRampAlt",
    "FourWireIVRamp"
]

def measurement_factory(type, *args, **kwargs):
    """Factory function to create a new measurement instance by type.

    >>> meas = measurement_factory("iv_ramp")
    >>> meas.run()
    """
    for cls in globals().values():
        if hasattr(cls, "type"):
            if cls.type == type:
                return cls(*args, **kwargs)

class Measurement:
    """Base measurement class."""

    type = None

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")

class MatrixSwitch(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = None

    def __init__(self):
        super().__init__()

    def setup_matrix(self):
        """Setup marix switch."""
        logging.info("setup matrix")

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"starting {self.type}")
        result = None
        exception = None
        try:
            self.reset_matrix()
            self.setup_matrix()
            result = self.code(*args, **kwargs)
        except Exception as e:
            # Re-raise exception after matrix switch reset!
            exception = e
        finally:
            # Always reset matrix switch!
            self.reset_matrix()
        if exception is not None:
            raise exception
        logging.info(f"finished {self.type}")
        return result

class IVRamp(MatrixSwitch):
    """IV ramp measurement."""

    type = "iv_ramp"

    def code(self, *args, **kwargs):
        with self.devices.get("smu1") as smu1:
            idn = smu1.identification
            logging.info("smu1: %s", idn)
        time.sleep(random.uniform(2.5, 4.0))

class BiasIVRamp(MatrixSwitch):
    """Bias IV ramp measurement."""

    type = "bias_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class CVRamp(MatrixSwitch):
    """CV ramp measurement."""

    type = "cv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class CVRampAlt(MatrixSwitch):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class FourWireIVRamp(MatrixSwitch):
    """4 wire IV ramp measurement."""

    type = "4wire_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

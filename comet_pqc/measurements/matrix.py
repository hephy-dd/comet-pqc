import logging

from .measurement import Measurement

__all__ = ["MatrixMeasurement"]

class MatrixMeasurement(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = None

    def __init__(self, process, parameters):
        super().__init__(process, parameters)

    def setup_matrix(self):
        """Setup marix switch."""
        channels = self.parameters.get("matrix_channels", [])
        logging.info("setup matrix channels: %s", channels)

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"running {self.type}...")
        matrix_enabled = self.parameters.get("matrix_enabled", False)
        result = None
        try:
            if matrix_enabled:
                self.reset_matrix()
                self.setup_matrix()
            result = self.code(*args, **kwargs)
        finally:
            if matrix_enabled:
                # Always reset matrix switch!
                self.reset_matrix()
        logging.info(f"finished {self.type}.")
        return result

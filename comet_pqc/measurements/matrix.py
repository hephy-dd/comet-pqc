import logging

from ..driver import K707B
from .measurement import Measurement

__all__ = ["MatrixMeasurement"]

class MatrixMeasurement(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = "matrix"

    default_matrix_enabled = False
    default_matrix_channels = []

    def setup_matrix(self):
        """Setup marix switch."""
        parameters = self.measurement_item.parameters
        channels = parameters.get("matrix_channels", self.default_matrix_channels)
        logging.info("close matrix channels: %s", channels)
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                closed_channels = matrix.channel.getclose()
                if closed_channels:
                    raise RuntimeError("Some matrix channels are still closed, " \
                        f"please verify the situation and open closed channels. Closed channels: {closed_channels}")
                if channels:
                    matrix.channel.close(channels)
                    closed_channels = matrix.channel.getclose()
                    if sorted(closed_channels) != sorted(channels):
                        raise RuntimeError("mismatch in closed channels")
        except Exception as e:
            raise RuntimeError(f"Failed to close matrix channels {channels}, {e.args}")

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        pass ## logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"running {self.type}...")
        parameters = self.measurement_item.parameters
        matrix_enabled = parameters.get("matrix_enabled", self.default_matrix_enabled)
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

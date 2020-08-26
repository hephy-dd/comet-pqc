import logging

from comet.driver.keithley import K707B
from .measurement import Measurement

__all__ = ["MatrixMeasurement"]

class MatrixMeasurement(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = "matrix"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('matrix_enable', False, type=bool)
        self.register_parameter('matrix_channels', [], type=list)

    def initialize_matrix(self):
        """Setup marix switch."""
        matrix_channels = self.get_parameter('matrix_channels')
        logging.info("close matrix channels: %s", matrix_channels)
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                closed_channels = matrix.channel.getclose()
                if closed_channels:
                    raise RuntimeError("Some matrix channels are still closed, " \
                        f"please verify the situation and open closed channels. Closed channels: {closed_channels}")
                if matrix_channels:
                    matrix.channel.close(matrix_channels)
                    closed_channels = matrix.channel.getclose()
                    if sorted(closed_channels) != sorted(matrix_channels):
                        raise RuntimeError("mismatch in closed channels")
        except Exception as e:
            raise RuntimeError(f"Failed to close matrix channels {matrix_channels}, {e.args}")

    def finalize_matrix(self):
        """Reset marix switch to a save state."""
        # TODO: in conflict with main initialize/finalize
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                matrix.channel.open() # open all
        except Exception as e:
            raise RuntimeError(f"Failed to open matrix channels, {e.args}")

    def run(self, *args, **kwargs):
        logging.info(f"running {self.type}...")
        matrix_enable = self.get_parameter('matrix_enable')
        result = None
        if matrix_enable:
            self.initialize_matrix()
        try:
            result = super().run(*args, **kwargs)
            logging.info(f"finished {self.type}.")
        finally:
            if matrix_enable:
                # Always reset matrix switch!
                self.finalize_matrix()
            logging.info(f"failed {self.type}.")
        return result

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

    def before_initialize(self, **kwargs):
        """Setup matrix switch."""
        super().before_initialize(**kwargs)
        matrix_enable = self.get_parameter('matrix_enable')
        if matrix_enable:
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

    def after_finalize(self, **kwargs):
        """Reset marix switch to a save state."""
        matrix_enable = self.get_parameter('matrix_enable')
        if matrix_enable:
            try:
                with self.resources.get("matrix") as matrix_res:
                    matrix = K707B(matrix_res)
                    matrix.channel.open() # open all
            except Exception as e:
                raise RuntimeError(f"Failed to open matrix channels, {e.args}")
        super().after_finalize(**kwargs)

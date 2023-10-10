import logging

from .measurement import Measurement

__all__ = ["MatrixMeasurement"]

logger = logging.getLogger(__name__)


class MatrixMeasurement(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = "matrix"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter("matrix_enable", True, type=bool)
        self.register_parameter("matrix_channels", [], type=list)

    def before_initialize(self, **kwargs):
        """Setup matrix switch."""
        super().before_initialize(**kwargs)
        matrix_enable = self.get_parameter("matrix_enable")
        if matrix_enable:
            matrix_channels = self.get_parameter("matrix_channels")
            logger.info("Matrix close channels: %s", matrix_channels)
            try:
                self.process.station.matrix.safe_close_channels(matrix_channels)
            except Exception as exc:
                raise RuntimeError(f"Failed to close matrix channels {matrix_channels}, {exc.args}") from exc

    def after_finalize(self, **kwargs):
        """Reset marix switch to a save state."""
        matrix_enable = self.get_parameter("matrix_enable")
        if matrix_enable:
            try:
                self.process.station.matrix.open_all_channels()
            except Exception as exc:
                raise RuntimeError(f"Matrix failed to open channels, {exc.args}") from exc
        super().after_finalize(**kwargs)

import logging

from .measurement import Measurement

__all__ = ["MatrixMeasurement"]

def matrix_channels_closed(resource):
    result = matrix.resource.query("print(channels.getclose(\"allslots\"))")
    if result.strip() == "nil":
        return []
    return result.split(";")

def matrix_channels_close(resource, channels):
    matrix.resource.write(";".join(channels))
    matrix.resource.query("*OPC?")

class MatrixMeasurement(Measurement):
    """Base measurement class wrapping code into matrix configuration."""

    type = "matrix"

    def setup_matrix(self):
        """Setup marix switch."""
        channels = self.measurement_item.parameters.get("matrix_channels", [])
        logging.info("close matrix channels: %s", channels)
        try:
            with self.devices.get("matrix") as matrix:
                closed = matrix_channels_closed(matrix.resource)
                if closed:
                    raise RuntimeError("Some matrix channels are still closed, " \
                        f"please verify the situation and open closed channels. Closed channels: {closed}")
                if channels:
                    matrix_channels_close(matrix.resource, channels)
                    closed = matrix_channels_closed(resource)
                    if sorted(closed) != sorted(channels):
                        raise RuntimeError("mismatch in closed channels")
        except Exception as e:
            raise RuntimeError(f"Failed to close matrix channels {channels}, {e,args}")

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        pass ## logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"running {self.type}...")
        matrix_enabled = self.measurement_item.parameters.get("matrix_enabled", False)
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

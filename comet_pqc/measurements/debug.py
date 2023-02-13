import logging
import time

from .measurement import Measurement
from .mixins import AnalysisError

__all__ = ["DebugMeasurement"]

logger = logging.getLogger(__name__)


class DebugMeasurement(Measurement):
    """Debug measurement."""

    type = "debug"

    required_instruments = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        self.process.emit("progress", 0, 1)
        # time.sleep(1)
        self.process.emit("progress", 1, 1)

    def measure(self):
        self.process.emit("progress", 0, 1)
        # time.sleep(1)
        self.process.emit("progress", 1, 1)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)
        raise AnalysisError()
        # time.sleep(1)
        self.process.emit("progress", 1, 1)

    def finalize(self):
        self.process.emit("progress", 0, 1)
        # time.sleep(1)
        self.process.emit("progress", 1, 1)

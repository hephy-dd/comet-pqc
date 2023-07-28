import logging

from .matrix import MatrixMeasurement
from .mixins import AnalysisMixin, EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["FrequencyScanMeasurement"]

logger = logging.getLogger(__name__)


class FrequencyScanMeasurement(MatrixMeasurement, HVSourceMixin, LCRMixin, EnvironmentMixin, AnalysisMixin):
    """Frequency scan."""

    type = "frequency_scan"

    required_instruments = ["hvsrc", "lcr"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_vsource()
        self.register_lcr()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc, lcr):
        self.process.emit("progress", 0, 2)

        self.process.emit("state", {
            "hvsrc_voltage": self.hvsrc_get_voltage_level(hvsrc),
            "hvsrc_current": None,
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc),
        })

        self.process.emit("progress", 2, 2)

    def measure(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)

        self.process.emit("progress", 1, 1)

import contextlib

from ..driver import K2410
from comet.driver.keysight import E4980A

from .matrix import MatrixMeasurement
from .mixins import HVSourceMixin
from .mixins import LCRMixin
from .mixins import EnvironmentMixin
from .mixins import AnalysisMixin

__all__ = ["FrequencyScanMeasurement"]

class FrequencyScanMeasurement(MatrixMeasurement, HVSourceMixin, LCRMixin, EnvironmentMixin, AnalysisMixin):
    """Frequency scan."""

    type = "frequency_scan"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_hvsource()
        self.register_lcr()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc, lcr):
        self.process.emit("progress", 0, 2)

        self.process.emit("state", dict(
            hvsrc_voltage=self.hvsrc_get_voltage_level(hvsrc),
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 2, 2)

    def measure(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)
        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 0, 0)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)

        self.process.emit("progress", 1, 1)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=self.hvsrc_create(es.enter_context(self.resources.get("hvsrc"))),
                lcr=E4980A(es.enter_context(self.resources.get("lcr")))
            )

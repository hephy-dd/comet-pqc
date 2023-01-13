import logging
import time

import comet

from ..core.resource import resource_registry
from ..settings import settings

__all__ = ["ContactQualityProcess"]

logger = logging.getLogger(__name__)


class LCRInstrument:

    def __init__(self, lcr):
        self.lcr = lcr

    def reset(self):
        self.lcr.reset()
        self.lcr.clear()
        self.lcr.configure()
        self.check_error()

    def quick_setup_cp_rp(self):
        self.safe_write(":FUNC:IMP:RANG:AUTO ON")
        self.safe_write(":FUNC:IMP:TYPE CPRP")
        self.safe_write(":APER SHOR")
        self.safe_write(":INIT:CONT OFF")
        self.safe_write(":TRIG:SOUR BUS")
        self.safe_write(":CORR:METH SING")

    def safe_write(self, message):
        self.lcr.context.resource.write(message)
        self.lcr.context.resource.query("*OPC?")
        self.check_error()

    def check_error(self):
        """Test for error."""
        error = self.lcr.next_error()
        if error is not None:
            raise RuntimeError(f"LCR Meter error {error.code}: {error.message}")

    def acquire_reading(self):
        prim, sec = self.lcr.acquire_reading()
        return prim, sec


class ContactQualityProcess(comet.Process):

    def __init__(self, update_interval=.250, matrix_channels=None, reading=None, **kwargs):
        super().__init__(**kwargs)
        self.update_interval = update_interval
        self.matrix_channels = matrix_channels or []
        self.reading = reading
        self._cached_reading = None, None

    def cached_reading(self):
        return self._cached_reading

    def close_matrix(self, channels):
        try:
            with resource_registry.get("matrix") as matrix_res:
                matrix = settings.getInstrumentType("matrix")(matrix_res)
                matrix.channel.close(channels)
                closed_channels = matrix.channel.getclose()
                if sorted(closed_channels) != sorted(channels):
                    raise RuntimeError("Matrix mismatch in closed channels")
                logger.info("Matrix: closed channels: %s", ", ".join(closed_channels))
        except Exception as exc:
            raise RuntimeError(f"Failed to close matrix channels {channels}, {exc.args}") from exc

    def open_matrix(self):
        try:
            with resource_registry.get("matrix") as matrix_res:
                matrix = settings.getInstrumentType("matrix")(matrix_res)
                matrix.channel.open()  # open all
            logger.info("Matrix: opened all channels")
        except Exception as exc:
            raise RuntimeError(f"Matrix failed to open channels, {exc.args}") from exc

    def measure(self):
        with resource_registry.get("lcr") as lcr_res:
            lcr = LCRInstrument(settings.getInstrumentType("lcr")(lcr_res))
            lcr.reset()
            lcr.quick_setup_cp_rp()
            while self.running:
                prim, sec = lcr.acquire_reading()
                self.emit(self.reading, prim, sec)
                self._cached_reading = prim, sec
                time.sleep(self.update_interval)

    def run(self):
        self._cached_reading = None, None
        try:
            self.close_matrix(self.matrix_channels)
            self.measure()
        finally:
            self._cached_reading = None, None
            self.open_matrix()

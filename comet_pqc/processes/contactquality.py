import logging
import time
from typing import List, Optional, Tuple

import comet

from ..driver.e4980a import E4980A

__all__ = ["ContactQualityProcess"]

logger = logging.getLogger(__name__)


class LCRInstrument:

    def __init__(self, resource):
        self.context = E4980A(resource)

    def reset(self):
        self.context.reset()
        self.context.clear()
        self.check_error()
        self.context.system.beeper.state = False
        self.check_error()

    def safe_write(self, message):
        self.context.resource.write(message)
        self.context.resource.query("*OPC?")
        self.check_error()

    def check_error(self):
        """Test for error."""
        code, message = self.context.system.error
        if code:
            raise RuntimeError(f"LCR Meter error {code}: {message}")

    def quick_setup_cp_rp(self):
        self.safe_write(":FUNC:IMP:RANG:AUTO ON")
        self.safe_write(":FUNC:IMP:TYPE CPRP")
        self.safe_write(":APER SHOR")
        self.safe_write(":INIT:CONT OFF")
        self.safe_write(":TRIG:SOUR BUS")
        self.safe_write(":CORR:METH SING")

    def acquire_reading(self):
        """Return primary and secondary LCR reading."""
        self.safe_write(":TRIG:IMM")
        prim, sec = self.context.fetch()[:2]
        return prim, sec


class ContactQualityProcess(comet.Process, comet.ResourceMixin):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_interval: float = 0.250  # seconds
        self.matrix_channels: List[str] = []
        self.reading = None
        self._cached_reading: Tuple = (None, None)

    def clear_cache(self) -> None:
        self._cached_reading = None, None

    def cached_reading(self) -> Tuple:
        return self._cached_reading

    def close_matrix(self, channels: List[str]) -> None:
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = self.get("matrix_instrument")(matrix_res)
                matrix.channel.close(channels)
                closed_channels = matrix.channel.getclose()
                if sorted(closed_channels) != sorted(channels):
                    raise RuntimeError(f"Matrix mismatch in closed channels: {closed_channels}")
                logger.info("Matrix: closed channels: %s", ", ".join(closed_channels))
        except Exception as exc:
            raise RuntimeError(f"Failed to close matrix channels {channels}, {exc.args}") from exc

    def open_matrix(self) -> None:
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = self.get("matrix_instrument")(matrix_res)
                matrix.channel.open()  # open all
            logger.info("Matrix: opened all channels")
        except Exception as exc:
            raise RuntimeError(f"Matrix failed to open channels, {exc.args}") from exc

    def measure(self) -> None:
        with self.resources.get("lcr") as lcr_res:
            lcr = LCRInstrument(lcr_res)
            lcr.reset()
            lcr.quick_setup_cp_rp()
            while self.running:
                prim, sec = lcr.acquire_reading()
                self.emit(self.reading, prim, sec)
                self._cached_reading = prim, sec
                time.sleep(self.update_interval)

    def run(self) -> None:
        self.clear_cache()
        try:
            self.close_matrix(self.matrix_channels)
            self.measure()
        finally:
            self.clear_cache()
            self.open_matrix()

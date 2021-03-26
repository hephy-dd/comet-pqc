import logging
import time

import comet
from comet.driver.keithley import K707B

from ..driver.e4980a import E4980A

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
        self.context.resource.write(":TRIG:IMM")
        self.context.resource.query("*OPC?")
        prim, sec = self.context.fetch()[:2]
        logging.info("LCR Meter reading: %s, %s", prim, sec)
        return prim, sec

class ContactQualityProcess(comet.Process, comet.ResourceMixin):

    def __init__(self, matrix_channels=None, reading=None, **kwargs):
        super().__init__(**kwargs)
        self.matrix_channels = matrix_channels or []
        self.reading = reading

    def close_matrix(self, channels):
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                matrix.channel.close(channels)
                closed_channels = matrix.channel.getclose()
                if sorted(closed_channels) != sorted(channels):
                    raise RuntimeError("Matrix mismatch in closed channels")
        except Exception as exc:
            raise RuntimeError(f"Failed to close matrix channels {matrix_channels}, {exc.args}") from exc

    def open_matrix(self):
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                matrix.channel.open() # open all
        except Exception as exc:
            raise RuntimeError(f"Matrix failed to open channels, {exc.args}") from exc

    def measure(self):
        with self.resources.get("lcr") as lcr_res:
            lcr = LCRInstrument(lcr_res)
            lcr.reset()
            lcr.quick_setup_cp_rp()
            while self.running:
                prim, sec = lcr.acquire_reading()
                logging.info("LCR Meter reading: %s %s", prim, sec)
                self.emit(self.reading, prim, sec)
                time.sleep(0.250)

    def run(self):
        try:
            self.close_matrix(self.matrix_channels)
            self.measure()
        finally:
            self.open_matrix()

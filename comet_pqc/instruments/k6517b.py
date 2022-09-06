import time
from typing import Tuple, Optional

from comet.driver.keithley import K6517B

from ..core.timer import Timer
from .generic import ELMInstrument, InstrumentError

__all__ = ["K6517BInstrument"]


def parse_error(response: str) -> Tuple[int, str]:
    code, message = response.split(",", 1)
    return int(code), message.strip().strip("\"")


class K6517BInstrument(ELMInstrument):

    Driver = K6517B

    def reset(self) -> None:
        self.context.reset()

    def clear(self) -> None:
        self.context.clear()

    def configure(self) -> None:
        ...

    def next_error(self) -> Optional[InstrumentError]:
        code, message = parse_error(self.context.resource.query(":SYST:ERR?"))
        if code:
            return InstrumentError(code, message)
        return None

    # Zero check

    def get_zero_check(self) -> bool:
        return bool(int(self.context.resource.query(":SYST:ZCH?")))

    def set_zero_check(self, enabled: bool) -> None:
        value = {True: "ON", False: "OFF"}[enabled]
        self.context.resource.write(f":SYST:ZCH {value}")
        self.context.resource.query("*OPC?")

    # Sense function

    def get_sense_function(self) -> str:
        return self.context.resource.query(":SENS:FUNC?").strip().strip("\"\'")

    def set_sense_function(self, function: str) -> None:
        self.context.resource.write(f":SENS:FUNC '{function}'")  # Note the quotes!
        self.context.resource.query("*OPC?")

    # Readings

    def acquire_reading(self, timeout: float, interval: float) -> float:
        self.context.resource.write("*CLS")
        self.context.resource.write("*OPC")
        self.context.resource.write(":INIT")
        t = Timer()
        interval = min(timeout, interval)
        while t.delta() < timeout:
            # Read event status
            if int(self.context.resource.query("*ESR?")) & 0x1:
                try:
                    result = self.context.resource.query(":FETCH?")
                    return float(result.split(",")[0])
                except Exception as exc:
                    raise RuntimeError(f"Failed to fetch Electrometer reading: {exc}") from exc
            time.sleep(interval)
        raise TimeoutError(f"Electrometer reading timeout, exceeded {timeout:G} s")

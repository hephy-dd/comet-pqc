from typing import Tuple, Optional

from ..driver.e4980a import E4980A

from .generic import LCRInstrument, InstrumentError

__all__ = ["E4980AInstrument"]


class E4980AInstrument(LCRInstrument):

    Driver = E4980A

    def reset(self) -> None:
        self.context.reset()

    def clear(self) -> None:
        self.context.clear()

    def configure(self) -> None:
        self.context.system.beeper.state = False

    def next_error(self) -> Optional[InstrumentError]:
        code, message = self.context.system.error
        if code:
            return InstrumentError(code, message)
        return None

    # Bias

    def get_bias_voltage_level(self) -> float:
        return self.context.bias.voltage.level

    def set_bias_voltage_level(self, voltage: float) -> None:
        self.context.bias.voltage.level = voltage

    def get_bias_polarity_current_level(self) -> float:
        return self.context.bias.polarity.current.level

    def get_bias_state(self) -> bool:
        return self.context.bias.state

    def set_bias_state(self, enabled: bool) -> None:
        self.context.bias.state = enabled

    # Readings

    def acquire_reading(self) -> Tuple[float, float]:
        self.context.resource.write("TRIG:IMM")
        prim, sec = self.context.fetch()[:2]
        return prim, sec

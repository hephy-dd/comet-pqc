from abc import abstractmethod
from typing import Tuple

from .instrument import Instrument, InstrumentError

__all__ = ["LCRInstrument"]


class LCRInstrument(Instrument):

    # Bias

    @abstractmethod
    def get_bias_voltage_level(self) -> float:
        ...

    @abstractmethod
    def set_bias_voltage_level(self, voltage: float) -> None:
        ...

    @abstractmethod
    def get_bias_polarity_current_level(self) -> float:
        ...

    @abstractmethod
    def get_bias_state(self) -> bool:
        ...

    @abstractmethod
    def set_bias_state(self, enabled: bool) -> None:
        ...

    # Readings

    @abstractmethod
    def acquire_reading(self) -> Tuple[float, float]:
        ...

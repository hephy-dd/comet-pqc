from abc import abstractmethod
from typing import Tuple

from .instrument import Instrument, InstrumentError

__all__ = ["ELMInstrument"]


class ELMInstrument(Instrument):

    # Zero check

    @abstractmethod
    def get_zero_check(self) -> bool:
        ...

    @abstractmethod
    def set_zero_check(self, enabled: bool) -> None:
        ...

    # Sense function

    @abstractmethod
    def get_sense_function(self) -> str:
        ...

    @abstractmethod
    def set_sense_function(self, function: str) -> None:
        ...

    # Readings

    @abstractmethod
    def acquire_reading(self, timeout, interval) -> float:
        ...

from abc import ABC, abstractmethod
from typing import Optional

from comet.driver import Driver

__all__ = ["Instrument", "InstrumentError"]


class InstrumentError:
    """Instrument error consisting of error code and message."""

    def __init__(self, code: int, message: str) -> None:
        self.code: int = code
        self.message: str = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}, {self.message!r})"


class Instrument(ABC):

    Driver: Driver = Driver

    def __init__(self, resource) -> None:
        self.context: Driver = type(self).Driver(resource)

    @abstractmethod
    def reset(self) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def configure(self) -> None:
        ...

    @abstractmethod
    def next_error(self) -> Optional[InstrumentError]:
        ...

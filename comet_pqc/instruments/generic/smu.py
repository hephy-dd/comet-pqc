from abc import abstractmethod
from typing import Tuple

from .instrument import Instrument, InstrumentError

__all__ = ["SMUInstrument"]


class SMUInstrument(Instrument):

    # Output

    OUTPUT_ON: str = "ON"
    OUTPUT_OFF: str = "OFF"
    OUTPUT_OPTIONS: Tuple[str, ...] = (
        OUTPUT_ON,
        OUTPUT_OFF
    )

    @abstractmethod
    def get_output(self) -> str:
        ...

    @abstractmethod
    def set_output(self, value: str) -> None:
        ...

    # Source function

    SOURCE_FUNCTION_VOLTAGE: str = "VOLTAGE"
    SOURCE_FUNCTION_CURRENT: str = "CURRENT"
    SOURCE_FUNCTION_OPTIONS: Tuple[str, ...] = (
        SOURCE_FUNCTION_VOLTAGE,
        SOURCE_FUNCTION_CURRENT
    )

    @abstractmethod
    def get_source_function(self) -> str:
        ...

    @abstractmethod
    def set_source_function(self, value: str) -> None:
        ...

    # Source voltage

    SOURCE_VOLTAGE_MINIMUM: float = -1000.0
    SOURCE_VOLTAGE_MAXIMUM: float = +1000.0

    @abstractmethod
    def get_source_voltage(self) -> float:
        ...

    @abstractmethod
    def set_source_voltage(self, value: float) -> None:
        ...

    # Source current

    SOURCE_CURRENT_MINIMUM: float = -1.0
    SOURCE_CURRENT_MAXIMUM: float = +1.0

    @abstractmethod
    def get_source_current(self) -> float:
        ...

    @abstractmethod
    def set_source_current(self, value: float) -> None:
        ...

    # Source voltage range

    @abstractmethod
    def get_source_voltage_range(self) -> float:
        ...

    @abstractmethod
    def set_source_voltage_range(self, value: float) -> None:
        ...

    # Source voltage autorange

    @abstractmethod
    def get_source_voltage_autorange(self) -> bool:
        ...

    @abstractmethod
    def set_source_voltage_autorange(self, value: bool) -> None:
        ...

    # Source current range

    @abstractmethod
    def get_source_current_range(self) -> float:
        ...

    @abstractmethod
    def set_source_current_range(self, value: float) -> None:
        ...

    # Source current autorange

    @abstractmethod
    def get_source_current_autorange(self) -> bool:
        ...

    @abstractmethod
    def set_source_current_autorange(self, value: bool) -> None:
        ...

    # Sense mode

    SENSE_MODE_LOCAL: str = "LOCAL"
    SENSE_MODE_REMOTE: str = "REMOTE"
    SENSE_MODE_OPTIONS: Tuple[str, ...] = (
        SENSE_MODE_LOCAL,
        SENSE_MODE_REMOTE
    )

    @abstractmethod
    def get_sense_mode(self) -> str:
        ...

    @abstractmethod
    def set_sense_mode(self, value: str) -> None:
        ...

    # Compliance tripped

    @abstractmethod
    def compliance_tripped(self) -> bool:
        ...

    # Compliance voltage

    @abstractmethod
    def get_compliance_voltage(self) -> float:
        ...

    @abstractmethod
    def set_compliance_voltage(self, value: float) -> None:
        ...

    # Compliance current

    @abstractmethod
    def get_compliance_current(self) -> float:
        ...

    @abstractmethod
    def set_compliance_current(self, value: float) -> None:
        ...

    # Filter enable

    @abstractmethod
    def get_filter_enable(self) -> bool:
        ...

    @abstractmethod
    def set_filter_enable(self, value: bool) -> None:
        ...

    # Filter count

    FILTER_COUNT_MINIMUM: int = 0
    FILTER_COUNT_MAXIMUM: int = 100

    @abstractmethod
    def get_filter_count(self) -> int:
        ...

    @abstractmethod
    def set_filter_count(self, value: int) -> None:
        ...

    # Filter type

    FILTER_TYPE_REPEAT: str = "REPEAT"
    FILTER_TYPE_MOVING: str = "MOVING"
    FILTER_TYPE_OPTIONS: Tuple[str, ...] = (
        FILTER_TYPE_REPEAT,
        FILTER_TYPE_MOVING
    )

    @abstractmethod
    def get_filter_type(self) -> str:
        ...

    @abstractmethod
    def set_filter_type(self, value: str) -> None:
        ...

    # Terminal

    TERMINAL_FRONT: str = "FRONT"
    TERMINAL_REAR: str = "REAR"
    TERMINAL_OPTIONS: Tuple[str, ...] = (
        TERMINAL_FRONT,
        TERMINAL_REAR
    )

    @abstractmethod
    def get_terminal(self) -> str:
        ...

    @abstractmethod
    def set_terminal(self, value: str) -> None:
        ...

    # Reading

    @abstractmethod
    def read_current(self) -> float:
        ...

    @abstractmethod
    def read_voltage(self) -> float:
        ...

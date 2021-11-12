from abc import abstractmethod
from typing import Tuple

from .instrument import Instrument

__all__ = ['SMUInstrument']


class SMUInstrument(Instrument):

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def get_error(self) -> Tuple[int, str]:
        pass

    # Output

    OUTPUT_ON: str = 'ON'
    OUTPUT_OFF: str = 'OFF'
    OUTPUT_OPTIONS = (
        OUTPUT_ON,
        OUTPUT_OFF
    )

    @abstractmethod
    def get_output(self) -> str:
        pass

    @abstractmethod
    def set_output(self, value: str) -> None:
        pass

    # Source function

    SOURCE_FUNCTION_VOLTAGE: str = 'VOLTAGE'
    SOURCE_FUNCTION_CURRENT: str = 'CURRENT'
    SOURCE_FUNCTION_OPTIONS = (
        SOURCE_FUNCTION_VOLTAGE,
        SOURCE_FUNCTION_CURRENT
    )

    @abstractmethod
    def get_source_function(self) -> str:
        pass

    @abstractmethod
    def set_source_function(self, value: str) -> None:
        pass

    # Source voltage

    SOURCE_VOLTAGE_MINIMUM: float = -1000.0
    SOURCE_VOLTAGE_MAXIMUM: float = +1000.0

    @abstractmethod
    def get_source_voltage(self) -> float:
        pass

    @abstractmethod
    def set_source_voltage(self, value: float) -> None:
        pass

    # Source current

    SOURCE_CURRENT_MINIMUM: float = -1.0
    SOURCE_CURRENT_MAXIMUM: float = +1.0

    @abstractmethod
    def get_source_current(self) -> float:
        pass

    @abstractmethod
    def set_source_current(self, value: float) -> None:
        pass

    # Source voltage range

    @abstractmethod
    def get_source_voltage_range(self) -> float:
        pass

    @abstractmethod
    def set_source_voltage_range(self, value: float) -> None:
        pass

    # Source voltage autorange

    @abstractmethod
    def get_source_voltage_autorange(self) -> bool:
        pass

    @abstractmethod
    def set_source_voltage_autorange(self, value: bool) -> None:
        pass

    # Source current range

    @abstractmethod
    def get_source_current_range(self) -> float:
        pass

    @abstractmethod
    def set_source_current_range(self, value: float) -> None:
        pass

    # Source current autorange

    @abstractmethod
    def get_source_current_autorange(self) -> bool:
        pass

    @abstractmethod
    def set_source_current_autorange(self, value: bool) -> None:
        pass

    # Sense mode

    SENSE_MODE_LOCAL: str = 'LOCAL'
    SENSE_MODE_REMOTE: str = 'REMOTE'
    SENSE_MODE_OPTIONS = (
        SENSE_MODE_LOCAL,
        SENSE_MODE_REMOTE
    )

    @abstractmethod
    def get_sense_mode(self) -> str:
        pass

    @abstractmethod
    def set_sense_mode(self, value: str) -> None:
        pass

    # Compliance tripped

    @abstractmethod
    def compliance_tripped(self) -> bool:
        pass

    # Compliance voltage

    @abstractmethod
    def get_compliance_voltage(self) -> float:
        pass

    @abstractmethod
    def set_compliance_voltage(self, value: float) -> None:
        pass

    # Compliance current

    @abstractmethod
    def get_compliance_current(self) -> float:
        pass

    @abstractmethod
    def set_compliance_current(self, value: float) -> None:
        pass

    # Filter enable

    @abstractmethod
    def get_filter_enable(self) -> bool:
        pass

    @abstractmethod
    def set_filter_enable(self, value: bool) -> None:
        pass

    # Filter count

    FILTER_COUNT_MINIMUM: int = 0
    FILTER_COUNT_MAXIMUM: int = 100

    @abstractmethod
    def get_filter_count(self) -> int:
        pass

    @abstractmethod
    def set_filter_count(self, value: int) -> None:
        pass

    # Filter type

    FILTER_TYPE_REPEAT: str = 'REPEAT'
    FILTER_TYPE_MOVING: str = 'MOVING'
    FILTER_TYPE_OPTIONS = (
        FILTER_TYPE_REPEAT,
        FILTER_TYPE_MOVING
    )

    @abstractmethod
    def get_filter_type(self) -> str:
        pass

    @abstractmethod
    def set_filter_type(self, value: str) -> None:
        pass

    # Terminal

    TERMINAL_FRONT: str = 'FRONT'
    TERMINAL_REAR: str = 'REAR'
    TERMINAL_OPTIONS = (
        TERMINAL_FRONT,
        TERMINAL_REAR
    )

    @abstractmethod
    def get_terminal(self) -> str:
        pass

    @abstractmethod
    def set_terminal(self, value: str) -> None:
        pass

    # Reading

    @abstractmethod
    def read_current(self) -> float:
        pass

    @abstractmethod
    def read_voltage(self) -> float:
        pass

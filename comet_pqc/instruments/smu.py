from abc import abstractmethod

from .instrument import Instrument

__all__ = ['SMUInstrument']

class SMUInstrument(Instrument):

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def get_error(self):
        pass

    # Output

    OUTPUT_ON = 'ON'
    OUTPUT_OFF = 'OFF'
    OUTPUT_OPTIONS = (
        OUTPUT_ON,
        OUTPUT_OFF
    )

    @abstractmethod
    def get_output(self):
        pass

    @abstractmethod
    def set_output(self, value):
        pass

    # Source function

    SOURCE_FUNCTION_VOLTAGE = 'VOLTAGE'
    SOURCE_FUNCTION_CURRENT = 'CURRENT'
    SOURCE_FUNCTION_OPTIONS = (
        SOURCE_FUNCTION_VOLTAGE,
        SOURCE_FUNCTION_CURRENT
    )

    @abstractmethod
    def get_source_function(self):
        pass

    @abstractmethod
    def set_source_function(self, value):
        pass

    # Source voltage

    SOURCE_VOLTAGE_MINIMUM = -1000.0
    SOURCE_VOLTAGE_MAXIMUM = +1000.0

    @abstractmethod
    def get_source_voltage(self):
        pass

    @abstractmethod
    def set_source_voltage(self, value):
        pass

    # Source current

    SOURCE_CURRENT_MINIMUM = -1.0
    SOURCE_CURRENT_MAXIMUM = +1.0

    @abstractmethod
    def get_source_current(self):
        pass

    @abstractmethod
    def set_source_current(self, value):
        pass

    # Source voltage range

    @abstractmethod
    def get_source_voltage_range(self):
        pass

    @abstractmethod
    def set_source_voltage_range(self, value):
        pass

    # Source voltage autorange

    @abstractmethod
    def get_source_voltage_autorange(self):
        pass

    @abstractmethod
    def set_source_voltage_autorange(self, value):
        pass

    # Source current range

    @abstractmethod
    def get_source_current_range(self):
        pass

    @abstractmethod
    def set_source_current_range(self, value):
        pass

    # Source current autorange

    @abstractmethod
    def get_source_current_autorange(self):
        pass

    @abstractmethod
    def set_source_current_autorange(self, value):
        pass

    # Sense mode

    SENSE_MODE_LOCAL = 'LOCAL'
    SENSE_MODE_REMOTE = 'REMOTE'
    SENSE_MODE_OPTIONS = (
        SENSE_MODE_LOCAL,
        SENSE_MODE_REMOTE
    )

    @abstractmethod
    def get_sense_mode(self):
        pass

    @abstractmethod
    def set_sense_mode(self, value):
        pass

    # Compliance tripped

    @abstractmethod
    def compliance_tripped(self):
        pass

    # Compliance voltage

    @abstractmethod
    def get_compliance_voltage(self):
        pass

    @abstractmethod
    def set_compliance_voltage(self, value):
        pass

    # Compliance current

    @abstractmethod
    def get_compliance_current(self):
        pass

    @abstractmethod
    def set_compliance_current(self, value):
        pass

    # Filter enable

    @abstractmethod
    def get_filter_enable(self):
        pass

    @abstractmethod
    def set_filter_enable(self, value):
        pass

    # Filter count

    FILTER_COUNT_MINIMUM = 0
    FILTER_COUNT_MAXIMUM = 100

    @abstractmethod
    def get_filter_count(self):
        pass

    @abstractmethod
    def set_filter_count(self, value):
        pass

    # Filter type

    FILTER_TYPE_REPEAT = 'REPEAT'
    FILTER_TYPE_MOVING = 'MOVING'
    FILTER_TYPE_OPTIONS = (
        FILTER_TYPE_REPEAT,
        FILTER_TYPE_MOVING
    )

    @abstractmethod
    def get_filter_type(self):
        pass

    @abstractmethod
    def set_filter_type(self, value):
        pass

    # Terminal

    TERMINAL_FRONT = 'FRONT'
    TERMINAL_REAR = 'REAR'
    TERMINAL_OPTIONS = (
        TERMINAL_FRONT,
        TERMINAL_REAR
    )

    @abstractmethod
    def get_terminal(self):
        pass

    @abstractmethod
    def set_terminal(self, value):
        pass

    # Reading

    @abstractmethod
    def read_current(self):
        pass

    @abstractmethod
    def read_voltage(self):
        pass

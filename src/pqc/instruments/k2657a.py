from typing import Tuple

from comet.driver.keithley import K2657A

from .smu import SMUInstrument

__all__ = ["K2657AInstrument"]


class K2657AInstrument(SMUInstrument):

    def __init__(self, context) -> None:
        super().__init__(K2657A(context))

    def reset(self) -> None:
        self.context.reset()
        self.context.clear()
        self.context.beeper.enable = False

    def clear(self) -> None:
        self.context.clear()

    def get_error(self) -> Tuple[int, str]:
        if self.context.errorqueue.count:
            code, message = self.context.errorqueue.next()
            return code, message
        return 0, "no error"

    # Output

    def get_output(self) -> str:
        value = self.context.source.output
        return {
            "ON": self.OUTPUT_ON,
            "OFF": self.OUTPUT_OFF
        }[value]

    def set_output(self, value: str) -> None:
        value = {
            self.OUTPUT_ON: "ON",
            self.OUTPUT_OFF: "OFF"
        }[value]
        self.context.source.output = value

    # Source function

    def get_source_function(self) -> str:
        value = self.context.source.func
        return {
            "DCVOLTS": self.SOURCE_FUNCTION_VOLTAGE,
            "DCAMPS": self.SOURCE_FUNCTION_CURRENT
        }[value]

    def set_source_function(self, value: str) -> None:
        value = {
            self.SOURCE_FUNCTION_VOLTAGE: "DCVOLTS",
            self.SOURCE_FUNCTION_CURRENT: "DCAMPS"
        }[value]
        self.context.source.func = value

    # Source voltage

    def get_source_voltage(self) -> float:
        return self.context.source.levelv

    def set_source_voltage(self, value: float) -> None:
        self.context.source.levelv = value

    # Source current

    def get_source_current(self) -> float:
        return self.context.source.leveli

    def set_source_current(self, value: float) -> None:
        self.context.source.leveli = value

    # Source voltage range

    def get_source_voltage_range(self) -> float:
        return self.context.source.rangev

    def set_source_voltage_range(self, value: float) -> None:
        self.context.source.rangev = value

    # Source voltage autorange

    def get_source_voltage_autorange(self) -> bool:
        return self.context.source.autorangev

    def set_source_voltage_autorange(self, value: bool) -> None:
        self.context.source.autorangev = value

    # Source current range

    def get_source_current_range(self) -> float:
        return self.context.source.rangei

    def set_source_current_range(self, value: float) -> None:
        self.context.source.rangei = value

    # Source current autorange

    def get_source_current_autorange(self) -> bool:
        return self.context.source.autorangei

    def set_source_current_autorange(self, value: bool) -> None:
        self.context.source.autorangei = value

    # Sense mode

    def get_sense_mode(self) -> str:
        value = self.context.sense
        return {
            "REMOTE": self.SENSE_MODE_REMOTE,
            "LOCAL": self.SENSE_MODE_LOCAL
        }[value]

    def set_sense_mode(self, value: str) -> None:
        value = {
            self.SENSE_MODE_REMOTE: "REMOTE",
            self.SENSE_MODE_LOCAL: "LOCAL"
        }[value]
        self.context.sense = value

    # Compliance tripped

    def compliance_tripped(self) -> bool:
        return self.context.source.compliance

    # Compliance voltage

    def get_compliance_voltage(self) -> float:
        return self.context.source.limitv

    def set_compliance_voltage(self, value: float) -> None:
        self.context.source.limitv = value

    # Compliance current

    def get_compliance_current(self) -> float:
        return self.context.source.limiti

    def set_compliance_current(self, value: float) -> None:
        self.context.source.limiti = value

    # Filter enable

    def get_filter_enable(self) -> bool:
        return self.context.measure.filter.enable

    def set_filter_enable(self, value: bool) -> None:
        self.context.measure.filter.enable = value

    # Filter count

    def get_filter_count(self) -> int:
        return self.context.measure.filter.count

    def set_filter_count(self, value: int) -> None:
        self.context.measure.filter.count = value

    # Filter type

    def get_filter_type(self) -> str:
        value = self.context.sense.average.tcontrol
        return {
            "REPEAT": self.FILTER_TYPE_REPEAT,
            "MOVING": self.FILTER_TYPE_MOVING
        }[value]

    def set_filter_type(self, value: str) -> None:
        value = {
            self.FILTER_TYPE_REPEAT: "REPEAT",
            self.FILTER_TYPE_MOVING: "MOVING"
        }[value]
        self.context.measure.filter.type = value

    # Terminal

    TERMINAL_OPTIONS = (
        SMUInstrument.TERMINAL_FRONT,
    )

    def get_terminal(self) -> str:
        return self.TERMINAL_FRONT

    def set_terminal(self, value: str) -> None:
        ...

    # Reading

    def read_current(self) -> float:
        return self.context.measure.i()

    def read_voltage(self) -> float:
        return self.context.measure.v()

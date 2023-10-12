from typing import Tuple

from comet.driver.keithley import K2410

from .smu import SMUInstrument

__all__ = ["K2410Instrument"]


class K2410Instrument(SMUInstrument):

    def __init__(self, context) -> None:
        super().__init__(K2410(context))

    def reset(self) -> None:
        self.context.reset()
        self.context.clear()
        self.context.system.beeper.status = False

    def clear(self) -> None:
        self.context.clear()

    def get_error(self) -> Tuple[int, str]:
        code, message = self.context.system.error
        return code, message

    # Output

    def get_output(self) -> str:
        value = self.context.output
        return {
            True: self.OUTPUT_ON,
            False: self.OUTPUT_OFF
        }[value]

    def set_output(self, value: str) -> None:
        self.context.output = {
            self.OUTPUT_ON: True,
            self.OUTPUT_OFF: False
        }[value]

    # Source function

    def get_source_function(self) -> str:
        value = self.context.source.function.mode
        return {
            "VOLTAGE": self.SOURCE_FUNCTION_VOLTAGE,
            "CURRENT": self.SOURCE_FUNCTION_CURRENT
        }[value]

    def set_source_function(self, value: str) -> None:
        value = {
            self.SOURCE_FUNCTION_VOLTAGE: "VOLTAGE",
            self.SOURCE_FUNCTION_CURRENT: "CURRENT"
        }[value]
        self.context.source.function.mode = value

    # Source voltage

    def get_source_voltage(self) -> float:
        return self.context.source.voltage.level

    def set_source_voltage(self, value: float) -> None:
        self.context.source.voltage.level = value

    # Source current

    def get_source_current(self) -> float:
        return self.context.source.current.level

    def set_source_current(self, value: float) -> None:
        self.context.source.current.level = value

    # Source voltage range

    def get_source_voltage_range(self) -> float:
        return self.context.source.voltage.range.level

    def set_source_voltage_range(self, value: float) -> None:
        self.context.source.voltage.range.level = value

    # Source voltage autorange

    def get_source_voltage_autorange(self) -> bool:
        return self.context.source.voltage.range.auto

    def set_source_voltage_autorange(self, value: bool) -> None:
        self.context.source.voltage.range.auto = value

    # Source current range

    def get_source_current_range(self) -> float:
        return self.context.source.current.range.level

    def set_source_current_range(self, value: float) -> None:
        self.context.source.current.range.level = value

    # Source current autorange

    def get_source_current_autorange(self) -> bool:
        return self.context.source.current.range.auto

    def set_source_current_autorange(self, value: bool) -> None:
        self.context.source.current.range.auto = value

    # Sense mode

    def get_sense_mode(self) -> str:
        value = self.context.system.rsense
        return {
            "ON": self.SENSE_MODE_REMOTE,
            "OFF": self.SENSE_MODE_LOCAL
        }[value]

    def set_sense_mode(self, value: str) -> None:
        value = {
            self.SENSE_MODE_REMOTE: "ON",
            self.SENSE_MODE_LOCAL: "OFF"
        }[value]
        self.context.system.rsense = value

    # Compliance tripped

    def compliance_tripped(self) -> bool:
        # TODO: how to distinguish?
        return self.context.sense.current.protection.tripped or \
            self.context.sense.voltage.protection.tripped

    # Compliance voltage

    def get_compliance_voltage(self) -> float:
        return self.context.sense.voltage.protection.level

    def set_compliance_voltage(self, value: float) -> None:
        self.context.sense.voltage.protection.level = value

    # Compliance current

    def get_compliance_current(self) -> float:
        return self.context.sense.current.protection.level

    def set_compliance_current(self, value: float) -> None:
        self.context.sense.current.protection.level = value

    # Filter enable

    def get_filter_enable(self) -> bool:
        return self.context.sense.average.state

    def set_filter_enable(self, value: bool) -> None:
        self.context.sense.average.state = value

    # Filter count

    def get_filter_count(self) -> int:
        return self.context.sense.average.count

    def set_filter_count(self, value: int) -> None:
        self.context.sense.average.count = value

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
        self.context.sense.average.tcontrol = value

    # Terminal

    def get_terminal(self) -> str:
        value = self.context.route.terminals
        return {
            "FRONT": self.TERMINAL_FRONT,
            "REAR": self.TERMINAL_REAR
        }[value]

    def set_terminal(self, value: str) -> None:
        value = {
            self.TERMINAL_FRONT: "FRONT",
            self.TERMINAL_REAR: "REAR"
        }[value]
        self.context.route.terminals = value

    # Reading

    def read_current(self) -> float:
        self.context.format.elements = ["CURRENT"]
        self.context.resource.write(":SENS:FUNC:CONC ON")
        self.context.resource.query("*OPC?")
        self.context.resource.write(":SENS:FUNC:ON 'CURR'")
        self.context.resource.query("*OPC?")
        return self.context.read()[0]

    def read_voltage(self) -> float:
        self.context.format.elements = ["VOLTAGE"]
        self.context.resource.write(":SENS:FUNC:CONC ON")
        self.context.resource.query("*OPC?")
        self.context.resource.write(":SENS:FUNC:ON 'VOLT'")
        self.context.resource.query("*OPC?")
        return self.context.read()[0]

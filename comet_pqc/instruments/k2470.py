from typing import Tuple

from .smu import SMUInstrument
from comet.driver import Driver

__all__ = ['K2470Instrument']


class K2470Instrument(SMUInstrument):

    def __init__(self, context) -> None:
        super().__init__(Driver(context))

    def reset(self) -> None:
        self.context.resource.write('*RST')
        self.context.resource.query('*OPC?')
        # TODO
        if self.context.resource.query('*LANG?') != 'SCPI':
            raise RuntimeError("K2470 instrument not in SCPI mode!")

    def clear(self) -> None:
        self.context.resource.write('*CLS')
        self.context.resource.query('*OPC?')

    def get_error(self) -> Tuple[int, str]:
        code, message = self.context.resource.query(':SYST:ERR?').split(',', 1)
        return int(code), message.strip().strip('"')

    # Output

    def get_output(self) -> str:
        value = int(self.context.resource.query(':OUTP?'))
        return {
            1: self.OUTPUT_ON,
            0: self.OUTPUT_OFF
        }.get(value)

    def set_output(self, value: str) -> None:
        value = {
            self.OUTPUT_ON: 1,
            self.OUTPUT_OFF: 0
        }.get(value)
        self.context.resource.write(f':OUTP {value:d}')
        self.context.resource.query('*OPC?')

    # Source function

    def get_source_function(self) -> str:
        value = self.context.resource.query(':SOUR:FUNC?')
        return {
            'VOLT': self.SOURCE_FUNCTION_VOLTAGE,
            'CURR': self.SOURCE_FUNCTION_CURRENT
        }.get(value)

    def set_source_function(self, value: str) -> None:
        value = {
            self.SOURCE_FUNCTION_VOLTAGE: 'VOLT',
            self.SOURCE_FUNCTION_CURRENT: 'CURR'
        }.get(value)
        self.context.resource.write(f':SOUR:FUNC {value}')
        self.context.resource.query('*OPC?')

    # Source voltage

    def get_source_voltage(self) -> float:
        return float(self.context.resource.query(':SOUR:VOLT:LEV?'))

    def set_source_voltage(self, value: float) -> None:
        self.context.resource.write(f':SOUR:VOLT:LEV {value:.3E}')
        self.context.resource.query('*OPC?')

    # Source current

    def get_source_current(self) -> float:
        return float(self.context.resource.query(':SOUR:CURR:LEV?'))

    def set_source_current(self, value: float) -> None:
        self.context.resource.write(f':SOUR:CURR:LEV {value:.3E}')
        self.context.resource.query('*OPC?')

    # Source voltage range

    def get_source_voltage_range(self) -> float:
        return float(self.context.resource.query(':SOUR:VOLT:RANG?'))

    def set_source_voltage_range(self, value: float) -> None:
        self.context.resource.write(f':SOUR:VOLT:RANG {value:.3E}')
        self.context.resource.query('*OPC?')

    # Source voltage autorange

    def get_source_voltage_autorange(self) -> bool:
        return bool(int(self.context.resource.query(':SOUR:VOLT:RANG:AUTO?')))

    def set_source_voltage_autorange(self, value: bool) -> None:
        self.context.resource.write(f':SOUR:VOLT:RANG:AUTO {value:d}')
        self.context.resource.query('*OPC?')

    # Source current range

    def get_source_current_range(self) -> float:
        return float(self.context.resource.query(':SOUR:CURR:RANG?'))

    def set_source_current_range(self, value: float) -> None:
        self.context.resource.write(f':SOUR:CURR:RANG {value:.3E}')
        self.context.resource.query('*OPC?')

    # Source current autorange

    def get_source_current_autorange(self) -> bool:
        return bool(int(self.context.resource.query(':SOUR:CURR:RANG:AUTO?')))

    def set_source_current_autorange(self, value: bool) -> None:
        self.context.resource.write(f':SOUR:CURR:RANG:AUTO {value:d}')
        self.context.resource.query('*OPC?')

    # Sense mode

    def get_sense_mode(self) -> str:
        value = int(self.context.resource.query(':SENS:VOLT:RSEN?'))  # TODO
        return {
            1: self.SENSE_MODE_REMOTE,
            0: self.SENSE_MODE_LOCAL
        }.get(value)

    def set_sense_mode(self, value: str) -> None:
        value = {
            self.SENSE_MODE_REMOTE: 'ON',
            self.SENSE_MODE_LOCAL: 'OFF'
        }.get(value)
        self.context.resource.write(f':SENS:VOLT:RSEN {value}')
        self.context.resource.query('*OPC?')
        self.context.resource.write(f':SENS:CURR:RSEN {value}')
        self.context.resource.query('*OPC?')

    # Compliance tripped

    def compliance_tripped(self) -> bool:
        # TODO: how to distinguish?
        current_vlimit_tripped = bool(int(self.context.resource.query(':SOUR:CURR:VLIM:TRIP?')))
        voltage_ilimit_tripped = bool(int(self.context.resource.query(':SOUR:VOLT:ILIM:TRIP?')))
        return current_vlimit_tripped or voltage_ilimit_tripped

    # Compliance voltage

    def get_compliance_voltage(self) -> float:
        return float(self.context.resource.query(':SOUR:CURR:VLIM?'))

    def set_compliance_voltage(self, value: float) -> None:
        self.context.resource.write(f':SOUR:CURR:VLIM {value:.3E}')
        self.context.resource.query('*OPC?')

    # Compliance current

    def get_compliance_current(self) -> float:
        return float(self.context.resource.query(':SOUR:VOLT:ILIM?'))

    def set_compliance_current(self, value: float) -> None:
        self.context.resource.write(f':SOUR:VOLT:ILIM {value:.3E}')
        self.context.resource.query('*OPC?')

    # Filter enable

    def get_filter_enable(self) -> bool:
        return bool(int(self.context.resource.query(':SENS:CURR:AVER?'))) # TODO

    def set_filter_enable(self, value: bool) -> None:
        self.context.resource.write(f':SENS:VOLT:AVER {value:d}')
        self.context.resource.query('*OPC?')
        self.context.resource.write(f':SENS:CURR:AVER {value:d}')
        self.context.resource.query('*OPC?')

    # Filter count

    def get_filter_count(self) -> int:
        return int(self.context.resource.query(':SENS:CURR:AVER:COUN?'))

    def set_filter_count(self, value: int) -> None:
        self.context.resource.write(f':SENS:VOLT:AVER:COUN {value:d}')
        self.context.resource.query('*OPC?')
        self.context.resource.write(f':SENS:CURR:AVER:COUN {value:d}')
        self.context.resource.query('*OPC?')

    # Filter type

    def get_filter_type(self) -> str:
        value = self.context.resource.query(':SENS:CURR:AVER:TCON?')
        return {
            'REP': self.FILTER_TYPE_REPEAT,
            'MOV': self.FILTER_TYPE_MOVING
        }.get(value)

    def set_filter_type(self, value: str) -> None:
        value = {
            self.FILTER_TYPE_REPEAT: 'REP',
            self.FILTER_TYPE_MOVING: 'MOV'
        }.get(value)
        self.context.resource.write(f':SENS:CURR:AVER:TCON {value}')
        self.context.resource.query('*OPC?')

    # Terminal

    def get_terminal(self) -> str:
        value = self.context.resource.query(':ROUT:TERM?')
        return {
            'FRON': self.TERMINAL_FRONT,
            'REAR': self.TERMINAL_REAR
        }.get(value)

    def set_terminal(self, value: str) -> None:
        value = {
            self.TERMINAL_FRONT: 'FRON',
            self.TERMINAL_REAR: 'REAR'
        }.get(value)
        self.context.resource.write(f':ROUT:TERM {value}')
        self.context.resource.query('*OPC?')

    # Reading

    def read_current(self) -> float:
        return float(self.context.resource.query(':MEAS:CURR?'))

    def read_voltage(self) -> float:
        return float(self.context.resource.query(':MEAS:VOLT?'))

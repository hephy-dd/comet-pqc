"""Keithley 2470 emulator."""

import random
import time

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['K2470Handler']


class SourceMixin:

    source_function = 'VOLT'

    @message(r':?SOUR:FUNC:MODE\?')
    def get_source_function_mode(self):
        return type(self).source_function

    @message(r':?SOUR:FUNC:MODE\s+(CURR|VOLT|MEM)')
    def set_source_function_mode(self, mode):
        type(self).source_function = mode

    source_voltage_level = 0.0

    @message(r':?SOUR:VOLT:LEV\?')
    def get_source_voltage_level(self):
        return format(type(self).source_voltage_level, 'E')

    @message(r':?SOUR:VOLT:LEV\s+(.*)')
    def set_source_voltage_level(self, value):
        type(self).source_voltage_level = float(value)

    source_current_level = 0.0

    @message(r':?SOUR:CURR:LEV\?')
    def get_source_current_level(self):
        return format(type(self).source_current_level, 'E')

    @message(r':?SOUR:CURR:LEV\s+(.*)')
    def set_source_current_level(self, value):
        type(self).source_current_level = float(value)

    source_current_vlimit = 0.2

    @message(r':?SOUR:CURR:VLIM\?')
    def get_source_current_vlimit(self):
        return format(type(self).source_current_vlimit, 'E')

    source_current_vlimit_tripped = False

    @message(r':?SOUR:CURR:VLIM:TRIP\?')
    def get_source_current_vlimit_tripped(self):
        return '0'

    source_voltage_ilimit = 0.0001

    @message(r':?SOUR:VOLT:ILIM\?')
    def get_source_voltage_ilimit(self):
        return format(type(self).source_voltage_ilimit, 'E')

    source_voltage_ilimit_tripped = False

    @message(r':?SOUR:VOLT:ILIM:TRIP\?')
    def get_source_voltage_ilimit_tripped(self):
        return '0'


class SenseMixin:

    sense_voltage_average_state = False

    @message(r':?SENS:VOLT:AVER\?')
    @message(r':?SENS:VOLT:AVER:STAT\?')
    def get_sense_voltage_average_state(self):
        return type(self).sense_voltage_average_state

    @message(r':?SENS:VOLT:AVER\s+(0|1|OFF|ON)')
    @message(r':?SENS:VOLT:AVER:STAT\s+(0|1|OFF|ON)')
    def set_sense_voltage_average_state(self, value):
        type(self).sense_voltage_average_state = {'0': False, '1': True, 'OFF': False, 'ON': True}.get(value, 0)

    sense_voltage_average_count = 0

    @message(r':?SENS:VOLT:AVER:COUN\?')
    def get_sense_voltage_average_count(self):
        return format(type(self).sense_voltage_average_count, 'd')

    @message(r':?SENS:VOLT:AVER:COUN\s+(\d+)')
    def set_sense_voltage_average_count(self, value):
        type(self).sense_voltage_average_count = int(value)

    sense_voltage_average_tcontrol = 'REP'

    @message(r':?SENS:VOLT:AVER:TCON\?')
    def get_sense_voltage_average_tcontrol(self):
        return type(self).sense_voltage_average_tcontrol, 'd'

    @message(r':?SENS:VOLT:AVER:TCON\s+(MOV|REP)')
    def set_sense_voltage_average_tcontrol(self, value):
        type(self).sense_voltage_average_tcontrol = value

    sense_voltage_rsense = False

    @message(r':?SENS:VOLT:RSEN\?')
    def get_sense_voltage_rsense(self):
        return format(type(self).sense_voltage_rsense, 'd')

    @message(r':?SENS:VOLT:RSEN\s+(0|1|OFF|ON)')
    def set_sense_voltage_rsense(self, value):
        type(self).sense_voltage_rsense = {'0': False, '1': True, 'OFF': False, 'ON': True}.get(value, 0)

    sense_current_average_state = False

    @message(r':?SENS:CURR:AVER\?')
    @message(r':?SENS:CURR:AVER:STAT\?')
    def get_sense_current_average_state(self):
        return type(self).sense_current_average_state

    @message(r':?SENS:CURR:AVER\s+(0|1|OFF|ON)')
    @message(r':?SENS:CURR:AVER:STAT\s+(0|1|OFF|ON)')
    def set_sense_current_average_state(self, value):
        type(self).sense_current_average_state = {'0': False, '1': True, 'OFF': False, 'ON': True}.get(value, 0)

    sense_current_average_count = 0

    @message(r':?SENS:CURR:AVER:COUN\?')
    def get_sense_current_average_count(self):
        return format(type(self).sense_current_average_count, 'd')

    @message(r':?SENS:CURR:AVER:COUN\s+(\d+)')
    def set_sense_current_average_count(self, value):
        type(self).sense_current_average_count = int(value)

    sense_current_average_tcontrol = 'REP'

    @message(r':?SENS:CURR:AVER:TCON\?')
    def get_sense_current_average_tcontrol(self):
        return type(self).sense_current_average_tcontrol, 'd'

    @message(r':?SENS:CURR:AVER:TCON\s+(MOV|REP)')
    def set_sense_current_average_tcontrol(self, value):
        type(self).sense_current_average_tcontrol = value

    sense_current_rsense = False

    @message(r':?SENS:CURR:RSEN\?')
    def get_sense_current_rsense(self):
        return format(type(self).sense_current_rsense, 'd')

    @message(r':?SENS:CURR:RSEN\s+(0|1|OFF|ON)')
    def set_sense_current_rsense(self, value):
        type(self).sense_current_rsense = {'0': False, '1': True, 'OFF': False, 'ON': True}.get(value, 0)


class RouteMixin:

    route_terminals = 'FRON'

    @message(r':?ROUT:TERM\?')
    def get_route_terminals(self):
        return type(self).sense_voltage_average_tcontrol, 'd'

    @message(r':?ROUT:TERM\s+(FRON|REAR)')
    def set_route_terminals(self, value):
        type(self).sense_voltage_average_tcontrol = value


class K2470Handler(IEC60488Handler, SourceMixin, SenseMixin, RouteMixin):
    """Generic Keithley 2470 series compliant request handler."""

    identification = "Spanish Inquisition Inc., Model 2470, 12345678, v1.0"

    output_state = False

    @message(r'\*LANG\?')
    def get_lang(self):
        return 'SCPI'

    @message(r':?SYST:ERR\?')
    @message(r':?SYST:ERR:NEXT\?')
    def query_system_error(self):
        return '0,"no error;1;"'

    @message(r':?OUTP\?')
    @message(r':?OUTP:STAT\?')
    def query_output(self):
        return format(type(self).output_state, 'd')

    @message(r':?OUTP\s+(0|1|OFF|ON)')
    @message(r':?OUTP:STAT\s+(0|1|OFF|ON)')
    def write_output(self, value):
        type(self).output_state = {'0': False, '1': True, 'OFF': False, 'ON': True}.get(value, 0)

    @message(r':?MEAS:VOLT\?')
    def get_measure_voltage(self):
        return format(random.uniform(0, 100), '.3E')

    @message(r':?MEAS:CURR\?')
    def get_measure_current(self):
        return format(random.uniform(0.00001, 0.0001), '.3E')


if __name__ == "__main__":
    run(K2470Handler)

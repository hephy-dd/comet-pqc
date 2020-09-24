import random

from comet.emulator.emulator import message, run
from comet.emulator.keysight.e4980a import E4980AHandler

class E4980AHandler(E4980AHandler):

    bias_voltage_level = 0.0
    bias_state = False

    @message(r':?BIAS:POL:CURR\?')
    @message(r':?BIAS:POL:CURR:LEV\?')
    def get_bias_polarity_current_level(self):
        return format(random.random() / 1000., 'E')

    @message(r':?BIAS:POL:VOLT\?')
    @message(r':?BIAS:POL:VOLT:LEV\?')
    def get_bias_polarity_voltage_level(self):
        return format(random.random() / 100., 'E')

    @message(r':?BIAS:VOLT:LEV\?')
    def get_bias_voltage_level(self):
        return format(type(self).bias_voltage_level, 'E')

    @message(r':?BIAS:VOLT:LEV\s+(.*)')
    def set_bias_voltage_level(self, value):
        type(self).bias_voltage_level = float(value)

    @message(r':?BIAS:STAT\?')
    def get_bias_state(self):
        return int(type(self).bias_state)

    @message(r':?BIAS:STAT\s+(0|1|ON|OFF)')
    def set_bias_state(self, value):
        type(self).bias_state = {'0': False, '1': True, 'OFF': False, 'ON': True}[value]

if __name__ == '__main__':
    run(E4980AHandler)

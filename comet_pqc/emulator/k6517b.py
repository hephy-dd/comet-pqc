"""Keithley 6517B emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['K6517BHandler']

class K6517BHandler(IEC60488Handler):

    identification = "Spanish Inquisition Inc., Model 6517B, 12345678, v1.0"

    zero_check = False

    @message(r'\:?SYST\:ERR\?')
    def query_system_error(self, message):
        return '0, "no error"'

    @message(r'\:?SYST\:ZCH\?')
    def query_system_zerocheck(self, message):
        return format(type(self).zero_check, 'd')

    @message(r'\:?SYST\:ZCH\s+ON')
    def write_system_zerocheck_on(self, message):
        type(self).zero_check = True

    @message(r'\:?SYST\:ZCH\s+OFF')
    def write_system_zerocheck_off(self, message):
        type(self).zero_check = False

    @message(r'\:?SENS\:FUNC\?')
    def query_sense_function(self, message):
        return '"CURR:DC"'

    @message(r'\:?READ\?')
    def query_read(self, message):
        return format(random.uniform(0.000001, 0.0001))

    @message(r'\:?FETCH\?')
    def query_fetch(self, message):
        return format(random.uniform(0.000001, 0.0001))

if __name__ == "__main__":
    run(K6517BHandler)

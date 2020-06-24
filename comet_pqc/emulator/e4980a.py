"""Keysight E4980A emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['E4980AHandler']

class E4980AHandler(IEC60488Handler):

    identification = "Spanish Inquisition Inc., Model 4980A, 12345678, v1.0"

    @message(r'\:SYST\:ERR\?')
    def query_system_error(self, message):
        return '0, "no error"'

    @message(r'\:?FETC\?')
    def query_fetch(self, message):
        return '{:E},{:E}'.format(random.random(), random.random())

if __name__ == "__main__":
    run(E4980AHandler)

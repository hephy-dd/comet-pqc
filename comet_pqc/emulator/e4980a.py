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

    correction_method = 0
    correction_channel = 0

    @message(r'\:SYST\:ERR\?')
    def query_system_error(self, message):
        return '0, "no error"'

    @message(r'\:?FETC\?')
    def query_fetch(self, message):
        return '{:E},{:E}'.format(random.random(), random.random())

    @message(r'\:CORR\:METH\?')
    def query_correction_method(self, message):
        return type(self).correction_method

    @message(r'\:CORR\:METH\s+SING')
    def write_correction_method_single(self, message):
        type(self).correction_method = 0

    @message(r'\:CORR\:METH\s+MULT')
    def write_correction_method_multi(self, message):
        type(self).correction_method = 1

    @message(r'\:CORR\:USE\:CHAN\?')
    def query_correction_channel(self, message):
        return type(self).correction_channel

    @message(r'\:CORR\:USE\:CHAN\s+(\d+)')
    def write_correction_method_single(self, message):
        type(self).correction_channel = int(message.split()[-1])

if __name__ == "__main__":
    run(E4980AHandler)

"""Keithley 2657A emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['K2657AHandler']

class BeeperMixin:

    enable = True

    @message(r'print\(beeper\.enable\)')
    def query_beeper_enable(self, message):
        return format(float(type(self).enable), 'E')

    @message(r'beeper\.enable\s*\=\s*(\d+)')
    def write_beeper_enable(self, message):
        type(self).enable = bool(int(message.split('=')[-1]))

class ErrorQueueMixin:

    count = 0

    @message(r'print\(errorqueue\.count\)')
    def query_errorqueue_count(self, message):
        return format(float(type(self).count), 'E')

    @message(r'print\(errorqueue\.next\(\)\)')
    def query_errorqueue_next(self, message):
        return '0.00000e+00\tQueue Is Empty'

    @message(r'errorqueue\.clear\(\)')
    def write_errorqueue_clear(self, message):
        type(self).count = 0

class SourceMixin:

    compliance = False
    leveli = 0.0
    levelv = 0.0
    limiti = 0.0
    limitv = 0.0
    output = False

    @message(r'print\(smua\.source\.compliance\)')
    def query_source_compliance(self, message):
        return format(int(type(self).compliance), 'E')

    @message(r'print\(smua\.source\.leveli\)')
    def query_source_leveli(self, message):
        return format(float(type(self).leveli), 'E')

    @message(r'smua\.source\.leveli\s*\=\s*(.*)')
    def write_source_leveli(self, message):
        type(self).leveli = float(message.split('=')[-1])

    @message(r'print\(smua\.source\.levelv\)')
    def query_source_levelv(self, message):
        return format(float(type(self).levelv), 'E')

    @message(r'smua\.source\.levelv\s*\=\s*(.*)')
    def write_source_levelv(self, message):
        type(self).levelv = float(message.split('=')[-1])

    @message(r'print\(smua\.source\.limiti\)')
    def query_source_limiti(self, message):
        return format(float(type(self).limiti), 'E')

    @message(r'smua\.source\.limiti\s*\=\s*(.*)')
    def write_source_limiti(self, message):
        type(self).limiti = float(message.split('=')[-1])

    @message(r'print\(smua\.source\.limitv\)')
    def query_source_limitv(self, message):
        return format(float(type(self).limitv), 'E')

    @message(r'smua\.source\.limitv\s*\=\s*(.*)')
    def write_source_limitv(self, message):
        type(self).limitv = float(message.split('=')[-1])

    @message(r'print\(smua\.source\.output\)')
    def query_source_output(self, message):
        return format(float(type(self).output), 'E')

    @message(r'smua\.source\.output\s*\=\s*(\d+)')
    def write_source_outout(self, message):
        type(self).output = bool(int(message.split('=')[-1]))

class K2657AHandler(IEC60488Handler, BeeperMixin, ErrorQueueMixin, SourceMixin):

    identification = "Spanish Inquisition Inc., Model 2657A, 12345678, v1.0"

if __name__ == "__main__":
    run(K2657AHandler)

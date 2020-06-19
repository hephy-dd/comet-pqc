"""Keithley 2657A emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['K2657AHandler']

def split_message(message):
    return [value.strip() for value in message.split('=')]

class BeeperMixin:

    enable = True

    @message(r'print\(beeper\.enable\)')
    def query_beeper_enable(self, message):
        return format(float(type(self).enable), 'E')

    @message(r'beeper\.enable\s*\=\s*(\d+)')
    def write_beeper_enable(self, message):
        type(self).enable = bool(int(split_message(message)[-1]))

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

class MeasureMixin:

    filter_count = 0
    filter_enable = False
    filter_type = 0
    nplc = 1.0

    @message(r'print\(smua\.measure\.filter\.count\)')
    def query_measure_filter_count(self, message):
        return format(float(type(self).filter_count), 'E')

    @message(r'smua\.measure\.filter\.count\s*\=\s*(\d+)')
    def write_measure_filter_count(self, message):
        type(self).filter_count = int(split_message(message)[-1])

    @message(r'print\(smua\.measure\.filter\.enable\)')
    def query_measure_filter_enable(self, message):
        return format(float(type(self).filter_enable), 'E')

    @message(r'smua\.measure\.filter\.enable\s*\=\s*(\d+)')
    def write_measure_filter_enable(self, message):
        type(self).filter_enable = bool(int(split_message(message)[-1]))

    @message(r'print\(smua\.measure\.filter\.type\)')
    def query_measure_filter_type(self, message):
        return format(float(type(self).filter_type), 'E')

    @message(r'smua\.measure\.filter\.type\s*\=\s*(.*)')
    def write_measure_filter_type(self, message):
        d = {'MOVING': 0, 'REPEAT': 1, 'MEDIAN': 2}
        value = split_message(message)[-1]
        if value in d:
            value = d[value]
        type(self).filter_type = value

    @message(r'print\(smua\.measure\.nplc\)')
    def query_measure_nplc(self, message):
        return format(float(type(self).nplc), 'E')

    @message(r'smua\.measure\.nplc\s*\=\s*(.*)')
    def write_measure_nplc(self, message):
        type(self).nplc = float(split_message(message)[-1])

    @message(r'print\(smua\.measure\.i\(\)\)')
    def query_measure_i(self, message):
        if SourceMixin.func == 0:
            return format(SourceMixin.leveli+random.uniform(-0.001, 0.001), 'E')
        else:
            return format(random.uniform(0.001, 0.01), 'E')

    @message(r'print\(smua\.measure\.v\(\)\)')
    def query_measure_v(self, message):
        if SourceMixin.func == 1:
            return format(SourceMixin.levelv+random.uniform(-0.001, 0.001), 'E')
        else:
            return format(random.uniform(1.0, 10.0), 'E')

    @message(r'print\(smua\.measure\.r\(\)\)')
    def query_measure_r(self, message):
        return format(random.random(), 'E')

    @message(r'print\(smua\.measure\.p\(\)\)')
    def query_measure_p(self, message):
        return format(random.random(), 'E')

    @message(r'print\(smua\.measure\.iv\(\)\)')
    def query_measure_iv(self, message):
        if SourceMixin.func == 0:
            return '{},{}'.format(SourceMixin.leveli+random.uniform(-0.001, 0.001), random.uniform(1.0, 10.0))
        else:
            return '{},{}'.format(random.uniform(0.001, 0.01), SourceMixin.levelv+random.uniform(-0.001, 0.001))

class SourceMixin:

    compliance = False
    func = 0
    highc = False
    leveli = 0.0
    levelv = 0.0
    limiti = 0.0
    limitv = 0.0
    output = 0

    @message(r'print\(smua\.source\.compliance\)')
    def query_source_compliance(self, message):
        return format(type(self).compliance).lower()

    @message(r'print\(smua\.source\.func\)')
    def query_source_func(self, message):
        return format(float(type(self).func), 'E')

    @message(r'smua\.source\.func\s*\=\s*(.*)')
    def write_source_func(self, message):
        d = {'DCAMPS': 0, 'DCVOLTS': 1}
        value = split_message(message)[-1]
        if value in d:
            value = d[value]
        type(self).func = value

    @message(r'print\(smua\.source\.highc\)')
    def query_source_highc(self, message):
        return format(float(type(self).highc), 'E')

    @message(r'smua\.source\.highc\s*\=\s*(\d+)')
    def write_source_highc(self, message):
        type(self).highc = bool(int(split_message(message)[-1]))

    @message(r'print\(smua\.source\.leveli\)')
    def query_source_leveli(self, message):
        return format(float(type(self).leveli), 'E')

    @message(r'smua\.source\.leveli\s*\=\s*(.*)')
    def write_source_leveli(self, message):
        type(self).leveli = float(split_message(message)[-1])

    @message(r'print\(smua\.source\.levelv\)')
    def query_source_levelv(self, message):
        return format(float(type(self).levelv), 'E')

    @message(r'smua\.source\.levelv\s*\=\s*(.*)')
    def write_source_levelv(self, message):
        type(self).levelv = float(split_message(message)[-1])

    @message(r'print\(smua\.source\.limiti\)')
    def query_source_limiti(self, message):
        return format(float(type(self).limiti), 'E')

    @message(r'smua\.source\.limiti\s*\=\s*(.*)')
    def write_source_limiti(self, message):
        type(self).limiti = float(split_message(message)[-1])

    @message(r'print\(smua\.source\.limitv\)')
    def query_source_limitv(self, message):
        return format(float(type(self).limitv), 'E')

    @message(r'smua\.source\.limitv\s*\=\s*(.*)')
    def write_source_limitv(self, message):
        type(self).limitv = float(split_message(message)[-1])

    @message(r'print\(smua\.source\.output\)')
    def query_source_output(self, message):
        return format(float(type(self).output), 'E')

    @message(r'smua\.source\.output\s*\=\s*(\d+)')
    def write_source_outout(self, message):
        type(self).output = int(split_message(message)[-1])

class K2657AHandler(IEC60488Handler, BeeperMixin, ErrorQueueMixin, MeasureMixin,
                    SourceMixin):

    identification = "Spanish Inquisition Inc., Model 2657A, 12345678, v1.0"

    smua_sense = 0

    @message(r'print\(smua\.sense\)')
    def query_smua_sense(self, message):
        return format(float(type(self).smua_sense), 'E')

    @message(r'smua\.sense\s*\=\s*(\d+)')
    def write_smua_sense(self, message):
        d = {'LOCAL': 0, 'REMOTE': 1, 'CALA': 2}
        value = split_message(message)[-1]
        if value in d:
            value = d[value]
        type(self).smua_sense = value

if __name__ == "__main__":
    run(K2657AHandler)

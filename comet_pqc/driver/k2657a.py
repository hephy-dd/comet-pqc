import datetime
import logging
import time

from comet.driver import Driver
from comet.driver import lock, Property, Action
from comet.driver import IEC60488

__all__ = ['K2657A']

class K2657A(IEC60488):
    """Keithley Models 2657A High Power System SourceMeter."""

    class Beeper(Driver):

        @Property(values=[False, True])
        def enable(self):
            return bool(float(self.resource.query('print(beeper.enable)')))

        @enable.setter
        @lock
        def enable(self, value):
            self.resource.write(f'beeper.enable = {value:d}')
            self.resource.query('*OPC?')

    class ErrorQueue(Driver):

        @Property()
        def count(self):
            return bool(float(self.resource.query('print(errorqueue.count)')))

        @Action()
        def next(self):
            return self.resource.query('print(errorqueue.next())').split('\t')

        @Action()
        def clear(self):
            self.resource.write('errorqueue.clear()')
            self.resource.query('*OPC?')

    class Measure(Driver):

        def __init__(self, resource):
            super().__init__(resource)
            self.filter = self.Filter(resource)

        class Filter(Driver):

            @Property(minimum=1, maximum=100)
            def count(self):
                return int(self.resource.query('print(smua.measure.filter.count)'))

            @count.setter
            @lock
            def count(self, value):
                self.resource.write(f'smua.measure.filter.count = {value:d}')
                self.resource.query('*OPC?')

            @Property(values=[False, True])
            def enable(self):
                return bool(int(self.resource.query('print(smua.measure.filter.enable)')))

            @enable.setter
            @lock
            def enable(self, value):
                self.resource.write(f'smua.measure.filter.enable = {value:d}')
                self.resource.query('*OPC?')

            @Property()
            def type(self):
                value = int(float(self.resource.query('print(smua.measure.filter.type)')))
                return {0: 'MOVING', 1: 'REPEAT', 2: 'MEDIAN'}[value]

            @type.setter
            @lock
            def type(self, value):
                value = {'MOVING': 0, 'REPEAT': 1, 'MEDIAN': 2}[value]
                self.resource.write(f'smua.measure.filter.type = {value:d}')
                self.resource.query('*OPC?')

        @Property(minimum=0.001, maximum=25.0)
        def nplc(self):
            return float(self.resource.query('print(smua.measure.nplc)'))

        @nplc.setter
        @lock
        def nplc(self, value):
            self.resource.write(f'smua.measure.nplc = {value:E}')
            self.resource.query('*OPC?')

        @Action()
        def i(self):
            return float(self.resource.query('print(smua.measure.i())'))

        @Action()
        def v(self):
            return float(self.resource.query('print(smua.measure.v())'))

        @Action()
        def r(self):
            return float(self.resource.query('print(smua.measure.r())'))

        @Action()
        def p(self):
            return float(self.resource.query('print(smua.measure.p())'))

        @Action()
        def iv(self):
            result = self.resource.query('print(smua.measure.iv())').split(',')
            return float(result[0]), float(result[1])

    class Source(Driver):

        @Property()
        def compliance(self):
            return {'false': False, 'true': True}[self.resource.query('print(smua.source.compliance)')]

        @Property()
        def func(self):
            value = int(float(self.resource.query('print(smua.source.func)')))
            return {0: 'DCAMPS', 1: 'DCVOLTS'}[value]

        @func.setter
        @lock
        def func(self, value):
            value = {'DCAMPS': 0, 'DCVOLTS': 1}[value]
            self.resource.write(f'smua.source.func = {value:d}')
            self.resource.query('*OPC?')

        @Property(values=[False, True])
        def highc(self):
            return bool(float(self.resource.query('print(smua.source.highc)')))

        @highc.setter
        @lock
        def highc(self, value):
            self.resource.write(f'smua.source.highc = {value:d}')
            self.resource.query('*OPC?')

        @Property()
        def leveli(self):
            return float(self.resource.query('print(smua.source.leveli)'))

        @leveli.setter
        @lock
        def leveli(self, value):
            self.resource.write(f'smua.source.leveli = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def limiti(self):
            return float(self.resource.query('print(smua.source.limiti)'))

        @limiti.setter
        @lock
        def limiti(self, value):
            self.resource.write(f'smua.source.limiti = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def levelv(self):
            return float(self.resource.query('print(smua.source.levelv)'))

        @levelv.setter
        @lock
        def levelv(self, value):
            self.resource.write(f'smua.source.levelv = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def limitv(self):
            return float(self.resource.query('print(smua.source.limitv)'))

        @limitv.setter
        @lock
        def limitv(self, value):
            self.resource.write(f'smua.source.limitv = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def output(self):
            value = int(float(self.resource.query('print(smua.source.output)')))
            return {0: 'OFF', 1: 'ON', 2: 'HIGH_Z'}[value]

        @output.setter
        @lock
        def output(self, value):
            value = {'OFF': 0, 'ON': 1, 'HIGH_Z': 2}[value]
            self.resource.write(f'smua.source.output = {value:d}')
            self.resource.query('*OPC?')

    def __init__(self, resource):
        super().__init__(resource)
        self.beeper = self.Beeper(resource)
        self.errorqueue = self.ErrorQueue(resource)
        self.measure = self.Measure(resource)
        self.source = self.Source(resource)

    @Action()
    @lock
    def reset(self):
        self.resource.write('smua.reset()')
        self.resource.query('*OPC?')

    @Property()
    def sense(self):
        value = int(float(self.resource.query('print(smua.sense)')))
        return {0: 'LOCAL', 1: 'REMOTE', 2: 'CALA'}[value]

    @sense.setter
    @lock
    def sense(self, value):
        value = {'LOCAL': 0, 'REMOTE': 1, 'CALA': 2}[value]
        self.resource.write(f'smua.sense = {value:d}')
        self.resource.query('*OPC?')

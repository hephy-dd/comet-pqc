import random

from comet.emulator.emulator import message, run
from comet.emulator.corvus.venus1 import Venus1Handler

class PQCVenus1Handler(Venus1Handler):

    table_limits = (0.0, 0.0, 0.0, 1000000.0, 100000.0, 25000.0)


    @classmethod
    @message(r'(.*)\s+setlimit')
    def setlimit(cls, value):
        a1, b1, c1, a2, b2, c2 = map(float, value.split())
        cls.table_limits = a1, b1, c1, a2, b2, c2

    @classmethod
    @message(r'getlimit')
    def getlimit(cls):
        a1, b1, c1, a2, b2, c2 = cls.table_limits
        return cls.read_termination.join((f"{a1:.6f} {b1:.6f}", f"{c1:.6f} {a2:.6f}", f"{b2:.6f} {c2:.6f}"))

if __name__ == '__main__':
    run(PQCVenus1Handler)

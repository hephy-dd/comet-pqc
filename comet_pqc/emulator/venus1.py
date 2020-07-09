"""Corvus Venus1 emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.corvus.venus1 import Venus1Handler as Venus1BaseHandler

__all__ = ['Venus1Handler']

class Venus1Handler(Venus1BaseHandler):

    n = -1

    @message(r'\d\s+getcaldone')
    def query_getcaldone(self, message):
        type(self).n += 1
        return min(type(self).n, 3)

    @message(r'\d\s+getaxis')
    def query_getaxis(self, message):
        return 3

    @message(r'[+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? rmove')
    def write_rmove(self, message):
        x, y, z, command = message.split()
        cls = self.__class__
        cls.x_pos += float(x)
        cls.y_pos += float(y)
        cls.z_pos += float(z)
        cls.x_pos = max(0.0, cls.x_pos)
        cls.y_pos = max(0.0, cls.y_pos)
        cls.z_pos = max(0.0, cls.z_pos)

if __name__ == "__main__":
    run(Venus1Handler)

"""Corvus Venus1 emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.corvus.venus1 import Venus1Handler as Venus1BaseHandler

__all__ = ['Venus1Handler']

class Venus1Handler(Venus1BaseHandler):

    getcaldone = 3
    getaxis = 3
    geterror = 0
    getmerror = 0

    joystick = False

    @message(r'\d\s+getcaldone')
    def query_getcaldone(self, message):
        return type(self).getcaldone

    @message(r'\d\s+getaxis')
    def query_getaxis(self, message):
        return type(self).getaxis

    @message(r'geterror')
    def query_geterror(self, message):
        return type(self).geterror

    @message(r'getmerror')
    def query_getmerror(self, message):
        return type(self).getmerror

    @message(r'joystick')
    def query_joystick(self, message):
        return type(self).joystick

    @message(r'\d\s+joystick')
    def write_joystick(self, message):
        state = bool(int(message.split([0])))
        type(self).joystick = state

    @message(r'[+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? rmove')
    def write_rmove(self, message):
        x, y, z = map(float, message.split()[:3])
        type(self).x_pos = max(0.0, type(self).x_pos + x)
        type(self).y_pos = max(0.0, type(self).y_pos + y)
        type(self).z_pos = max(0.0, type(self).z_pos + z)

    @message(r'[+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? [+-]?\d+(\.\d+)? move')
    def write_move(self, message):
        x, y, z = map(float, message.split()[:3])
        type(self).x_pos = max(0.0, x)
        type(self).y_pos = max(0.0, y)
        type(self).z_pos = max(0.0, z)

if __name__ == "__main__":
    run(Venus1Handler)

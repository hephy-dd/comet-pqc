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

if __name__ == "__main__":
    run(K6517BHandler)

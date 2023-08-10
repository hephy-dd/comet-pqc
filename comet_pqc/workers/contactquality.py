import logging
import time
from typing import List

import comet

__all__ = ["ContactQualityWorker"]

logger = logging.getLogger(__name__)


class ContactQualityWorker(comet.Process):

    def __init__(self, station, update_interval=.250, matrix_channels=None, reading=None, **kwargs):
        super().__init__(**kwargs)
        self.station = station
        self.update_interval = update_interval
        self.matrix_channels = matrix_channels or []
        self.reading = reading
        self._cached_reading = None, None

    def cached_reading(self) -> tuple:
        return self._cached_reading

    def measure(self):
        with self.station.lcr_resource:  # TODO
            lcr = self.station.lcr
            lcr.reset()
            lcr.quick_setup_cp_rp()
            while self.running:
                prim, sec = lcr.acquire_reading()
                self.emit(self.reading, prim, sec)
                self._cached_reading = prim, sec
                time.sleep(self.update_interval)

    def run(self):
        self._cached_reading = None, None
        try:
            self.station.matrix.safe_close_channels(self.matrix_channels)
            self.measure()
        finally:
            self._cached_reading = None, None
            self.station.matrix.open_all_channels()

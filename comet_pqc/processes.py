import logging
import random
import time
import threading

import comet

from .measurements import measurement_factory

class CalibrateProcess(comet.Process):
    """Calibration process for CORVUS table."""

    def run(self):
        steps = 8
        self.push("message", "Calibrating...")
        for i in range(steps):
            self.push("progress", i + 1, steps)
            time.sleep(1)
        self.push("message", None)

class MeasureProcess(comet.Process):
    """Measure process executing a sequence of measurements."""

    cuck_config = {}
    wafer_config = {}
    sequence_config = {}
    wafers = []

    manual_mode = False
    auto_continue = True
    wait_for_continue = threading.Event()
    wait_interval = .25

    def pause(self):
        self.wait_for_continue.set()
        while self.wait_for_continue.is_set():
            if not self.running:
                return False
            time.sleep(self.wait_interval)
        return True

    def unpause(self):
        self.wait_for_continue.clear()

    def run_measurement(self, measurement):
        self.push("show_panel", measurement)
        self.pause()
        measurement = measurement_factory(measurement.type)
        if measurement is None:
            raise RuntimeError(f"No such measurement '{measurement.type}'")
        try:
            measurement.run()
        except Exception as e:
            raise e

    def run(self):
        self.push("message", "Measuring...")
        self.wait_for_continue.clear()
        wafer_config = self.wafer_config
        config = self.sequence_config
        # Count measurements
        count = 0
        step = 0
        for wafer in self.wafers:
            for item in config.items:
                if item.enabled:
                    for measurement in item.measurements:
                        if measurement.enabled:
                            count += 1
        if not self.manual_mode:
            for wafer in self.wafers:
                ref = {}
                self.push("message", "Move to wafer reference point...")
                self.push("select_ref", ref)
                if not self.pause():
                    break
        for wafer in self.wafers:
            for item in config.items:
                if not self.running:
                    break
                if item.enabled:
                    item.locked = True
                    item.state = "ACTIVE"
                    if self.manual_mode:
                        ref = {}
                        self.push("message", "Manually move to flute...")
                        self.push("next_flute", ref)
                        if not self.pause():
                            break
                    for measurement in item.measurements:
                        if measurement.enabled:
                            measurement.locked = True
                            measurement.state = "ACTIVE"
                            if not self.auto_continue:
                                self.push("enable_continue")
                                self.push("message", "Waiting for user to continue...")
                                if not self.pause():
                                    break
                            if not self.running:
                                break
                            self.push("progress", step, count)
                            self.push("message", f"Measuring {item.name} {measurement.name}...")
                            self.run_measurement(measurement)
                            measurement.state = "DONE"
                            step += 1
                    item.state = "DONE"
        self.push("message", "Done.")

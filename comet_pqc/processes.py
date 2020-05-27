import logging
import random
import time
import threading
import os

import comet
from comet.device import DeviceMixin

from .measurements import measurement_factory

class CalibrateProcess(comet.Process, DeviceMixin):
    """Calibration process for Corvus table."""

    def run(self):
        self.set("success", False)
        self.events.message("Calibrating...")
        with self.devices.get('corvus') as corvus:
            corvus.mode = 0
            retries = 16
            delay = 1.0

            def handle_error():
                time.sleep(delay)
                error = corvus.error
                if error:
                    raise RuntimeError(f"Corvus: {error}")
                time.sleep(delay)

            def ncal(axis):
                axis.ncal()
                for i in range(retries + 1):
                    if axis.caldone == 1:
                        break
                    time.sleep(delay)
                return i < retries

            def nrm(axis):
                axis.nrm()
                for i in range(retries + 1):
                    if axis.caldone == 3:
                        break
                    time.sleep(delay)
                return i < retries

            handle_error()
            self.events.progress(0, 7)
            self.events.message("Retreating Z axis...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed retreating Z axis")
            time.sleep(delay)

            handle_error()
            self.events.progress(1, 7)
            self.events.message("Calibrating Y axis...")
            if corvus.y.enabled:
                if not ncal(corvus.y):
                    raise RuntimeError("failed to calibrate Y axis")
            time.sleep(delay)

            handle_error()
            self.events.progress(2, 7)
            self.events.message("Calibrating X axis...")
            if corvus.x.enabled:
                if not ncal(corvus.x):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_error()
            self.events.progress(3, 7)
            self.events.message("Range measure X axis...")
            if corvus.x.enabled:
                if not nrm(corvus.x):
                    raise RuntimeError("failed to ragne measure X axis")
            time.sleep(delay)

            handle_error()
            self.events.progress(4, 7)
            self.events.message("Range measure Y axis...")
            if corvus.y.enabled:
                if not nrm(corvus.y):
                    raise RuntimeError("failed to range measure Y axis")
            time.sleep(delay)

            handle_error()
            corvus.rmove(-1000, -1000, 0)
            for i in range(retries):
                pos = corvus.pos
                if pos[:2] == (0, 0):
                    break
                time.sleep(delay)
            if pos[:2] != (0, 0):
                raise RuntimeError("failed to relative move, current pos: {}".format(pos))

            handle_error()
            self.events.progress(5, 7)
            self.events.message("Calibrating Z axis minimum...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_error()
            self.events.progress(6, 7)
            self.events.message("Range measure Z axis maximum...")
            if corvus.z.enabled:
                if not nrm(corvus.z):
                    raise RuntimeError("failed to range measure Z axis")
            time.sleep(delay)

            handle_error()
            corvus.rmove(0, 0, -1000)
            for i in range(retries):
                pos = corvus.pos
                if pos == (0, 0, 0):
                    break
                time.sleep(delay)
            if pos != (0, 0, 0):
                raise RuntimeError("failed to calibrate axes, current pos: {}".format(pos))

            handle_error()
            self.events.progress(7, 7)
            self.events.message(None)
        self.set("success", True)

class MeasureProcess(comet.Process):
    """Measure process executing a single measurements."""

    measurement_item = None

    def initialize(self):
        self.events.message("Initialize measurement...")

    def process(self):
        self.events.message("Process measurement...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        # TODO
        measurement = measurement_factory(self.measurement_item.type, self)
        measurement.sample_name = sample_name
        measurement.sample_type = sample_type
        measurement.output_dir = output_dir
        measurement.measurement_item = self.measurement_item
        try:
            self.events.measurement_state(self.measurement_item, "Active")
            measurement.run()
        except Exception:
            self.events.measurement_state(self.measurement_item, "Failed")
            raise
        else:
            self.events.measurement_state(self.measurement_item, "Success")

    def finalize(self):
        self.events.message("Finalize measurement...")
        self.measurement_item = None

    def run(self):
        self.events.message("Starting measurement...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.events.message("Measurement done.")

class SequenceProcess(comet.Process):
    """Sequence process executing a sequence of measurements."""

    sequence_tree = []

    def initialize(self):
        self.events.message("Initialize sequence...")

    def process(self):
        self.events.message("Process sequence...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        for contact_item in self.sequence_tree:
            if not self.running:
                break
            if not contact_item.enabled:
                continue
            self.events.measurement_state(contact_item, "Active")
            self.set("continue_contact", False)
            self.events.continue_contact(contact_item)
            while self.running:
                if self.get("continue_contact", False):
                    break
                time.sleep(.100)
            self.set("continue_contact", False)
            if not self.running:
                break
            logging.info(" => %s", contact_item.name)
            for measurement_item in contact_item.children:
                if not self.running:
                    break
                if not measurement_item.enabled:
                    self.events.measurement_state(measurement_item, "Skipped")
                    continue
                autopilot = self.get("autopilot", False)
                logging.info("Autopilot: %s", ["OFF", "ON"][autopilot])
                if not autopilot:
                    logging.info("Waiting for %s", measurement_item.name)
                    self.events.measurement_state(measurement_item, "Waiting")
                    self.set("continue_measurement", False)
                    self.events.continue_measurement(measurement_item)
                    while self.running:
                        if self.get("continue_measurement", False):
                            break
                        time.sleep(.100)
                    self.set("continue_measurement", False)
                if not self.running:
                    self.events.measurement_state(measurement_item, "Aborted")
                    break
                logging.info("Run %s", measurement_item.name)
                self.events.measurement_state(measurement_item, "Active")
                # TODO
                measurement = measurement_factory(measurement_item.type, self)
                measurement.sample_name = sample_name
                measurement.sample_type = sample_type
                measurement.output_dir = output_dir
                measurement.measurement_item = measurement_item
                try:
                    measurement.run()
                except Exception as e:
                    logging.error(format(e))
                    logging.error("%s failed.", measurement_item.name)
                    self.events.measurement_state(measurement_item, "Failed")
                    ## raise
                else:
                    logging.info("%s done.", measurement_item.name)
                    self.events.measurement_state(measurement_item, "Success")
            self.events.measurement_state(contact_item, None)

    def finalize(self):
        self.events.message("Finalize sequence...")
        self.sequence_tree = []

    def run(self):
        self.events.message("Starting sequence...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.events.message("Sequence done.")

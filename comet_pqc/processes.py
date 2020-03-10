import logging
import random
import time
import threading
import os

import comet

from .measurements import measurement_factory

class CalibrateProcess(comet.Process):
    """Calibration process for Corvus table."""

    def run(self):
        steps = 8
        self.events.message("Calibrating...")
        for i in range(steps):
            self.events.progress(i + 1, steps)
            time.sleep(1)
        self.events.message(None)

class MeasureProcess(comet.Process):
    """Measure process executing a single measurements."""

    measurement_item = None

    def initialize(self):
        self.events.message("Initialize measurement...")

    def process(self):
        self.events.message("Process measurement...")
        sample_name = self.get("sample_name")
        wafer_type = self.get("wafer_type")
        output_dir = self.get("output_dir")
        # TODO
        measurement = measurement_factory(self.measurement_item.type, self)
        measurement.sample_name = sample_name
        measurement.wafer_type = wafer_type
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

    sequence_tree = None

    def initialize(self):
        self.events.message("Initialize sequence...")

    def process(self):
        self.events.message("Process sequence...")
        sample_name = self.get("sample_name")
        wafer_type = self.get("wafer_type")
        output_dir = self.get("output_dir")
        for connection_item in self.sequence_tree:
            if not self.running:
                break
            if not connection_item.enabled:
                continue
            self.events.measurement_state(connection_item, "Active")
            self.set("continue_connection", False)
            self.events.continue_connection(connection_item)
            while self.running:
                if self.get("continue_connection", False):
                    break
                time.sleep(.100)
            self.set("continue_connection", False)
            if not self.running:
                break
            logging.info(" => %s", connection_item.name)
            for measurement_item in connection_item.children:
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
                measurement.wafer_type = wafer_type
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
            self.events.measurement_state(connection_item, None)

    def finalize(self):
        self.events.message("Finalize sequence...")
        self.sequence_tree = None

    def run(self):
        self.events.message("Starting sequence...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.events.message("Sequence done.")

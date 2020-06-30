import logging
import random
import time
import threading
import os

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.driver.corvus import Venus1

from ..utils import format_metric
from ..measurements import measurement_factory
from ..driver import EnvironmentBox
from ..driver import K707B

class BaseProcess(comet.Process, ResourceMixin):

    def safe_initialize_vsrc(self, resource):
        resource.query("*IDN?")
        if int(resource.query(":OUTP:STAT?")):
            self.emit("message", "Ramping down VSource...")
            start_voltage = float(resource.query(":SOUR:VOLT:LEV?"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f":SOUR:VOLT:LEV {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output VSource...")
            resource.write(":OUTP:STAT OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized VSource.")

    def safe_initialize_hvsrc(self, resource):
        resource.query("*IDN?")
        if int(float(resource.query("print(smua.source.output)"))):
            self.emit("message", "Ramping down HVSource...")
            start_voltage = float(resource.query("print(smua.source.levelv)"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f"smua.source.levelv = {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output HVSource...")
            resource.write("smua.source.output = 0")
            resource.query("*OPC?")
        self.emit("message", "Initialized HVSource.")

    def discarge_decoupling(self, device):
        device.identification
        self.emit("message", "Auto-discharging decoupling box...")
        device.discharge()
        self.emit("message", "Auto-discharged decoupling box.")

    def initialize_matrix(self, resource):
        matrix = K707B(resource)
        matrix.identification
        logging.info("matrix: open all channels.")
        matrix.channel.open()
        channels = matrix.channel.getclose()
        logging.info("matrix channels: %s", channels)
        # self.emit("message", "Initialized Matrix.")

    def safe_initialize(self):
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.error("unable to connect with VSource")
            raise RuntimeError("Failed to connect with VSource")
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.warning("unable to connect with HVSource")
        if self.get("use_environ"):
            with self.resources.get("environ") as environ_resource:
                environ = EnvironmentBox(environ_resource)
                self.discarge_decoupling(environ)
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self):
        with self.resources.get("vsrc") as vsrc:
            self.safe_initialize_vsrc(vsrc)
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.warning("unable to connect with HVSource")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.warning("unable to connect with: Matrix")

class MeasureProcess(BaseProcess):
    """Measure process executing a single measurements."""

    measurement_item = None

    def __init__(self, message, progress, measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading

    def initialize(self):
        self.emit("message", "Initialize measurement...")
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process measurement...")
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
            self.emit("measurement_state", self.measurement_item, "Active")
            measurement.run()
        except Exception:
            self.emit("measurement_state", self.measurement_item, "Failed")
            raise
        else:
            self.emit("measurement_state", self.measurement_item, "Success")

    def finalize(self):
        self.emit("message", "Finalize measurement...")
        self.measurement_item = None
        self.safe_finalize()

    def run(self):
        self.emit("message", "Starting measurement...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.emit("message", "Measurement done.")

class SequenceProcess(BaseProcess):
    """Sequence process executing a sequence of measurements."""

    sequence_tree = []

    def __init__(self, message, progress, continue_contact, continue_measurement,
                 measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.continue_contact = continue_contact
        self.continue_measurement = continue_measurement
        self.measurement_state = measurement_state
        self.reading = reading

    def initialize(self):
        self.emit("message", "Initialize sequence...")
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process sequence...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        for contact_item in self.sequence_tree:
            if not self.running:
                break
            if not contact_item.enabled:
                continue
            self.emit("measurement_state", contact_item, "Active")
            self.set("continue_contact", False)
            self.emit("continue_contact", contact_item)
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
                    self.emit("measurement_state", measurement_item, "Skipped")
                    continue
                autopilot = self.get("autopilot", False)
                logging.info("Autopilot: %s", ["OFF", "ON"][autopilot])
                if not autopilot:
                    logging.info("Waiting for %s", measurement_item.name)
                    self.emit("measurement_state", measurement_item, "Waiting")
                    self.set("continue_measurement", False)
                    self.emit("continue_measurement", measurement_item)
                    while self.running:
                        if self.get("continue_measurement", False):
                            break
                        time.sleep(.100)
                    self.set("continue_measurement", False)
                if not self.running:
                    self.emit("measurement_state", measurement_item, "Aborted")
                    break
                logging.info("Run %s", measurement_item.name)
                self.emit("measurement_state", measurement_item, "Active")
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
                    self.emit("measurement_state", measurement_item, "Failed")
                    ## raise
                else:
                    logging.info("%s done.", measurement_item.name)
                    self.emit("measurement_state", measurement_item, "Success")
            self.emit("measurement_state", contact_item, None)

    def finalize(self):
        self.emit("message", "Finalize sequence...")
        self.sequence_tree = []
        self.safe_finalize()

    def run(self):
        self.emit("message", "Starting sequence...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.emit("message", "Sequence done.")

import datetime
import logging
import random
import time
import threading
import traceback
import os

import pyvisa

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.process import ProcessMixin
from comet.driver.corvus import Venus1
from comet.driver.hephy import EnvironmentBox
from comet.driver.keithley import K707B

from ..utils import format_metric
from ..measurements.measurement import ComplianceError
from ..measurements import measurement_factory

from ..sequence import MeasurementTreeItem
from ..sequence import ContactTreeItem
from ..sequence import SampleTreeItem
from ..sequence import SamplesItem

__all__ = ['MeasureProcess']

class LogFileHandler:
    """Context manager for log files."""

    Format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    DateFormat = '%Y-%m-%dT%H:%M:%S'

    def __init__(self, filename=None):
        self.__filename = filename
        self.__handler = None
        self.__logger = logging.getLogger()

    def create_path(self, filename):
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

    def create_handler(self, filename):
        self.create_path(filename)
        handler = logging.FileHandler(filename=filename)
        handler.setFormatter(logging.Formatter(
            fmt=self.Format,
            datefmt=self.DateFormat
        ))
        return handler

    def __enter__(self):
        if self.__filename:
            self.__handler = self.create_handler(self.__filename)
            self.__logger.addHandler(self.__handler)
        return self

    def __exit__(self, *exc):
        if self.__handler is not None:
            self.__logger.removeHandler(self.__handler)
        return False

class BaseProcess(comet.Process, ResourceMixin, ProcessMixin):

    def create_filename(self, measurement, suffix=''):
        filename = comet.safe_filename(f"{measurement.basename}{suffix}")
        return os.path.join(self.get('output_dir'), measurement.sample_name, filename)

    def safe_initialize_hvsrc(self, resource):
        resource.query("*IDN?")
        if int(resource.query(":OUTP:STAT?")):
            self.emit("message", "Ramping down HVSource...")
            start_voltage = float(resource.query(":SOUR:VOLT:LEV?"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f":SOUR:VOLT:LEV {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output HVSource...")
            resource.write(":OUTP:STAT OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized HVSource.")

    def safe_initialize_vsrc(self, resource):
        resource.query("*IDN?")
        if int(float(resource.query("print(smua.source.output)"))):
            self.emit("message", "Ramping down VSource...")
            start_voltage = float(resource.query("print(smua.source.levelv)"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f"smua.source.levelv = {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output VSource...")
            resource.write("smua.source.output = 0")
            resource.query("*OPC?")
        self.emit("message", "Initialized VSource.")

    def discharge_decoupling(self, context):
        self.emit("message", "Auto-discharging decoupling box...")
        context.discharge()
        self.emit("message", "Auto-discharged decoupling box.")

    def initialize_matrix(self, resource):
        self.emit("message", "Open all matrix channels...")
        matrix = K707B(resource)
        matrix.identification
        logging.info("matrix: open all channels.")
        matrix.channel.open()
        channels = matrix.channel.getclose()
        logging.info("matrix channels: %s", channels)
        self.emit("message", "Opened all matrix channels.")

    def safe_initialize(self):
        try:
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    environment.set_test_led(True)
        except Exception:
            logging.warning("unable to connect with environment box (test LED ON)")
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.error("unable to connect with HVSource")
            raise RuntimeError("Failed to connect with HVSource")
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.warning("unable to connect with VSource")
        try:
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    self.discharge_decoupling(environment)
        except Exception:
            logging.warning("unable to connect with environment box (discharge decoupling)")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self):
        with self.resources.get("hvsrc") as hvsrc:
            self.safe_initialize_hvsrc(hvsrc)
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.warning("unable to connect with VSource")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.warning("unable to connect with: Matrix")
            raise RuntimeError("Failed to connect with Matrix")
        try:
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    environment.set_test_led(False)
        except Exception:
            logging.warning("unable to connect with environment box (test LED OFF)")

class MeasureProcess(BaseProcess):
    """Measure process executing a samples, contacts and measurements."""

    context = None

    def __init__(self, message, progress, measurement_state=None, reading=None, save_to_image=None, push_summary=None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading
        self.save_to_image = save_to_image
        self.push_summary = push_summary
        self.stop_requested = False

    def stop(self):
        """Stop running measurements."""
        self.stop_requested = True
        super().stop()

    def safe_move_table(self, position):
        table_process = self.processes.get("table")
        if table_process.running and table_process.enabled:
            logging.info("safe move table to %s", position)
            self.emit("message", "Moving table...")
            self.set("movement_finished", False)
            def absolute_move_finished():
                table_process.absolute_move_finished = None
                self.set("table_position", table_process.get_cached_position())
                self.set("movement_finished", True)
                self.emit("message", "Moving table... done.")
            table_process.absolute_move_finished = absolute_move_finished
            table_process.safe_absolute_move(*position)
            while not self.get("movement_finished"):
                time.sleep(.25)
            logging.info("safe move table to %s... done.", position)

    def initialize(self):
        self.emit("message", "Initialize...")
        self.stop_requested = False
        try:
            self.safe_initialize()
        except Exception:
            self.emit("message", "Initialize... failed.")
            raise
        else:
            self.emit("message", "Initialize... done.")

    def process_measurement(self, measurement_item):
        self.emit("message", "Process measurement...")
        sample_name = measurement_item.contact.sample.name
        sample_type = measurement_item.contact.sample.sample_type
        table_position = self.get("table_position")
        operator = self.get("operator")
        output_dir = self.get("output_dir")
        sample_output_dir = os.path.join(output_dir, sample_name)
        if not os.path.exists(sample_output_dir):
            os.makedirs(sample_output_dir)
        write_logfiles = self.get("write_logfiles")
        # TODO
        measurement = measurement_factory(
            measurement_item.type,
            process=self,
            sample_name=sample_name,
            sample_type=sample_type,
            table_position=table_position,
            operator=operator
        )
        measurement.measurement_item = measurement_item
        log_filename = self.create_filename(measurement, suffix='.log') if write_logfiles else None
        plot_filename = self.create_filename(measurement, suffix='.png')
        state = measurement_item.ActiveState
        self.emit('show_measurement', measurement_item)
        self.emit("measurement_state", measurement_item, state)
        with LogFileHandler(log_filename):
            try:
                measurement.run()
            except ResourceError as e:
                self.emit("message", "Process... failed.")
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = measurement_item.TimeoutState
                elif isinstance(e.exc, BrokenPipeError):
                    state = measurement_item.TimeoutState
                else:
                    state = measurement_item.ErrorState
                raise
            except ComplianceError:
                self.emit("message", "Process... failed.")
                state = measurement_item.ComplianceState
                raise
            except Exception as e:
                self.emit("message", "Process... failed.")
                state = measurement_item.ErrorState
                raise
            else:
                self.emit("message", "Process... done.")
                if self.stop_requested:
                    state = measurement_item.StoppedState
                else:
                    state = measurement_item.SuccessState
            finally:
                self.emit("measurement_state", measurement_item, state, measurement.quality)
                self.emit("save_to_image", measurement_item, plot_filename)
                self.emit('push_summary', measurement.timestamp, sample_name, sample_type, measurement_item.contact.name, measurement_item.name, state)
                if self.get("serialize_json"):
                    with open(self.create_filename(measurement, suffix='.json'), 'w') as fp:
                        measurement.serialize_json(fp)
                if self.get("serialize_txt"):
                    # See https://docs.python.org/3/library/csv.html#csv.DictWriter
                    with open(self.create_filename(measurement, suffix='.txt'), 'w', newline='') as fp:
                        measurement.serialize_txt(fp)

    def process_contact(self, contact_item):
        self.emit("message", "Process contact...")
        self.emit("measurement_state", contact_item, contact_item.ProcessingState)
        logging.info(" => %s", contact_item.name)
        prev_measurement_item = None
        self.set("movement_finished", False)
        if self.get("move_to_contact") and contact_item.has_position:
            self.safe_move_table(contact_item.position)
        table_position = self.get("table_position")
        prev_measurement_item = None
        for measurement_item in contact_item.children:
            if not self.running:
                break
            if not measurement_item.enabled:
                continue
            if not self.running:
                self.emit("measurement_state", measurement_item, measurement_item.StoppedState)
                break
            if prev_measurement_item:
                self.emit('hide_measurement', prev_measurement_item)
            try:
                self.process_measurement(measurement_item)
            except Exception as exc:
                tb = traceback.format_exc()
                logging.error("%s: %s", measurement_item.name, tb)
                logging.error("%s: %s", measurement_item.name, exc)
            prev_measurement_item = measurement_item
        self.emit("measurement_state", contact_item, contact_item.StoppedState if self.stop_requested else contact_item.SuccessState)
        if prev_measurement_item:
            self.emit('hide_measurement', prev_measurement_item)

    def process_sample(self, sample_item):
        self.emit("message", "Process sample...")
        self.emit("measurement_state", sample_item, sample_item.ProcessingState)
        # Check contact positions
        for contact_item in sample_item.children:
            if contact_item.enabled:
                if not contact_item.has_position:
                    raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name}")
        for contact_item in sample_item.children:
            if not self.running:
                break
            if not contact_item.enabled:
                continue
            if not self.running:
                self.emit("measurement_state", contact_item, contact_item.StoppedState)
                break
            self.process_contact(contact_item)
        self.emit("measurement_state", sample_item, sample_item.StoppedState if self.stop_requested else sample_item.SuccessState)
        move_to_after_position = self.get("move_to_after_position")
        if self.get("move_to_after_position") is not None:
            self.safe_move_table(move_to_after_position)

    def process_samples(self, samples_item):
        self.emit("message", "Process samples...")
        # Check contact positions
        for sample_item in samples_item.children:
            if sample_item.enabled:
                for contact_item in sample_item.children:
                    if contact_item.enabled:
                        if not contact_item.has_position:
                            raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name}")
        for sample_item in samples_item.children:
            if not self.running:
                break
            if not sample_item.enabled:
                continue
            if not self.running:
                self.emit("measurement_state", sample_item, contact_item.StoppedState)
                break
            self.process_sample(sample_item)
        move_to_after_position = self.get("move_to_after_position")
        if self.get("move_to_after_position") is not None:
            self.safe_move_table(move_to_after_position)

    def process(self):
        if isinstance(self.context, MeasurementTreeItem):
            self.process_measurement(self.context)
        elif isinstance(self.context, ContactTreeItem):
            self.process_contact(self.context)
        elif isinstance(self.context, SampleTreeItem):
            self.process_sample(self.context)
        elif isinstance(self.context, SamplesItem):
            self.process_samples(self.context)
        else:
            raise TypeError(type(self.context))

    def finalize(self):
        self.emit("message", "Finalize...")
        self.context = None
        try:
            self.safe_finalize()
        except Exception:
            self.emit("message", "Finalize... failed.")
            raise
        else:
            self.emit("message", "Finalize... done.")
        finally:
            self.stop_requested = False

    def run(self):
        try:
            try:
                self.initialize()
                self.process()
            finally:
                self.finalize()
        except Exception:
            self.emit("message", "Measurement failed.")
            raise
        else:
            self.emit("message", "Measurement done.")

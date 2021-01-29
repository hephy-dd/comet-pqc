import datetime
import logging
import random
import time
import threading
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
        return os.path.join(self.get('output_dir'), filename)

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
    """Measure process executing a single measurements."""

    measurement_item = None

    def __init__(self, message, progress, measurement_state=None, reading=None, save_to_image=None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading
        self.save_to_image = save_to_image
        self.push_summary = None
        self.stopped = False

    def stop(self):
        self.stopped = True
        super().stop()

    def initialize(self):
        self.emit("message", "Initialize measurement...")
        self.stopped = False
        try:
            self.safe_initialize()
        except Exception:
            self.emit("message", "Initialize measurement... failed.")
            raise
        else:
            self.emit("message", "Initialize measurement... done.")

    def process(self):
        self.emit("message", "Process measurement...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        table_position = self.get("table_position")
        operator = self.get("operator")
        output_dir = self.get("output_dir")
        write_logfiles = self.get("write_logfiles")
        # TODO
        measurement = measurement_factory(
            self.measurement_item.type,
            process=self,
            sample_name=sample_name,
            sample_type=sample_type,
            table_position=table_position,
            operator=operator
        )
        measurement.measurement_item = self.measurement_item
        log_filename = self.create_filename(measurement, suffix='.log') if write_logfiles else None
        plot_filename = self.create_filename(measurement, suffix='.png')
        state = self.measurement_item.ActiveState
        self.emit("measurement_state", self.measurement_item, state)
        with LogFileHandler(log_filename):
            try:
                measurement.run()
            except ResourceError as e:
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = self.measurement_item.TimeoutState
                elif isinstance(e.exc, BrokenPipeError):
                    state = self.measurement_item.TimeoutState
                else:
                    state = self.measurement_item.ErrorState
                raise
            except ComplianceError:
                state = self.measurement_item.ComplianceState
                raise
            except Exception as e:
                state = self.measurement_item.ErrorState
                raise
            else:
                if self.stopped:
                    state = self.measurement_item.StoppedState
                else:
                    state = self.measurement_item.SuccessState
            finally:
                self.emit("measurement_state", self.measurement_item, state, measurement.quality)
                self.emit("save_to_image", self.measurement_item, plot_filename)
                self.emit('push_summary', measurement.timestamp, sample_name, sample_type, self.measurement_item.contact.name, self.measurement_item.name, state)
                if self.get("serialize_json"):
                    with open(self.create_filename(measurement, suffix='.json'), 'w') as fp:
                        measurement.serialize_json(fp)
                if self.get("serialize_txt"):
                    # See https://docs.python.org/3/library/csv.html#csv.DictWriter
                    with open(self.create_filename(measurement, suffix='.txt'), 'w', newline='') as fp:
                        measurement.serialize_txt(fp)

    def finalize(self):
        self.emit("message", "Finalize measurement...")
        self.measurement_item = None
        try:
            self.safe_finalize()
        except Exception:
            self.emit("message", "Finalize measurement... failed.")
            raise
        else:
            self.emit("message", "Finalize measurement... done.")
        finally:
            self.stopped = False

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

class SequenceProcess(BaseProcess):
    """Sequence process executing a sequence of measurements."""

    # sequence_tree = []
    contact_item = None

    def __init__(self, message, progress, measurement_state=None, reading=None, save_to_image=None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading
        self.save_to_image = save_to_image
        self.stopped = False

    def stop(self):
        self.stopped = True
        super().stop()

    def initialize(self):
        self.emit("message", "Initialize sequence...")
        self.stopped = False
        try:
            self.safe_initialize()
        except Exception:
            self.emit("message", "Initialize sequence... failed.")
            raise
        else:
            self.emit("message", "Initialize sequence... done.")

    def safe_move_table(self, position):
        table_process = self.processes.get("table")
        if table_process.running and table_process.enabled:
            self.emit("message", "Moving table...")
            def absolute_move_finished():
                table_process.absolute_move_finished = None
                self.set("table_position", table_process.get_cached_position())
                self.set("movement_finished", True)
                self.emit("message", "Moving table... done.")
            table_process.absolute_move_finished = absolute_move_finished
            table_process.safe_absolute_move(*position)
            while not self.get("movement_finished"):
                time.sleep(.25)

    def process(self):
        self.emit("message", "Process sequence...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        operator = self.get("operator")
        output_dir = self.get("output_dir")
        write_logfiles = self.get("write_logfiles")
        contact_item = self.contact_item
        self.emit("measurement_state", contact_item, contact_item.ProcessingState)
        logging.info(" => %s", contact_item.name)
        prev_measurement_item = None
        self.set("movement_finished", False)
        if self.get("move_to_contact") and contact_item.has_position:
            self.safe_move_table(contact_item.position)
        table_position = self.get("table_position")
        for measurement_item in contact_item.children:
            if not self.running:
                break
            if not measurement_item.enabled:
                continue
            if not self.running:
                self.emit("measurement_state", measurement_item, measurement_item.StoppedState)
                break
            logging.info("Run %s", measurement_item.name)
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
            state = "Active"
            self.emit("measurement_state", measurement_item, state)
            if prev_measurement_item:
                self.emit('hide_measurement', prev_measurement_item)
            self.emit('show_measurement', measurement_item)
            with LogFileHandler(log_filename):
                try:
                    measurement.run()
                except ResourceError as e:
                    if isinstance(e.exc, pyvisa.errors.VisaIOError):
                        state = measurement_item.TimeoutState
                    elif isinstance(e.exc, BrokenPipeError):
                        state = measurement_item.TimeoutState
                    else:
                        state = measurement_item.ErrorState
                    logging.error(format(e))
                    logging.error("%s failed.", measurement_item.name)
                except ComplianceError as e:
                    logging.error(format(e))
                    logging.error("%s failed.", measurement_item.name)
                    state = "Compliance"
                except Exception as e:
                    logging.error(format(e))
                    logging.error("%s failed.", measurement_item.name)
                    state = measurement_item.ErrorState
                else:
                    if self.stopped:
                        state = measurement_item.StoppedState
                    else:
                        state = measurement_item.SuccessState
                    logging.info("%s done.", measurement_item.name)
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

            prev_measurement_item = measurement_item
        self.emit("measurement_state", contact_item)
        if prev_measurement_item:
            self.emit('hide_measurement', prev_measurement_item)

        if self.get("move_to_after_position"):
            self.safe_move_table(self.get("move_to_after_position"))

    def finalize(self):
        self.emit("message", "Finalize sequence...")
        self.contact_item = None
        try:
            self.safe_finalize()
        except Exception:
            self.emit("message", "Finalize sequence... failed.")
            raise
        else:
            self.emit("message", "Finalize sequence... done.")
        finally:
            self.stopped = False

    def run(self):
        try:
            try:
                self.initialize()
                self.process()
            finally:
                self.finalize()
        except Exception:
            self.emit("message", "Sequence failed.")
            raise
        else:
            self.emit("message", "Sequence done.")

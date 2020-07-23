import datetime
import logging
import math
import time
import os
import re

import comet
from ..driver import K2410

from ..proxy import create_proxy
from ..utils import format_metric
from ..formatter import PQCFormatter
from ..estimate import Estimate
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

__all__ = ["IVRampMeasurement"]

class IVRampMeasurement(MatrixMeasurement):
    """IV ramp measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('voltage_start', unit='V', required=True)
        self.register_parameter('voltage_stop', unit='V', required=True)
        self.register_parameter('voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('hvsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('hvsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('hvsrc_filter_enable', False, type=bool)
        self.register_parameter('hvsrc_filter_count', 10, type=int)
        self.register_parameter('hvsrc_filter_type', 'repeat', values=('repeat', 'moving'))

    def initialize(self, hvsrc):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 5)

        voltage_start = self.get_parameter('voltage_start')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_filter_enable = self.get_parameter('hvsrc_filter_enable')
        hvsrc_filter_count = self.get_parameter('hvsrc_filter_count')
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')

        hvsrc_proxy = create_proxy(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc_proxy.source_voltage_level,
            hvsrc_current=None,
            hvsrc_output=hvsrc_proxy.output_enable
        ))

        hvsrc_proxy.reset()
        hvsrc_proxy.assert_success()
        hvsrc_proxy.clear()
        hvsrc_proxy.assert_success()

        # Beeper off
        hvsrc_proxy.beeper_enable = False
        hvsrc_proxy.assert_success()
        self.process.emit("progress", 1, 5)

        # Select rear terminal
        logging.info("set route termination: '%s'", hvsrc_route_termination)
        if hvsrc_route_termination == "front":
            hvsrc.resource.write(":ROUT:TERM FRONT")
        elif hvsrc_route_termination == "rear":
            hvsrc.resource.write(":ROUT:TERM REAR")
        hvsrc.resource.query("*OPC?")
        hvsrc_proxy.assert_success()
        self.process.emit("progress", 2, 5)

        # set sense mode
        logging.info("set sense mode: '%s'", hvsrc_sense_mode)
        if hvsrc_sense_mode == "remote":
            hvsrc.resource.write(":SYST:RSEN ON")
        elif hvsrc_sense_mode == "local":
            hvsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {hvsrc_sense_mode}")
        hvsrc.resource.query("*OPC?")
        hvsrc_proxy.assert_success()
        self.process.emit("progress", 3, 5)

        # Compliance
        logging.info("set compliance: %E A", hvsrc_current_compliance)
        hvsrc.sense.current.protection.level = hvsrc_current_compliance
        hvsrc_proxy.assert_success()

        # Range
        current_range = 1.05E-6
        hvsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        hvsrc.resource.query("*OPC?")
        hvsrc_proxy.assert_success()
        #hvsrc.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #hvsrc.resource.query("*OPC?")
        #hvsrc_proxy.assert_success()

        # Filter

        hvsrc_proxy.filter_count = hvsrc_filter_count
        hvsrc_proxy.assert_success()
        hvsrc_proxy.filter_type = hvsrc_filter_type.upper()
        hvsrc_proxy.assert_success()
        hvsrc_proxy.filter_enable = hvsrc_filter_enable
        hvsrc_proxy.assert_success()

        self.process.emit("progress", 5, 5)

        # If output enabled
        if hvsrc_proxy.output_enable:
            voltage = hvsrc_proxy.source_voltage_level

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
            for voltage in comet.Range(voltage, 0, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", f"{voltage:.3f} V")
                hvsrc_proxy.source_voltage_level = voltage
                # hvsrc_proxy.assert_success()
                time.sleep(QUICK_RAMP_DELAY)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            hvsrc_proxy.source_voltage_level = voltage
            hvsrc_proxy.assert_success()
            hvsrc_proxy.output_enable = True
            hvsrc_proxy.assert_success()
            time.sleep(.100)

        self.process.emit("progress", 2, 5)

        if self.process.running:

            voltage = hvsrc_proxy.source_voltage_level

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, hvsrc.resource.query(":FORM:ELEM?").split(",")))
            hvsrc_proxy.assert_success()

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
                hvsrc_proxy.source_voltage_level = voltage
                # hvsrc_proxy.assert_success()
                # Returns <elements> comma separated
                #values = list(map(float, hvsrc.resource.query(":READ?").split(",")))
                #data = zip(elements, values)
                time.sleep(QUICK_RAMP_DELAY)
                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 5, 5)

    def measure(self, hvsrc):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_filter_enable = self.get_parameter('hvsrc_filter_enable')
        hvsrc_filter_count = self.get_parameter('hvsrc_filter_count')
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')

        hvsrc_proxy = create_proxy(hvsrc)

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f", unit="s")
            fmt.add_column("hvsrc_voltage", "E", unit="V")
            fmt.add_column("hvsrc_current", "E", unit="A")
            fmt.add_column("temperature_box", "E", unit="degC")
            fmt.add_column("temperature_chuck", "E", unit="degC")
            fmt.add_column("humidity_box", "E", unit="%")

            # Write meta data
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("voltage_start", f"{voltage_start:G} V")
            fmt.write_meta("voltage_stop", f"{voltage_stop:G} V")
            fmt.write_meta("voltage_step", f"{voltage_step:G} V")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
            fmt.write_meta("hvsrc_sense_mode", hvsrc_sense_mode)
            fmt.write_meta("hvsrc_route_termination", hvsrc_route_termination)
            fmt.write_meta("hvsrc_filter_enable", format(hvsrc_filter_enable).lower())
            fmt.write_meta("hvsrc_filter_count", format(hvsrc_filter_count))
            fmt.write_meta("hvsrc_filter_type", hvsrc_filter_type)

            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            voltage = hvsrc_proxy.source_voltage_level

            # HV Source reading format: CURR
            hvsrc.resource.write(":FORM:ELEM CURR")
            hvsrc.resource.query("*OPC?")

            t0 = time.time()

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                hvsrc_proxy.source_voltage_level = voltage
                # hvsrc_proxy.assert_success()

                time.sleep(waiting_time)

                td = time.time() - t0
                reading_current = float(hvsrc.resource.query(":READ?").split(',')[0])
                logging.info("HV Source reading: %E A", reading_current)
                self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, reading_current)

                # Environment
                if self.process.get("use_environ"):
                    with self.resources.get("environ") as environ:
                        pc_data = environ.query("GET:PC_DATA ?").split(",")
                    temperature_box = float(pc_data[2])
                    logging.info("temperature box: %s degC", temperature_box)
                    temperature_chuck = float(pc_data[33])
                    logging.info("temperature chuck: %s degC", temperature_chuck)
                    humidity_box = float(pc_data[1])
                    logging.info("humidity box: %s degC", humidity_box)
                else:
                    temperature_box = float('nan')
                    temperature_chuck = float('nan')
                    humidity_box = float('nan')

                # Write reading
                fmt.write_row(dict(
                    timestamp=td,
                    hvsrc_voltage=voltage,
                    hvsrc_current=reading_current,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()

                est.next()
                self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ValueError("compliance tripped")
                # hvsrc_proxy.assert_success()
                if not self.process.running:
                    break

        self.process.emit("progress", 0, 0)

    def finalize(self, hvsrc):
        voltage_step = self.get_parameter('voltage_step')

        hvsrc_proxy = create_proxy(hvsrc)

        voltage = hvsrc_proxy.source_voltage_level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            hvsrc_proxy.source_voltage_level = voltage
            time.sleep(QUICK_RAMP_DELAY)
            # hvsrc_proxy.assert_success()

        hvsrc_proxy.output_enable = False
        hvsrc_proxy.assert_success()

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("hvsrc") as hvsrc_res:
            hvsrc = K2410(hvsrc_res)
            try:
                self.initialize(hvsrc)
                self.measure(hvsrc)
            finally:
                self.finalize(hvsrc)

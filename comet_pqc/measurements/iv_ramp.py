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
        self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('vsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('vsrc_filter_enable', False, type=bool)
        self.register_parameter('vsrc_filter_count', 10, type=int)
        self.register_parameter('vsrc_filter_type', 'repeat', values=('repeat', 'moving'))

    def env_detect_model(self, env):
        try:
            env_idn = env.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access Environment Box", env.resource.resource_name, e)
        logging.info("Detected Environment Box: %s", env_idn)
        # TODO
        self.process.emit("state", dict(
            env_model=env_idn
        ))

    def initialize(self, vsrc):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 5)

        voltage_start = self.get_parameter('voltage_start')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_route_termination = self.get_parameter('vsrc_route_termination')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        vsrc_proxy = create_proxy(vsrc)

        vsrc_idn = vsrc_proxy.identification
        logging.info("Detected V Source: %s", vsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', vsrc_idn, re.IGNORECASE).groups()
        vsrc_model = ''.join(result) or None

        if self.process.get("use_environ"):
            with self.resources.get("environ") as environ:
                self.env_detect_model(environ)

        self.process.emit("state", dict(
            vsrc_model=vsrc_model,
            vsrc_voltage=vsrc_proxy.source_voltage_level,
            vsrc_current=None,
            vsrc_output=vsrc_proxy.output_enable
        ))

        vsrc_proxy.reset()
        vsrc_proxy.assert_success()
        vsrc_proxy.clear()
        vsrc_proxy.assert_success()

        # Beeper off
        vsrc_proxy.beeper_enable = False
        vsrc_proxy.assert_success()
        self.process.emit("progress", 1, 5)

        # Select rear terminal
        logging.info("set route termination: '%s'", vsrc_route_termination)
        if vsrc_route_termination == "front":
            vsrc.resource.write(":ROUT:TERM FRONT")
        elif vsrc_route_termination == "rear":
            vsrc.resource.write(":ROUT:TERM REAR")
        vsrc.resource.query("*OPC?")
        vsrc_proxy.assert_success()
        self.process.emit("progress", 2, 5)

        # set sense mode
        logging.info("set sense mode: '%s'", vsrc_sense_mode)
        if vsrc_sense_mode == "remote":
            vsrc.resource.write(":SYST:RSEN ON")
        elif vsrc_sense_mode == "local":
            vsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {vsrc_sense_mode}")
        vsrc.resource.query("*OPC?")
        vsrc_proxy.assert_success()
        self.process.emit("progress", 3, 5)

        # Compliance
        logging.info("set compliance: %E A", vsrc_current_compliance)
        vsrc.sense.current.protection.level = vsrc_current_compliance
        vsrc_proxy.assert_success()

        # Range
        current_range = 1.05E-6
        vsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        vsrc.resource.query("*OPC?")
        vsrc_proxy.assert_success()
        #vsrc.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #vsrc.resource.query("*OPC?")
        #vsrc_proxy.assert_success()

        # Filter

        vsrc_proxy.filter_count = vsrc_filter_count
        vsrc_proxy.assert_success()
        vsrc_proxy.filter_type = vsrc_filter_type.upper()
        vsrc_proxy.assert_success()
        vsrc_proxy.filter_enable = vsrc_filter_enable
        vsrc_proxy.assert_success()

        self.process.emit("progress", 5, 5)

        # If output enabled
        if vsrc_proxy.output_enable:
            voltage = vsrc_proxy.source_voltage_level

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
            for voltage in comet.Range(voltage, 0, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", f"{voltage:.3f} V")
                vsrc_proxy.source_voltage_level = voltage
                # vsrc_proxy.assert_success()
                time.sleep(.100)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            vsrc_proxy.source_voltage_level = voltage
            vsrc_proxy.assert_success()
            vsrc_proxy.output_enable = True
            vsrc_proxy.assert_success()
            time.sleep(.100)

        self.process.emit("progress", 2, 5)

        if self.process.running:

            voltage = vsrc_proxy.source_voltage_level

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, vsrc.resource.query(":FORM:ELEM?").split(",")))
            vsrc_proxy.assert_success()

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
                vsrc_proxy.source_voltage_level = voltage
                # vsrc_proxy.assert_success()
                time.sleep(.100)
                # Returns <elements> comma separated
                #values = list(map(float, vsrc.resource.query(":READ?").split(",")))
                #data = zip(elements, values)
                time.sleep(waiting_time)
                # Compliance?
                compliance_tripped = vsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 5, 5)

    def measure(self, vsrc):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_route_termination = self.get_parameter('vsrc_route_termination')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        vsrc_proxy = create_proxy(vsrc)

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("vsrc_voltage", "E")
            fmt.add_column("vsrc_current", "E")
            fmt.add_column("temperature_box", "E")
            fmt.add_column("temperature_chuck", "E")
            fmt.add_column("humidity_box", "E")

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
            fmt.write_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
            fmt.write_meta("vsrc_sense_mode", vsrc_sense_mode)
            fmt.write_meta("vsrc_route_termination", vsrc_route_termination)
            fmt.write_meta("vsrc_filter_enable", format(vsrc_filter_enable).lower())
            fmt.write_meta("vsrc_filter_count", format(vsrc_filter_count))
            fmt.write_meta("vsrc_filter_type", vsrc_filter_type)

            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            voltage = vsrc_proxy.source_voltage_level

            # V Source reading format: CURR
            vsrc.resource.write(":FORM:ELEM CURR")
            vsrc.resource.query("*OPC?")

            t0 = time.time()

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                vsrc_proxy.source_voltage_level = voltage
                time.sleep(.100)
                # vsrc_proxy.assert_success()
                td = time.time() - t0
                reading_current = float(vsrc.resource.query(":READ?").split(',')[0])
                logging.info("V Source reading: %E A", reading_current)
                self.process.emit("reading", "vsrc", abs(voltage) if ramp.step < 0 else voltage, reading_current)

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
                    vsrc_voltage=voltage,
                    vsrc_current=reading_current,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.emit("message", "Elapsed {} | Remaining {} | {}".format(elapsed, remaining, format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # Compliance?
                compliance_tripped = vsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                # vsrc_proxy.assert_success()
                if not self.process.running:
                    break

        self.process.emit("progress", 0, 0)

    def finalize(self, vsrc):
        voltage_step = self.get_parameter('voltage_step')

        vsrc_proxy = create_proxy(vsrc)

        voltage = vsrc_proxy.source_voltage_level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            vsrc_proxy.source_voltage_level = voltage
            time.sleep(.100)
            # vsrc_proxy.assert_success()

        vsrc_proxy.output_enable = False
        vsrc_proxy.assert_success()

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            vsrc = K2410(vsrc_res)
            try:
                self.initialize(vsrc)
                self.measure(vsrc)
            finally:
                self.finalize(vsrc)

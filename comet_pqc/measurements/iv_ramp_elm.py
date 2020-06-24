import datetime
import logging
import time
import os
import re

import comet
from comet.driver.keithley import K6517B

from ..driver import K2410
from ..utils import format_metric
from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["IVRampElmMeasurement"]

def check_error(vsrc):
    error = vsrc.system.error
    if error[0]:
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampElmMeasurement(MatrixMeasurement):
    """IV ramp with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_elm"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('voltage_start', unit='V', required=True)
        self.register_parameter('voltage_stop', unit='V', required=True)
        self.register_parameter('voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', 1.0, unit='s')
        self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('vsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('vsrc_filter_enable', False, type=bool)
        self.register_parameter('vsrc_filter_count', 10, type=int)
        self.register_parameter('vsrc_filter_type', 'repeat', values=('repeat', 'moving'))
        self.register_parameter('elm_filter_enable', False, type=bool)
        self.register_parameter('elm_filter_count', 10, type=int)
        self.register_parameter('elm_filter_type', 'repeat')
        self.register_parameter('elm_zero_correction', False, type=bool)
        self.register_parameter('elm_integration_rate', 50, type=int)
        self.register_parameter('elm_current_range', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_enable', True, type=bool)
        self.register_parameter('elm_current_autorange_minimum', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_maximum', comet.ureg('20 mA'), unit='A')

    def env_detect_model(self, env):
        try:
            env_idn = env.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access Environment Box", env.resource_name, e)
        logging.info("Detected Environment Box: %s", env_idn)
        # TODO
        self.process.emit("state", dict(
            env_model=env_idn
        ))

    def initialize(self, vsrc, elm):
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
        elm_filter_enable = self.get_parameter('elm_filter_enable')
        elm_filter_count = self.get_parameter('elm_filter_count')
        elm_filter_type = self.get_parameter('elm_filter_type')
        elm_zero_correction = self.get_parameter('elm_zero_correction')
        elm_integration_rate = self.get_parameter('elm_integration_rate')
        elm_current_range = self.get_parameter('elm_current_range')
        elm_current_autorange_enable = self.get_parameter('elm_current_autorange_enable')
        elm_current_autorange_minimum = self.get_parameter('elm_current_autorange_minimum')
        elm_current_autorange_maximum = self.get_parameter('elm_current_autorange_maximum')

        vsrc_idn = vsrc.identification
        logging.info("Detected V Source: %s", vsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', vsrc_idn, re.IGNORECASE).groups()
        vsrc_model = ''.join(result) or None

        self.process.emit("progress", 1, 5)

        elm_idn = elm.identification
        logging.info("Detected Electrometer: %s", elm_idn)
        result = re.search(r'model\s+([\d\w]+)', elm_idn, re.IGNORECASE).groups()
        elm_model = ''.join(result) or None

        if self.process.get("use_environ"):
            with self.resources.get("environ") as environ:
                self.env_detect_model(environ)

        self.process.emit("progress", 2, 5)

        self.process.emit("state", dict(
            vsrc_model=vsrc_model,
            vsrc_voltage=vsrc.source.voltage.level,
            vsrc_current=None,
            vsrc_output=vsrc.output,
            elm_model=elm_model,
            elm_current=None,
        ))

        # Beeper off
        vsrc.reset()
        vsrc.clear()
        vsrc.system.beeper.status = False
        check_error(vsrc)

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.voltage.level,
            vsrc_current=None,
            vsrc_output=vsrc.output,
            elm_current=None
        ))

        # Select rear terminal
        logging.info("set route termination: '%s'", vsrc_route_termination)
        if vsrc_route_termination == "front":
            vsrc.resource.write(":ROUT:TERM FRONT")
        elif vsrc_route_termination == "rear":
            vsrc.resource.write(":ROUT:TERM REAR")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)

        # set sense mode
        logging.info("set sense mode: '%s'", vsrc_sense_mode)
        if vsrc_sense_mode == "remote":
            vsrc.resource.write(":SYST:RSEN ON")
        elif vsrc_sense_mode == "local":
            vsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {vsrc_sense_mode}")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)

        # Compliance
        logging.info("set compliance: %E A", vsrc_current_compliance)
        vsrc.sense.current.protection.level = vsrc_current_compliance
        check_error(vsrc)

        # Range
        current_range = 1.05E-6
        vsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        vsrc.resource.write(":SENS:VOLT:RANG:AUTO ON")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)
        #vsrc.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #vsrc.resource.query("*OPC?")
        #check_error(vsrc)

        # Filter
        vsrc.resource.write(f":SENS:AVER:COUN {vsrc_filter_count:d}")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)

        if vsrc_filter_type == "repeat":
            vsrc.resource.write(":SENS:AVER:TCON REP")
        elif vsrc_filter_type == "repeat":
            vsrc.resource.write(":SENS:AVER:TCON MOV")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)

        if vsrc_filter_enable:
            vsrc.resource.write(":SENS:AVER:STATE ON")
        else:
            vsrc.resource.write(":SENS:AVER:STATE OFF")
        vsrc.resource.query("*OPC?")
        check_error(vsrc)

        self.process.emit("progress", 1, 5)

        # If output disabled
        voltage = 0
        vsrc.source.voltage.level = voltage
        check_error(vsrc)
        vsrc.output = True
        check_error(vsrc)
        time.sleep(.100)

        self.process.emit("state", dict(
            vsrc_output=vsrc.output
        ))

        self.process.emit("progress", 2, 5)

        if self.process.running:

            voltage = vsrc.source.voltage.level

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", f"{voltage:.3f} V")
                vsrc.source.voltage.level = voltage
                # check_error(vsrc)
                time.sleep(.100)
                time.sleep(waiting_time)

                self.process.emit("state", dict(
                    vsrc_voltage=voltage,
                ))
                # Compliance?
                compliance_tripped = vsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        def elm_safe_write(message):
            """Write, wait for operation complete, test for errors."""
            elm.resource.write(message)
            elm.resource.query("*OPC?")
            code, label = elm.resource.query(":SYST:ERR?").split(",", 1)
            code = int(code)
            label = label.strip("\"")
            if code != 0:
                logging.error(f"error {code}: {label} returned by '{message}'")
                raise RuntimeError(f"error {code}: {label} returned by '{message}'")

        elm_safe_write("*RST")
        elm_safe_write("*CLS")

        # Filter
        elm_safe_write(f":SENS:CURR:AVER:COUN {elm_filter_count:d}")

        if elm_filter_type == "repeat":
            elm_safe_write(":SENS:CURR:AVER:TCON REP")
        elif elm_filter_type == "repeat":
            elm_safe_write(":SENS:CURR:AVER:TCON MOV")

        if elm_filter_enable:
            elm_safe_write(":SENS:CURR:AVER:STATE ON")
        else:
            elm_safe_write(":SENS:CURR:AVER:STATE OFF")

        nplc = elm_integration_rate / 10.
        elm_safe_write(f":SENS:CURR:NPLC {nplc:02f}")

        elm_safe_write(":SYST:ZCH ON") # enable zero check
        assert elm.resource.query(":SYST:ZCH?") == '1', "failed to enable zero check"

        elm_safe_write(":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        elm_safe_write(f":SENS:CURR:RANG {elm_current_range:E}")
        if elm_zero_correction:
            elm_safe_write(":SYST:ZCOR ON") # perform zero correction
        # Auto range
        elm_safe_write(f":SENS:CURR:RANG:AUTO {elm_current_autorange_enable:d}")
        elm_safe_write(f":SENS:CURR:RANG:AUTO:LLIM {elm_current_autorange_minimum:E}")
        elm_safe_write(f":SENS:CURR:RANG:AUTO:ULIM {elm_current_autorange_maximum:E}")

        elm_safe_write(":SYST:ZCH OFF") # disable zero check
        assert elm.resource.query(":SYST:ZCH?") == '0', "failed to disable zero check"

        self.process.emit("progress", 3, 5)

    def measure(self, vsrc, elm):
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
        elm_filter_enable = self.get_parameter('elm_filter_enable')
        elm_filter_count = self.get_parameter('elm_filter_count')
        elm_filter_type = self.get_parameter('elm_filter_type')
        elm_zero_correction = self.get_parameter('elm_zero_correction')
        elm_integration_rate = self.get_parameter('elm_integration_rate')
        elm_current_range = self.get_parameter('elm_current_range')
        elm_current_autorange_enable = self.get_parameter('elm_current_autorange_enable')
        elm_current_autorange_minimum = self.get_parameter('elm_current_autorange_minimum')
        elm_current_autorange_maximum = self.get_parameter('elm_current_autorange_maximum')

        if not self.process.running:
            return

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("current_vsrc", "E")
            fmt.add_column("current_elm", "E")
            fmt.add_column("temperature_box", "E")
            fmt.add_column("temperature_chuck", "E")
            fmt.add_column("humidity_box", "E")

            # Write meta data
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
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
            fmt.write_meta("elm_filter_enable", format(elm_filter_enable).lower())
            fmt.write_meta("elm_filter_count", format(elm_filter_count))
            fmt.write_meta("elm_filter_type", elm_filter_type)
            fmt.write_meta("elm_zero_correction", format(elm_zero_correction))
            fmt.write_meta("elm_integration_rate", format(elm_integration_rate))
            fmt.write_meta("elm_current_range", format(elm_current_range, 'G'))
            fmt.write_meta("elm_current_autorange_enable", format(elm_current_autorange_enable).lower())
            fmt.write_meta("elm_current_autorange_minimum", format(elm_current_autorange_minimum, 'G'))
            fmt.write_meta("elm_current_autorange_maximum", format(elm_current_autorange_maximum, 'G'))
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            voltage = vsrc.source.voltage.level

            # V Source reading format: CURR
            vsrc.resource.write(":FORM:ELEM CURR")
            vsrc.resource.query("*OPC?")

            # Electrometer reading format: READ
            elm.resource.write(":FORM:ELEM READ")
            elm.resource.query("*OPC?")

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                vsrc.clear()
                vsrc.source.voltage.level = voltage
                time.sleep(.100)
                # check_error(vsrc)
                dt = time.time() - t0

                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.emit("message", "Elapsed {} | Remaining {} | {}".format(elapsed, remaining, format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read V Source
                vsrc_reading = float(vsrc.resource.query(":READ?").split(',')[0])
                logging.info("V Source reading: %E", vsrc_reading)
                self.process.emit("reading", "vsrc", abs(voltage) if ramp.step < 0 else voltage, vsrc_reading)

                # read ELM
                elm_reading = float(elm.resource.query(":READ?").split(',')[0])
                logging.info("ELM reading: %E", elm_reading)
                self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                self.process.emit("update")
                self.process.emit("state", dict(
                    vsrc_voltage=voltage,
                    vsrc_current=vsrc_reading,
                    elm_current=elm_reading
                ))

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

                self.process.emit("state", dict(
                    env_chuck_temperature=temperature_chuck,
                    env_box_temperature=temperature_box,
                    env_box_humidity=humidity_box
                ))

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    voltage=voltage,
                    current_vsrc=vsrc_reading,
                    current_elm=elm_reading,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                # Compliance?
                compliance_tripped = vsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                # check_error(vsrc)
                if not self.process.running:
                    break

        self.process.emit("progress", 4, 5)

    def finalize(self, vsrc, elm):
        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        self.process.emit("state", dict(
            vsrc_current=None,
            elm_current=None
        ))

        voltage_step = self.get_parameter('voltage_step')
        voltage = vsrc.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            vsrc.source.voltage.level = voltage
            time.sleep(.100)
            # check_error(vsrc)
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))

        vsrc.output = False
        check_error(vsrc)

        self.process.emit("state", dict(
            vsrc_output=vsrc.output,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            with self.resources.get("elm") as elm_res:
                vsrc = K2410(vsrc_res)
                elm = K6517B(elm_res)
                try:
                    self.initialize(vsrc, elm)
                    self.measure(vsrc, elm)
                finally:
                    self.finalize(vsrc, elm)

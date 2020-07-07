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
from ..benchmark import Benchmark
from .matrix import MatrixMeasurement

__all__ = ["IVRampElmMeasurement"]

def check_error(hvsrc):
    error = hvsrc.system.error
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
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('hvsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('hvsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('hvsrc_filter_enable', False, type=bool)
        self.register_parameter('hvsrc_filter_count', 10, type=int)
        self.register_parameter('hvsrc_filter_type', 'repeat', values=('repeat', 'moving'))
        self.register_parameter('elm_filter_enable', False, type=bool)
        self.register_parameter('elm_filter_count', 10, type=int)
        self.register_parameter('elm_filter_type', 'repeat')
        self.register_parameter('elm_zero_correction', False, type=bool)
        self.register_parameter('elm_integration_rate', 50, type=int)
        self.register_parameter('elm_current_range', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_enable', False, type=bool)
        self.register_parameter('elm_current_autorange_minimum', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_maximum', comet.ureg('20 mA'), unit='A')

    def initialize(self, hvsrc, elm):
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
        elm_filter_enable = self.get_parameter('elm_filter_enable')
        elm_filter_count = self.get_parameter('elm_filter_count')
        elm_filter_type = self.get_parameter('elm_filter_type')
        elm_zero_correction = self.get_parameter('elm_zero_correction')
        elm_integration_rate = self.get_parameter('elm_integration_rate')
        elm_current_range = self.get_parameter('elm_current_range')
        elm_current_autorange_enable = self.get_parameter('elm_current_autorange_enable')
        elm_current_autorange_minimum = self.get_parameter('elm_current_autorange_minimum')
        elm_current_autorange_maximum = self.get_parameter('elm_current_autorange_maximum')

        self.process.emit("progress", 2, 5)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.voltage.level,
            hvsrc_current=None,
            hvsrc_output=hvsrc.output,
            elm_current=None,
        ))

        # Beeper off
        hvsrc.reset()
        hvsrc.clear()
        hvsrc.system.beeper.status = False
        check_error(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.voltage.level,
            hvsrc_current=None,
            hvsrc_output=hvsrc.output,
            elm_current=None
        ))

        # Select rear terminal
        logging.info("set route termination: '%s'", hvsrc_route_termination)
        if hvsrc_route_termination == "front":
            hvsrc.resource.write(":ROUT:TERM FRONT")
        elif hvsrc_route_termination == "rear":
            hvsrc.resource.write(":ROUT:TERM REAR")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)

        # set sense mode
        logging.info("set sense mode: '%s'", hvsrc_sense_mode)
        if hvsrc_sense_mode == "remote":
            hvsrc.resource.write(":SYST:RSEN ON")
        elif hvsrc_sense_mode == "local":
            hvsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {hvsrc_sense_mode}")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)

        # Compliance
        logging.info("set compliance: %E A", hvsrc_current_compliance)
        hvsrc.sense.current.protection.level = hvsrc_current_compliance
        check_error(hvsrc)

        # Range
        current_range = 1.05E-6
        hvsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        hvsrc.resource.write(":SENS:VOLT:RANG:AUTO ON")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)
        #hvsrc.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #hvsrc.resource.query("*OPC?")
        #check_error(hvsrc)

        # Filter
        hvsrc.resource.write(f":SENS:AVER:COUN {hvsrc_filter_count:d}")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)

        if hvsrc_filter_type == "repeat":
            hvsrc.resource.write(":SENS:AVER:TCON REP")
        elif hvsrc_filter_type == "repeat":
            hvsrc.resource.write(":SENS:AVER:TCON MOV")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)

        if hvsrc_filter_enable:
            hvsrc.resource.write(":SENS:AVER:STATE ON")
        else:
            hvsrc.resource.write(":SENS:AVER:STATE OFF")
        hvsrc.resource.query("*OPC?")
        check_error(hvsrc)

        self.process.emit("progress", 1, 5)

        # If output disabled
        voltage = 0
        hvsrc.source.voltage.level = voltage
        check_error(hvsrc)
        hvsrc.output = True
        check_error(hvsrc)
        time.sleep(.100)

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output
        ))

        self.process.emit("progress", 2, 5)

        if self.process.running:

            voltage = hvsrc.source.voltage.level

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", f"{voltage:.3f} V")
                hvsrc.source.voltage.level = voltage
                # check_error(hvsrc)
                time.sleep(.100)
                time.sleep(waiting_time)

                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                ))
                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
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

    def measure(self, hvsrc, elm):
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
            fmt.add_column("timestamp", ".3f", unit="s")
            fmt.add_column("voltage", "E", unit="V")
            fmt.add_column("current_hvsrc", "E", unit="A")
            fmt.add_column("current_elm", "E", unit="A")
            fmt.add_column("temperature_box", "E", unit="degC")
            fmt.add_column("temperature_chuck", "E", unit="degC")
            fmt.add_column("humidity_box", "E", unit="%")

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
            fmt.write_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
            fmt.write_meta("hvsrc_sense_mode", hvsrc_sense_mode)
            fmt.write_meta("hvsrc_route_termination", hvsrc_route_termination)
            fmt.write_meta("hvsrc_filter_enable", format(hvsrc_filter_enable).lower())
            fmt.write_meta("hvsrc_filter_count", format(hvsrc_filter_count))
            fmt.write_meta("hvsrc_filter_type", hvsrc_filter_type)
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

            voltage = hvsrc.source.voltage.level

            # HV Source reading format: CURR
            hvsrc.resource.write(":FORM:ELEM CURR")
            hvsrc.resource.query("*OPC?")

            # Electrometer reading format: READ
            elm.resource.write(":FORM:ELEM READ")
            elm.resource.query("*OPC?")

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            benchmark_step = Benchmark("Single_Step")
            benchmark_elm = Benchmark("Read_ELM")
            benchmark_hvsrc = Benchmark("Read_HV_Source")
            benchmark_environ = Benchmark("Read_Environment")

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                with benchmark_step:
                    logging.info("set voltage: %E V", voltage)
                    hvsrc.clear()
                    hvsrc.source.voltage.level = voltage
                    time.sleep(.100)
                    # check_error(hvsrc)
                    dt = time.time() - t0

                    est.next()
                    elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                    remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                    self.process.emit("message", "Elapsed {} | Remaining {} | {}".format(elapsed, remaining, format_metric(voltage, "V")))
                    self.process.emit("progress", *est.progress)

                    # read HV Source
                    with benchmark_hvsrc:
                        hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                    logging.info("HV Source reading: %E", hvsrc_reading)
                    self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, hvsrc_reading)

                    # read ELM
                    with benchmark_elm:
                        elm_reading = float(elm.resource.query(":READ?").split(',')[0])
                    logging.info("ELM reading: %E", elm_reading)
                    self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                    self.process.emit("update")
                    self.process.emit("state", dict(
                        hvsrc_voltage=voltage,
                        hvsrc_current=hvsrc_reading,
                        elm_current=elm_reading
                    ))

                    # Environment
                    if self.process.get("use_environ"):
                        with benchmark_environ:
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
                        current_hvsrc=hvsrc_reading,
                        current_elm=elm_reading,
                        temperature_box=temperature_box,
                        temperature_chuck=temperature_chuck,
                        humidity_box=humidity_box
                    ))
                    fmt.flush()
                    time.sleep(waiting_time)

                    # Compliance?
                    compliance_tripped = hvsrc.sense.current.protection.tripped
                    if compliance_tripped:
                        logging.error("HV Source in compliance")
                        raise ValueError("compliance tripped")
                    # check_error(hvsrc)
                    if not self.process.running:
                        break

            logging.info(benchmark_step)
            logging.info(benchmark_elm)
            logging.info(benchmark_hvsrc)
            logging.info(benchmark_environ)

        self.process.emit("progress", 4, 5)

    def finalize(self, hvsrc, elm):
        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        self.process.emit("state", dict(
            hvsrc_current=None,
            elm_current=None
        ))

        voltage_step = self.get_parameter('voltage_step')
        voltage = hvsrc.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            hvsrc.source.voltage.level = voltage
            time.sleep(.100)
            # check_error(hvsrc)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))

        hvsrc.output = False
        check_error(hvsrc)

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("hvsrc") as hvsrc_res:
            with self.resources.get("elm") as elm_res:
                hvsrc = K2410(hvsrc_res)
                elm = K6517B(elm_res)
                try:
                    self.initialize(hvsrc, elm)
                    self.measure(hvsrc, elm)
                finally:
                    self.finalize(hvsrc, elm)

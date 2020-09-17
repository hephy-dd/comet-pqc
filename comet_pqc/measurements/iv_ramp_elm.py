import datetime
import logging
import time
import os
import re

import comet
from comet.driver.keithley import K6517B
from comet.driver.keithley import K2410

from ..utils import format_metric
from ..estimate import Estimate
from ..formatter import PQCFormatter
from ..benchmark import Benchmark
from .matrix import MatrixMeasurement
from .measurement import ComplianceError
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY
from .mixins import ElectrometerMixin
from .mixins import EnvironmentMixin

__all__ = ["IVRampElmMeasurement"]

def check_error(hvsrc):
    error = hvsrc.system.error
    if error[0]:
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampElmMeasurement(MatrixMeasurement, ElectrometerMixin, EnvironmentMixin):
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
        self.register_elm()
        self.register_environment()

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
        elif hvsrc_filter_type == "moving":
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
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                ))

                time.sleep(QUICK_RAMP_DELAY)

                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("compliance tripped")
                if not self.process.running:
                    break

        self.elm_safe_write(elm, "*RST")
        self.elm_safe_write(elm, "*CLS")

        # Filter
        self.elm_safe_write(elm, f":SENS:CURR:AVER:COUN {elm_filter_count:d}")

        if elm_filter_type == "repeat":
            self.elm_safe_write(elm, ":SENS:CURR:AVER:TCON REP")
        elif elm_filter_type == "repeat":
            self.elm_safe_write(elm, ":SENS:CURR:AVER:TCON MOV")

        if elm_filter_enable:
            self.elm_safe_write(elm, ":SENS:CURR:AVER:STATE ON")
        else:
            self.elm_safe_write(elm, ":SENS:CURR:AVER:STATE OFF")

        nplc = elm_integration_rate / 10.
        self.elm_safe_write(elm, f":SENS:CURR:NPLC {nplc:02f}")

        self.elm_safe_write(elm, ":SYST:ZCH ON") # enable zero check
        assert elm.resource.query(":SYST:ZCH?") == '1', "failed to enable zero check"

        self.elm_safe_write(elm, ":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        self.elm_safe_write(elm, f":SENS:CURR:RANG {elm_current_range:E}")
        if elm_zero_correction:
            self.elm_safe_write(elm, ":SYST:ZCOR ON") # perform zero correction
        # Auto range
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO {elm_current_autorange_enable:d}")
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO:LLIM {elm_current_autorange_minimum:E}")
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO:ULIM {elm_current_autorange_maximum:E}")

        self.elm_safe_write(elm, ":SYST:ZCH OFF") # disable zero check
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
        elm_read_timeout = self.get_parameter('elm_read_timeout')

        if not self.process.running:
            return

        # Extend meta data
        self.set_meta("voltage_start", f"{voltage_start:G} V")
        self.set_meta("voltage_stop", f"{voltage_stop:G} V")
        self.set_meta("voltage_step", f"{voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.set_meta("hvsrc_sense_mode", hvsrc_sense_mode)
        self.set_meta("hvsrc_route_termination", hvsrc_route_termination)
        self.set_meta("hvsrc_filter_enable", format(hvsrc_filter_enable).lower())
        self.set_meta("hvsrc_filter_count", format(hvsrc_filter_count))
        self.set_meta("hvsrc_filter_type", hvsrc_filter_type)
        self.set_meta("elm_filter_enable", format(elm_filter_enable).lower())
        self.set_meta("elm_filter_count", format(elm_filter_count))
        self.set_meta("elm_filter_type", elm_filter_type)
        self.set_meta("elm_zero_correction", format(elm_zero_correction))
        self.set_meta("elm_integration_rate", format(elm_integration_rate))
        self.set_meta("elm_current_range", format(elm_current_range, 'G'))
        self.set_meta("elm_current_autorange_enable", format(elm_current_autorange_enable).lower())
        self.set_meta("elm_current_autorange_minimum", format(elm_current_autorange_minimum, 'G'))
        self.set_meta("elm_current_autorange_maximum", format(elm_current_autorange_maximum, 'G'))
        self.set_meta("elm_read_timeout", format(elm_read_timeout, 'G'))

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage", "V")
        self.set_series_unit("current_hvsrc", "A")
        self.set_series_unit("current_elm", "A")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage")
        self.register_series("current_hvsrc")
        self.register_series("current_elm")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        voltage = hvsrc.source.voltage.level

        # HV Source reading format: CURR
        hvsrc.resource.write(":FORM:ELEM CURR")
        hvsrc.resource.query("*OPC?")

        # Electrometer reading format: READ
        elm.resource.write(":FORM:ELEM READ")
        elm.resource.query("*OPC?")
        self.elm_check_error(elm)

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
                # check_error(hvsrc)

                time.sleep(waiting_time)

                dt = time.time() - t0

                est.next()
                self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read ELM
                with benchmark_elm:
                    elm_reading = self.elm_read(elm, timeout=elm_read_timeout)
                self.elm_check_error(elm)
                logging.info("ELM reading: %E", elm_reading)
                self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                # read HV Source
                with benchmark_hvsrc:
                    hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                logging.info("HV Source reading: %E", hvsrc_reading)
                self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, hvsrc_reading)

                self.process.emit("update")
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                    hvsrc_current=hvsrc_reading,
                    elm_current=elm_reading
                ))

                self.environment_update()

                self.process.emit("state", dict(
                    env_chuck_temperature=self.environment_temperature_chuck,
                    env_box_temperature=self.environment_temperature_box,
                    env_box_humidity=self.environment_humidity_box
                ))

                # Append series data
                self.append_series(
                    timestamp=dt,
                    voltage=voltage,
                    current_hvsrc=hvsrc_reading,
                    current_elm=elm_reading,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                )

                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("compliance tripped")
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
            # check_error(hvsrc)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        hvsrc.output = False
        check_error(hvsrc)

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 5, 5)

    def run(self):
        with self.resources.get("hvsrc") as hvsrc_res:
            with self.resources.get("elm") as elm_res:
                super().run(
                    hvsrc=K2410(hvsrc_res),
                    elm=K6517B(elm_res)
                )

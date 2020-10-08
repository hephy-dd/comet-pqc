import contextlib
import datetime
import logging
import time
import os
import re

import comet
from comet.driver.keithley import K6517B
from comet.driver.keithley import K2410
from comet.driver.keithley import K2657A

from ..utils import format_metric
from ..estimate import Estimate
from ..formatter import PQCFormatter
from ..benchmark import Benchmark

from .matrix import MatrixMeasurement
from .measurement import ComplianceError
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

from .mixins import HVSourceMixin
from .mixins import VSourceMixin
from .mixins import ElectrometerMixin
from .mixins import EnvironmentMixin

__all__ = ["IVRampBiasElmMeasurement"]

def check_error(vsrc):
    if vsrc.errorqueue.count:
        error = vsrc.errorqueue.next()
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampBiasElmMeasurement(MatrixMeasurement, HVSourceMixin, VSourceMixin, ElectrometerMixin, EnvironmentMixin):
    """Bias IV ramp measurement."""

    type = "iv_ramp_bias_elm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter('voltage_start', unit='V', required=True)
        self.register_parameter('voltage_stop', unit='V', required=True)
        self.register_parameter('voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('bias_voltage', unit='V', required=True)
        self.register_parameter('bias_mode', 'constant', values=('constant', 'offset'))
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_parameter('elm_filter_enable', False, type=bool)
        self.register_parameter('elm_filter_count', 10, type=int)
        self.register_parameter('elm_filter_type', 'repeat')
        self.register_parameter('elm_zero_correction', False, type=bool)
        self.register_parameter('elm_integration_rate', 50, type=int)
        self.register_parameter('elm_current_range', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_enable', False, type=bool)
        self.register_parameter('elm_current_autorange_minimum', comet.ureg('20 pA'), unit='A')
        self.register_parameter('elm_current_autorange_maximum', comet.ureg('20 mA'), unit='A')
        self.register_hvsource()
        self.register_vsource()
        self.register_elm()
        self.register_environment()

    def initialize(self, hvsrc, vsrc, elm):
        self.process.emit("progress", 1, 5)
        self.process.emit("message", "Ramp to start...")

        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
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
        elm_read_timeout = self.get_parameter('elm_read_timeout')

        # Extend meta data
        self.set_meta("voltage_start", f"{voltage_start:G} V")
        self.set_meta("voltage_stop", f"{voltage_stop:G} V")
        self.set_meta("voltage_step", f"{voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("bias_voltage", f"{bias_voltage:G} V")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.hvsrc_update_meta()
        self.set_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
        self.vsrc_update_meta()
        self.set_meta("elm_filter_enable", elm_filter_enable)
        self.set_meta("elm_filter_count", elm_filter_count)
        self.set_meta("elm_filter_type", elm_filter_type)
        self.set_meta("elm_zero_correction", elm_zero_correction)
        self.set_meta("elm_integration_rate", elm_integration_rate)
        self.set_meta("elm_current_range", format(elm_current_range, 'G'))
        self.set_meta("elm_current_autorange_enable", elm_current_autorange_enable)
        self.set_meta("elm_current_autorange_minimum", format(elm_current_autorange_minimum, 'G'))
        self.set_meta("elm_current_autorange_maximum", format(elm_current_autorange_maximum, 'G'))
        self.set_meta("elm_read_timeout", format(elm_read_timeout, 'G'))
        self.elm_update_meta()
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage", "V")
        self.set_series_unit("current_elm", "A")
        self.set_series_unit("current_vsrc", "A")
        self.set_series_unit("current_hvsrc", "A")
        self.set_series_unit("bias_voltage", "V")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage")
        self.register_series("current_elm")
        self.register_series("current_vsrc")
        self.register_series("current_hvsrc")
        self.register_series("bias_voltage")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        # Initialize HV Source

        self.hvsrc_reset(hvsrc)
        self.hvsrc_setup(hvsrc)
        self.hvsrc_set_compliance(hvsrc, hvsrc_current_compliance)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.voltage.level,
            hvsrc_current=None,
            hvsrc_output=hvsrc.output
        ))

        if not self.process.running:
            return

        # Initialize V Source

        self.vsrc_reset(vsrc)
        self.vsrc_setup(vsrc)

        # Current source
        vsrc.source.func = 'DCVOLTS'
        check_error(vsrc)

        self.vsrc_set_current_compliance(vsrc, vsrc_current_compliance)

        if not self.process.running:
            return

        # Initialize Electrometer

        self.elm_safe_write(elm, "*RST")
        self.elm_safe_write(elm, "*CLS")

        # Filter
        self.elm_safe_write(elm, f":SENS:CURR:AVER:COUN {elm_filter_count:d}")

        if elm_filter_type == "repeat":
            self.elm_safe_write(elm, ":SENS:CURR:AVER:TCON REP")
        elif elm_filter_type == "moving":
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

        # Output enable

        hvsrc.output = True
        time.sleep(.100)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output
        ))
        vsrc.source.output = 'ON'
        time.sleep(.100)
        self.process.emit("state", dict(
            vsrc_output=vsrc.source.output
        ))

        # Ramp HV Spource to bias voltage
        voltage = vsrc.source.levelv

        logging.info("ramp to bias voltage: from %E V to %E V with step %E V", voltage, bias_voltage, 1.0)
        for voltage in comet.Range(voltage, bias_voltage, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp to bias... {}".format(format_metric(voltage, "V")))
            vsrc.source.levelv = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

            # Compliance?
            compliance_tripped = vsrc.source.compliance
            if compliance_tripped:
                logging.error("V Source in compliance")
                raise ComplianceError("V Source compliance tripped")

            if not self.process.running:
                break

        # Ramp HV Source to start voltage
        voltage = hvsrc.source.voltage.level

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, 1.0)
        for voltage in comet.Range(voltage, voltage_start, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            hvsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            # check_error(hvsrc)
            time.sleep(QUICK_RAMP_DELAY)

            # Compliance?
            compliance_tripped = hvsrc.sense.current.protection.tripped
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ComplianceError("HV Source compliance tripped")

            if not self.process.running:
                break

        self.process.emit("progress", 5, 5)

    def measure(self, hvsrc, vsrc, elm):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to...")

        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')
        elm_read_timeout = self.get_parameter('elm_read_timeout')

        if not self.process.running:
            return

        # HV Source reading format: CURR
        hvsrc.resource.write(":FORM:ELEM CURR")
        hvsrc.resource.query("*OPC?")


        # Electrometer reading format: READ
        elm.resource.write(":FORM:ELEM READ")
        elm.resource.query("*OPC?")
        self.elm_check_error(elm)

        voltage = hvsrc.source.voltage.level

        ramp = comet.Range(voltage, voltage_stop, voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        benchmark_step = Benchmark("Single_Step")
        benchmark_elm = Benchmark("Read_ELM")
        benchmark_hvsrc = Benchmark("Read_HV_Source")
        benchmark_vsrc = Benchmark("Read_V_Source")
        benchmark_environ = Benchmark("Read_Environment")

        logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                logging.info("set voltage: %E V", voltage)
                hvsrc.source.voltage.level = voltage
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                ))
                # Move bias TODO
                if bias_mode == "offset":
                    bias_voltage += abs(ramp.step) if ramp.begin <= ramp.end else -abs(ramp.step)
                    logging.info("set bias voltage: %E V", bias_voltage)
                    vsrc.source.levelv = bias_voltage
                    self.process.emit("state", dict(
                        vsrc_voltage=bias_voltage,
                    ))

                time.sleep(waiting_time)

                dt = time.time() - t0

                est.next()
                self.process.emit("message", "{} | HV Source {} | Bias {}".format(format_estimate(est), format_metric(voltage, "V"), format_metric(bias_voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read ELM
                with benchmark_elm:
                    elm_reading = self.elm_read(elm, timeout=elm_read_timeout)
                self.elm_check_error(elm)
                logging.info("ELM reading: %E", elm_reading)
                self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                # read V Source
                with benchmark_vsrc:
                    vsrc_reading = vsrc.measure.i()
                logging.info("V Source reading: %E A", vsrc_reading)

                # read HV Source
                with benchmark_hvsrc:
                    hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                logging.info("HV Source bias reading: %E A", hvsrc_reading)

                self.process.emit("update")
                self.process.emit("state", dict(
                    elm_current=elm_reading,
                    hvsrc_current=hvsrc_reading,
                    vsrc_current=vsrc_reading,
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
                    current_elm=elm_reading,
                    current_vsrc=vsrc_reading,
                    current_hvsrc=hvsrc_reading,
                    bias_voltage=bias_voltage,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                )

                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("HV Source compliance tripped")
                compliance_tripped = vsrc.source.compliance
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ComplianceError("V Source compliance tripped")
                if not self.process.running:
                    break

        logging.info(benchmark_step)
        logging.info(benchmark_elm)
        logging.info(benchmark_hvsrc)
        logging.info(benchmark_vsrc)
        logging.info(benchmark_environ)

        self.process.emit("progress", 2, 2)

    def finalize(self, hvsrc, vsrc, elm):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to zero...")

        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        self.process.emit("state", dict(
            elm_current=None,
            vsrc_current=None,
            hvsrc_current=None
        ))

        voltage_step = self.get_parameter('voltage_step')

        voltage = hvsrc.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, 1.0)
        for voltage in comet.Range(voltage, 0, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            hvsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        bias_voltage = vsrc.source.levelv

        logging.info("ramp bias to zero: from %E V to %E V with step %E V", bias_voltage, 0, 1.0)
        for voltage in comet.Range(bias_voltage, 0, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp bias to zero... {}".format(format_metric(voltage, "V")))
            vsrc.source.levelv = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        hvsrc.output = False
        vsrc.source.output = 'OFF'

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output,
            hvsrc_voltage=None,
            hvsrc_current=None,
            vsrc_output=vsrc.source.output,
            vsrc_voltage=None,
            vsrc_current=None,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=K2410(es.enter_context(self.resources.get("hvsrc"))),
                vsrc=K2657A(es.enter_context(self.resources.get("vsrc"))),
                elm=K6517B(es.enter_context(self.resources.get("elm")))
            )

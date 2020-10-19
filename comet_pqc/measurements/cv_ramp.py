import contextlib
import logging
import datetime
import time
import os
import re

import comet
# from comet.driver.keysight import E4980A
from comet.driver.keithley import K2410
from ..driver import E4980A

from ..utils import format_metric
from ..formatter import PQCFormatter
from ..estimate import Estimate
from ..benchmark import Benchmark

from .matrix import MatrixMeasurement
from .measurement import ComplianceError
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

from .mixins import HVSourceMixin
from .mixins import LCRMixin
from .mixins import EnvironmentMixin

__all__ = ["CVRampMeasurement"]

class CVRampMeasurement(MatrixMeasurement, HVSourceMixin, LCRMixin, EnvironmentMixin):
    """CV ramp measurement."""

    type = "cv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter('bias_voltage_start', unit='V', required=True)
        self.register_parameter('bias_voltage_stop', unit='V', required=True)
        self.register_parameter('bias_voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_hvsource()
        self.register_lcr()
        self.register_environment()

    def quick_ramp_zero(self, hvsrc):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)

        bias_voltage_step = self.get_parameter('bias_voltage_step')

        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state
        ))
        if hvsrc_output_state:
            hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)
            ramp = comet.Range(hvsrc_voltage_level, 0, bias_voltage_step)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, ramp.count)
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage
                ))
                time.sleep(QUICK_RAMP_DELAY)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state
        ))
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def initialize(self, hvsrc, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 1, 6)

        # Parameters
        bias_voltage_start = self.get_parameter('bias_voltage_start')
        bias_voltage_step = self.get_parameter('bias_voltage_step')
        bias_voltage_stop = self.get_parameter('bias_voltage_stop')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')

        # Extend meta data
        self.set_meta("bias_voltage_start", f"{bias_voltage_start:G} V")
        self.set_meta("bias_voltage_stop", f"{bias_voltage_stop:G} V")
        self.set_meta("bias_voltage_step", f"{bias_voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.hvsrc_update_meta()
        self.lcr_update_meta()
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage_hvsrc", "V")
        self.set_series_unit("current_hvsrc", "A")
        self.set_series_unit("capacitance", "F")
        self.set_series_unit("capacitance2", "1")
        self.set_series_unit("resistance", "Ohm")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage_hvsrc")
        self.register_series("current_hvsrc")
        self.register_series("capacitance")
        self.register_series("capacitance2")
        self.register_series("resistance")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        # Initialize HV Source

        self.hvsrc_reset(hvsrc)
        self.process.emit("progress", 3, 6)

        self.hvsrc_setup(hvsrc)
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        self.hvsrc_set_compliance(hvsrc, hvsrc_current_compliance)
        self.process.emit("progress", 4, 6)

        self.hvsrc_set_output_state(hvsrc, True)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state,
        ))

        # Initialize LCR

        self.lcr_reset(lcr)
        self.process.emit("progress", 5, 6)

        self.lcr_setup(lcr)
        self.process.emit("progress", 6, 6)

    def measure(self, hvsrc, lcr):
        # Parameters
        bias_voltage_start = self.get_parameter('bias_voltage_start')
        bias_voltage_step = self.get_parameter('bias_voltage_step')
        bias_voltage_stop = self.get_parameter('bias_voltage_stop')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        lcr_soft_filter = self.get_parameter('lcr_soft_filter')

        # Ramp to start voltage

        hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, bias_voltage_start, bias_voltage_step)
        for voltage in comet.Range(hvsrc_voltage_level, bias_voltage_start, bias_voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            time.sleep(QUICK_RAMP_DELAY)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            # Compliance?
            compliance_tripped = self.hvsrc_compliance_tripped(hvsrc)
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ComplianceError("compliance tripped!")

            if not self.process.running:
                break

        if not self.process.running:
            return

        hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

        ramp = comet.Range(hvsrc_voltage_level, bias_voltage_stop, bias_voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        self.hvsrc_safe_write(hvsrc, "*CLS")
        # HV Source reading format: CURR
        self.hvsrc_safe_write(hvsrc, ":FORM:ELEM CURR")

        benchmark_step = Benchmark("Single_Step")
        benchmark_lcr = Benchmark("Read_LCR")
        benchmark_hvsrc = Benchmark("Read_HV_Source")
        benchmark_environ = Benchmark("Read_Environment")

        logging.info("ramp to end voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                self.hvsrc_set_voltage_level(hvsrc, voltage)

                # Delay
                time.sleep(waiting_time)

                # hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)
                dt = time.time() - t0
                est.next()
                self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read LCR, for CpRp -> prim: Cp, sec: Rp
                with benchmark_lcr:
                    try:
                        if lcr_soft_filter:
                            lcr_prim, lcr_sec = self.lcr_acquire_filter_reading(lcr)
                        else:
                            lcr_prim, lcr_sec = self.lcr_acquire_reading(lcr)
                    except Exception as e:
                        raise RuntimeError(f"Failed to read from LCR: {e}")
                    try:
                        lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                    except ZeroDivisionError:
                        lcr_prim2 = 0.0

                # read HV Source
                with benchmark_hvsrc:
                    hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                logging.info("HV Source reading: %E", hvsrc_reading)

                self.process.emit("reading", "lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                self.process.emit("reading", "lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

                self.process.emit("update", )
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                    hvsrc_current=hvsrc_reading
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
                    voltage_hvsrc=voltage,
                    current_hvsrc=hvsrc_reading,
                    capacitance=lcr_prim,
                    capacitance2=lcr_prim2,
                    resistance=lcr_sec,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                )

                # Compliance?
                compliance_tripped = self.hvsrc_compliance_tripped(hvsrc)
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("compliance tripped!")

                if not self.process.running:
                    break

        logging.info(benchmark_step)
        logging.info(benchmark_lcr)
        logging.info(benchmark_hvsrc)
        logging.info(benchmark_environ)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 1, 2)
        self.process.emit("state", dict(
            hvsrc_current=None,
        ))

        self.quick_ramp_zero(hvsrc)
        self.hvsrc_set_output_state(hvsrc, False)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state,
        ))

        self.process.emit("state", dict(
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=K2410(es.enter_context(self.resources.get("hvsrc"))),
                lcr=E4980A(es.enter_context(self.resources.get("lcr")))
            )

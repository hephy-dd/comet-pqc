import logging
import random
import datetime
import time
import os

import comet
# from comet.driver.keysight import E4980A
from ..driver import E4980A

from ..utils import format_metric
from ..estimate import Estimate
from ..benchmark import Benchmark

from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

from .mixins import LCRMixin
from .mixins import EnvironmentMixin

__all__ = ["CVRampAltMeasurement"]

class CVRampAltMeasurement(MatrixMeasurement, LCRMixin, EnvironmentMixin):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter('bias_voltage_start', unit='V', required=True)
        self.register_parameter('bias_voltage_stop', unit='V', required=True)
        self.register_parameter('bias_voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_lcr()
        self.register_environment()

    def quick_ramp_zero(self, lcr):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)

        bias_voltage_step = self.get_parameter('bias_voltage_step')

        lcr_output=self.lcr_get_bias_state(lcr)
        self.process.emit("state", dict(
            lcr_output=lcr_output
        ))
        if lcr_output:
            lcr_voltage_level = self.lcr_get_bias_voltage_level(lcr)
            ramp = comet.Range(lcr_voltage_level, 0, bias_voltage_step)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, ramp.count)
                self.lcr_set_bias_voltage_level(lcr, voltage)
                self.process.emit("state", dict(
                    lcr_voltage=voltage
                ))
                time.sleep(QUICK_RAMP_DELAY)
        self.process.emit("state", dict(
            lcr_output=self.lcr_get_bias_state(lcr)
        ))
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def initialize(self, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 1, 6)

        # Parameters
        bias_voltage_start = self.get_parameter('bias_voltage_start')
        bias_voltage_step = self.get_parameter('bias_voltage_step')
        bias_voltage_stop = self.get_parameter('bias_voltage_stop')
        waiting_time = self.get_parameter('waiting_time')

        # Extend meta data
        self.set_meta("bias_voltage_start", f"{bias_voltage_start:G} V")
        self.set_meta("bias_voltage_stop", f"{bias_voltage_stop:G} V")
        self.set_meta("bias_voltage_step", f"{bias_voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.lcr_update_meta()
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage_lcr", "V")
        self.set_series_unit("current_lcr", "A")
        self.set_series_unit("capacitance", "F")
        self.set_series_unit("capacitance2", "1")
        self.set_series_unit("resistance", "Ohm")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage_lcr")
        self.register_series("current_lcr")
        self.register_series("capacitance")
        self.register_series("capacitance2")
        self.register_series("resistance")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        # Initialize LCR

        self.quick_ramp_zero(lcr)
        self.lcr_reset(lcr)
        self.process.emit("progress", 5, 6)

        self.lcr_setup(lcr)
        self.process.emit("progress", 6, 6)

        self.lcr_set_bias_voltage_level(lcr, 0)
        self.lcr_set_bias_state(lcr, True)
        self.process.emit("state", dict(
            lcr_voltage=self.lcr_get_bias_voltage_level(lcr),
            lcr_output=self.lcr_get_bias_state(lcr),
        ))

    def measure(self, lcr):
        # Parameters
        bias_voltage_start = self.get_parameter('bias_voltage_start')
        bias_voltage_step = self.get_parameter('bias_voltage_step')
        bias_voltage_stop = self.get_parameter('bias_voltage_stop')
        waiting_time = self.get_parameter('waiting_time')
        lcr_soft_filter = self.get_parameter('lcr_soft_filter')

        # Ramp to start voltage

        lcr_voltage_level = self.lcr_get_bias_voltage_level(lcr)

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", lcr_voltage_level, bias_voltage_start, bias_voltage_step)
        for voltage in comet.Range(lcr_voltage_level, bias_voltage_start, bias_voltage_step):
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.lcr_set_bias_voltage_level(lcr, voltage)
            time.sleep(QUICK_RAMP_DELAY)
            self.process.emit("state", dict(
                lcr_voltage=voltage,
            ))
            # Compliance?

            if not self.process.running:
                break

        if not self.process.running:
            return


        lcr_voltage_level = self.lcr_get_bias_voltage_level(lcr)

        ramp = comet.Range(lcr_voltage_level, bias_voltage_stop, bias_voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        lcr.clear()

        benchmark_step = Benchmark("Single_Step")
        benchmark_lcr = Benchmark("Read_LCR")
        benchmark_lcr_source = Benchmark("Read_LCR_Source")
        benchmark_environ = Benchmark("Read_Environment")

        logging.info("ramp to end voltage: from %E V to %E V with step %E V", lcr_voltage_level, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                self.lcr_set_bias_voltage_level(lcr, voltage)

                # Delay
                time.sleep(waiting_time)

                dt = time.time() - t0
                est.next()
                self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read LCR, for CpRp -> prim: Cp, sec: Rp
                with benchmark_lcr:
                    if lcr_soft_filter:
                        lcr_prim, lcr_sec = self.lcr_acquire_filter_reading(lcr)
                    else:
                        lcr_prim, lcr_sec = self.lcr_acquire_reading(lcr)
                    try:
                        lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                    except ZeroDivisionError:
                        lcr_prim2 = 0.0

                # read V Source
                with benchmark_lcr_source:
                    lcr_reading = self.lcr_get_bias_polarity_current_level(lcr)
                logging.info("LCR reading: %E A", lcr_reading)

                self.process.emit("reading", "lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                self.process.emit("reading", "lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

                self.process.emit("update")
                self.process.emit("state", dict(
                    lcr_voltage=voltage,
                    lcr_current=lcr_reading
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
                    voltage_lcr=voltage,
                    current_lcr=lcr_reading,
                    capacitance=lcr_prim,
                    capacitance2=lcr_prim2,
                    resistance=lcr_sec,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                )

                # Compliance?

                if not self.process.running:
                    break

        logging.info(benchmark_step)
        logging.info(benchmark_lcr)
        logging.info(benchmark_lcr_source)
        logging.info(benchmark_environ)

    def finalize(self, lcr):
        self.process.emit("progress", 1, 2)
        self.process.emit("state", dict(
            lcr_current=None,
        ))

        self.quick_ramp_zero(lcr)
        self.lcr_set_bias_state(lcr, False)
        self.process.emit("state", dict(
            lcr_output=self.lcr_get_bias_state(lcr),
        ))

        self.process.emit("state", dict(
            lcr_voltage=None,
            lcr_current=None,
            lcr_output=None
        ))

        self.process.emit("state", dict(
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def run(self):
        with self.resources.get("lcr") as lcr_resource:
            super().run(
                lcr=E4980A(lcr_resource)
            )

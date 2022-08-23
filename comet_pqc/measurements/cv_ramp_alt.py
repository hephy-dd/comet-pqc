import contextlib
import logging
import time

import comet
import numpy as np

# from comet.driver.keysight import E4980A
from ..core.benchmark import Benchmark
from ..core.estimate import Estimate
from ..driver import E4980A
from ..utils import format_metric
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .mixins import AnalysisMixin, EnvironmentMixin, LCRMixin

__all__ = ["CVRampAltMeasurement"]

logger = logging.getLogger(__name__)


class CVRampAltMeasurement(MatrixMeasurement, LCRMixin, EnvironmentMixin, AnalysisMixin):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter("bias_voltage_start", unit="V", required=True)
        self.register_parameter("bias_voltage_stop", unit="V", required=True)
        self.register_parameter("bias_voltage_step", unit="V", required=True)
        self.register_parameter("waiting_time", 1.0, unit="s")
        self.register_parameter("bias_voltage_step_before", comet.ureg("0 V"), unit="V")
        self.register_parameter("waiting_time_before", comet.ureg("100 ms"), unit="s")
        self.register_parameter("bias_voltage_step_after", comet.ureg("0 V"), unit="V")
        self.register_parameter("waiting_time_after", comet.ureg("100 ms"), unit="s")
        self.register_parameter("waiting_time_start", comet.ureg("0 s"), unit="s")
        self.register_parameter("waiting_time_end", comet.ureg("0 s"), unit="s")
        self.register_lcr()
        self.register_environment()
        self.register_analysis()

    def quick_ramp_zero(self, lcr):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)

        bias_voltage_step_after = self.get_parameter("bias_voltage_step_after") or self.get_parameter("bias_voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")

        lcr_output = self.lcr_get_bias_state(lcr)
        self.process.emit("state", {"lcr_output": lcr_output})
        if lcr_output:
            lcr_voltage_level = self.lcr_get_bias_voltage_level(lcr)
            ramp = comet.Range(lcr_voltage_level, 0, bias_voltage_step_after)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, ramp.count)
                self.lcr_set_bias_voltage_level(lcr, voltage)
                self.process.emit("state", {"lcr_voltage": voltage})
                time.sleep(waiting_time_after)
        self.process.emit("state", {"lcr_output": self.lcr_get_bias_state(lcr)})
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def initialize(self, lcr):
        self.process.emit("progress", 1, 6)

        # Parameters
        bias_voltage_start = self.get_parameter("bias_voltage_start")
        bias_voltage_step = self.get_parameter("bias_voltage_step")
        bias_voltage_stop = self.get_parameter("bias_voltage_stop")
        waiting_time = self.get_parameter("waiting_time")
        bias_voltage_step_before = self.get_parameter("bias_voltage_step_before") or self.get_parameter("bias_voltage_step")
        waiting_time_before = self.get_parameter("waiting_time_before")
        bias_voltage_step_after = self.get_parameter("bias_voltage_step_after") or self.get_parameter("bias_voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")
        waiting_time_start = self.get_parameter("waiting_time_start")
        waiting_time_end = self.get_parameter("waiting_time_end")

        # Extend meta data
        self.set_meta("bias_voltage_start", f"{bias_voltage_start:G} V")
        self.set_meta("bias_voltage_stop", f"{bias_voltage_stop:G} V")
        self.set_meta("bias_voltage_step", f"{bias_voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("bias_voltage_step_before", f"{bias_voltage_step_before:G} V")
        self.set_meta("waiting_time_before", f"{waiting_time_before:G} s")
        self.set_meta("bias_voltage_step_after", f"{bias_voltage_step_after:G} V")
        self.set_meta("waiting_time_after", f"{waiting_time_after:G} s")
        self.set_meta("waiting_time_start", f"{waiting_time_start:G} s")
        self.set_meta("waiting_time_end", f"{waiting_time_end:G} s")
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
        self.process.emit("state", {
            "lcr_voltage": self.lcr_get_bias_voltage_level(lcr),
            "lcr_output": self.lcr_get_bias_state(lcr),
        })

        # Ramp to start voltage

        lcr_voltage_level = self.lcr_get_bias_voltage_level(lcr)

        logger.info("LCR Meter ramp to start voltage: from %E V to %E V with step %E V", lcr_voltage_level, bias_voltage_start, bias_voltage_step_before)
        for voltage in comet.Range(lcr_voltage_level, bias_voltage_start, bias_voltage_step_before):
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.process.emit("progress", 0, 1)
            self.lcr_set_bias_voltage_level(lcr, voltage)
            time.sleep(waiting_time_after)
            self.process.emit("state", {"lcr_voltage": voltage})

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

    def measure(self, lcr):
        self.process.emit("progress", 1, 2)

        # Parameters
        bias_voltage_step = self.get_parameter("bias_voltage_step")
        bias_voltage_stop = self.get_parameter("bias_voltage_stop")
        waiting_time = self.get_parameter("waiting_time")
        lcr_soft_filter = self.get_parameter("lcr_soft_filter")

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

        logger.info("LCR Meter ramp to end voltage: from %E V to %E V with step %E V", lcr_voltage_level, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                self.lcr_set_bias_voltage_level(lcr, voltage)

                # Delay
                time.sleep(waiting_time)

                dt = time.time() - t0
                est.advance()
                self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                self.environment_update()

                # LCR read current
                with benchmark_lcr_source:
                    lcr_reading = self.lcr_get_bias_polarity_current_level(lcr)

                self.process.emit("update")
                self.process.emit("state", {
                    "lcr_voltage": voltage,
                    "lcr_current": lcr_reading
                })

                # read LCR, for CpRp -> prim: Cp, sec: Rp
                with benchmark_lcr:
                    try:
                        if lcr_soft_filter:
                            lcr_prim, lcr_sec = self.lcr_acquire_filter_reading(lcr)
                        else:
                            lcr_prim, lcr_sec = self.lcr_acquire_reading(lcr)
                    except Exception as exc:
                        raise RuntimeError(f"Failed to read from LCR: {exc}") from exc
                    try:
                        lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                    except ZeroDivisionError:
                        lcr_prim2 = 0.0

                self.process.emit("reading", "lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                self.process.emit("reading", "lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

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

                if not self.process.running:
                    break

        logger.info(benchmark_step)
        logger.info(benchmark_lcr)
        logger.info(benchmark_lcr_source)
        logger.info(benchmark_environ)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        v = np.array(self.get_series("voltage_lcr"))
        c = np.array(self.get_series("capacitance"))
        self.analysis_cv(c, v)

        self.process.emit("progress", 1, 1)

    def finalize(self, lcr):
        self.process.emit("progress", 1, 2)
        waiting_time_end = self.get_parameter("waiting_time_end")

        self.process.emit("state", {"lcr_current": None})

        self.quick_ramp_zero(lcr)

        # Waiting time after ramp down.
        self.wait(waiting_time_end)

        self.lcr_set_bias_state(lcr, False)
        self.process.emit("state", {
            "lcr_output": self.lcr_get_bias_state(lcr)
        })

        self.process.emit("state", {
            "lcr_voltage": None,
            "lcr_current": None,
            "lcr_output": None,
        })

        self.process.emit("state", {
            "env_chuck_temperature": None,
            "env_box_temperature": None,
            "env_box_humidity": None,
        })

        self.process.emit("progress", 2, 2)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                lcr=E4980A(es.enter_context(self.resources.get("lcr")))
            )

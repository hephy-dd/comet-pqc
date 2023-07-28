import logging
import time

import comet
import numpy as np

from ..core.benchmark import Benchmark
from ..core.estimate import Estimate
from ..core.functions import LinearRange
from ..utils import format_metric
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .mixins import AnalysisMixin, EnvironmentMixin, HVSourceMixin, LCRMixin

__all__ = ["CVRampMeasurement"]

logger = logging.getLogger(__name__)


class CVRampMeasurement(MatrixMeasurement, HVSourceMixin, LCRMixin, EnvironmentMixin, AnalysisMixin):
    """CV ramp measurement."""

    type = "cv_ramp"

    required_instruments = ["hvsrc", "lcr"]

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
        self.register_parameter("hvsrc_current_compliance", unit="A", required=True)
        self.register_parameter("hvsrc_accept_compliance", False, type=bool)
        self.register_vsource()
        self.register_lcr()
        self.register_environment()
        self.register_analysis()

    def quick_ramp_zero(self, hvsrc):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)

        bias_voltage_step_after = self.get_parameter("bias_voltage_step_after") or self.get_parameter("bias_voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")

        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", {"hvsrc_output": hvsrc_output_state})
        if hvsrc_output_state:
            hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)
            ramp = LinearRange(hvsrc_voltage_level, 0, bias_voltage_step_after)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, len(ramp))
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                self.process.emit("state", {"hvsrc_voltage": voltage})
                time.sleep(waiting_time_after)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", {"hvsrc_output": hvsrc_output_state})
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def initialize(self, hvsrc, lcr):
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
        hvsrc_current_compliance = self.get_parameter("hvsrc_current_compliance")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")

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
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.set_meta("hvsrc_accept_compliance", hvsrc_accept_compliance)
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
        hvsrc_current_compliance = self.get_parameter("hvsrc_current_compliance")
        self.hvsrc_set_current_compliance(hvsrc, hvsrc_current_compliance)
        self.process.emit("progress", 4, 6)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_ON)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", {"hvsrc_output": hvsrc_output_state})

        # Initialize LCR

        self.lcr_reset(lcr)
        self.lcr_setup(lcr)

        self.process.emit("progress", 5, 6)

        # Ramp to start voltage

        hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

        logger.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, bias_voltage_start, bias_voltage_step_before)
        for voltage in LinearRange(hvsrc_voltage_level, bias_voltage_start, bias_voltage_step_before):
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            time.sleep(waiting_time_before)
            self.process.emit("state", {"hvsrc_voltage": voltage})

            # Compliance tripped?
            self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

        self.process.emit("progress", 6, 6)

    def measure(self, hvsrc, lcr):
        self.process.emit("progress", 1, 2)
        # Parameters
        bias_voltage_step = self.get_parameter("bias_voltage_step")
        bias_voltage_stop = self.get_parameter("bias_voltage_stop")
        waiting_time = self.get_parameter("waiting_time")
        hvsrc_current_compliance = self.get_parameter("hvsrc_current_compliance")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")
        lcr_soft_filter = self.get_parameter("lcr_soft_filter")

        if not self.process.running:
            return

        hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

        ramp = LinearRange(hvsrc_voltage_level, bias_voltage_stop, bias_voltage_step)
        est = Estimate(len(ramp))
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        self.hvsrc_clear(hvsrc)

        benchmark_step = Benchmark("Single_Step")
        benchmark_lcr = Benchmark("Read_LCR")
        benchmark_hvsrc = Benchmark("Read_HV_Source")
        benchmark_environ = Benchmark("Read_Environment")

        logger.info("HV Source ramp to end voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                self.hvsrc_set_voltage_level(hvsrc, voltage)

                # Delay
                time.sleep(waiting_time)

                dt = time.time() - t0
                est.advance()
                self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                self.environment_update()

                # read HV Source
                with benchmark_hvsrc:
                    hvsrc_reading = self.hvsrc_read_current(hvsrc)

                self.process.emit("update")
                self.process.emit("state", {
                    "hvsrc_voltage": voltage,
                    "hvsrc_current": hvsrc_reading
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
                    voltage_hvsrc=voltage,
                    current_hvsrc=hvsrc_reading,
                    capacitance=lcr_prim,
                    capacitance2=lcr_prim2,
                    resistance=lcr_sec,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                )

                # Compliance tripped?
                if hvsrc_accept_compliance:
                    if self.hvsrc_compliance_tripped(hvsrc):
                        logger.info("HV Source compliance tripped, gracefully stopping measurement.")
                        break
                else:
                    self.hvsrc_check_compliance(hvsrc)

                if not self.process.running:
                    break

        logger.info(benchmark_step)
        logger.info(benchmark_lcr)
        logger.info(benchmark_hvsrc)
        logger.info(benchmark_environ)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        v = np.array(self.get_series("voltage_hvsrc"))
        c = np.array(self.get_series("capacitance"))
        self.analysis_cv(c, v)

        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 1, 2)
        waiting_time_end = self.get_parameter("waiting_time_end")

        self.process.emit("state", {"hvsrc_current": None})

        self.quick_ramp_zero(hvsrc)

        # Waiting time after ramp down.
        self.wait(waiting_time_end)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", {"hvsrc_output": hvsrc_output_state})

        self.process.emit("state", {
            "env_chuck_temperature": None,
            "env_box_temperature": None,
            "env_box_humidity": None
        })

        self.process.emit("progress", 2, 2)

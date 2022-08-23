import contextlib
import logging
import time

import comet
import numpy as np
from comet.driver.keithley import K6517B

from ..benchmark import Benchmark
from ..estimate import Estimate
from ..utils import format_metric
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .mixins import (
    AnalysisMixin,
    ElectrometerMixin,
    EnvironmentMixin,
    HVSourceMixin,
)

__all__ = ["IVRampElmMeasurement"]

logger = logging.getLogger(__name__)


class IVRampElmMeasurement(MatrixMeasurement, HVSourceMixin, ElectrometerMixin, EnvironmentMixin, AnalysisMixin):
    """IV ramp with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_elm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter("voltage_start", unit="V", required=True)
        self.register_parameter("voltage_stop", unit="V", required=True)
        self.register_parameter("voltage_step", unit="V", required=True)
        self.register_parameter("waiting_time", 1.0, unit="s")
        self.register_parameter("voltage_step_before", comet.ureg("0 V"), unit="V")
        self.register_parameter("waiting_time_before", comet.ureg("100 ms"), unit="s")
        self.register_parameter("voltage_step_after", comet.ureg("0 V"), unit="V")
        self.register_parameter("waiting_time_after", comet.ureg("100 ms"), unit="s")
        self.register_parameter("waiting_time_start", comet.ureg("0 s"), unit="s")
        self.register_parameter("waiting_time_end", comet.ureg("0 s"), unit="s")
        self.register_parameter("hvsrc_current_compliance", unit="A", required=True)
        self.register_parameter("hvsrc_accept_compliance", False, type=bool)
        self.register_parameter("elm_filter_enable", False, type=bool)
        self.register_parameter("elm_filter_count", 10, type=int)
        self.register_parameter("elm_filter_type", "repeat")
        self.register_parameter("elm_zero_correction", False, type=bool)
        self.register_parameter("elm_integration_rate", 50, type=int)
        self.register_parameter("elm_current_range", comet.ureg("20 pA"), unit="A")
        self.register_parameter("elm_current_autorange_enable", False, type=bool)
        self.register_parameter("elm_current_autorange_minimum", comet.ureg("20 pA"), unit="A")
        self.register_parameter("elm_current_autorange_maximum", comet.ureg("20 mA"), unit="A")
        self.register_hvsource()
        self.register_elm()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc, elm):
        self.process.emit("progress", 0, 5)

        # Parameters
        voltage_start = self.get_parameter("voltage_start")
        voltage_stop = self.get_parameter("voltage_stop")
        voltage_step = self.get_parameter("voltage_step")
        waiting_time = self.get_parameter("waiting_time")
        voltage_step_before = self.get_parameter("voltage_step_before") or self.get_parameter("voltage_step")
        waiting_time_before = self.get_parameter("waiting_time_before")
        voltage_step_after = self.get_parameter("voltage_step_after") or self.get_parameter("voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")
        waiting_time_start = self.get_parameter("waiting_time_start")
        waiting_time_end = self.get_parameter("waiting_time_end")
        hvsrc_current_compliance = self.get_parameter("hvsrc_current_compliance")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")
        elm_filter_enable = self.get_parameter("elm_filter_enable")
        elm_filter_count = self.get_parameter("elm_filter_count")
        elm_filter_type = self.get_parameter("elm_filter_type")
        elm_zero_correction = self.get_parameter("elm_zero_correction")
        elm_integration_rate = self.get_parameter("elm_integration_rate")
        elm_current_range = self.get_parameter("elm_current_range")
        elm_current_autorange_enable = self.get_parameter("elm_current_autorange_enable")
        elm_current_autorange_minimum = self.get_parameter("elm_current_autorange_minimum")
        elm_current_autorange_maximum = self.get_parameter("elm_current_autorange_maximum")
        elm_read_timeout = self.get_parameter("elm_read_timeout")

        # Extend meta data
        self.set_meta("voltage_start", f"{voltage_start:G} V")
        self.set_meta("voltage_stop", f"{voltage_stop:G} V")
        self.set_meta("voltage_step", f"{voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("voltage_step_before", f"{voltage_step_before:G} V")
        self.set_meta("waiting_time_before", f"{waiting_time_before:G} s")
        self.set_meta("voltage_step_after", f"{voltage_step_after:G} V")
        self.set_meta("waiting_time_after", f"{waiting_time_after:G} s")
        self.set_meta("waiting_time_start", f"{waiting_time_start:G} s")
        self.set_meta("waiting_time_end", f"{waiting_time_end:G} s")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.set_meta("hvsrc_accept_compliance", hvsrc_accept_compliance)
        self.hvsrc_update_meta()
        self.set_meta("elm_filter_enable", elm_filter_enable)
        self.set_meta("elm_filter_count", elm_filter_count)
        self.set_meta("elm_filter_type", elm_filter_type)
        self.set_meta("elm_zero_correction", elm_zero_correction)
        self.set_meta("elm_integration_rate", elm_integration_rate)
        self.set_meta("elm_current_range", format(elm_current_range, "G"))
        self.set_meta("elm_current_autorange_enable", elm_current_autorange_enable)
        self.set_meta("elm_current_autorange_minimum", format(elm_current_autorange_minimum, "G"))
        self.set_meta("elm_current_autorange_maximum", format(elm_current_autorange_maximum, "G"))
        self.set_meta("elm_read_timeout", format(elm_read_timeout, "G"))
        self.elm_update_meta()
        self.environment_update_meta()

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

        self.hvsrc_reset(hvsrc)
        self.hvsrc_setup(hvsrc)
        self.hvsrc_set_current_compliance(hvsrc, hvsrc_current_compliance)

        self.process.emit("state", {
            "hvsrc_voltage": self.hvsrc_get_voltage_level(hvsrc),
            "hvsrc_current": None,
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc),
            "elm_current": None,
        })

        self.process.emit("progress", 1, 5)

        # If output disabled
        voltage = 0
        self.hvsrc_set_voltage_level(hvsrc, voltage)
        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_ON)
        time.sleep(.100)

        self.process.emit("state", {
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc)
        })

        self.process.emit("progress", 2, 5)

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

        self.elm_set_zero_check(elm, True)
        assert self.elm_get_zero_check(elm) is True, "failed to enable zero check"

        self.elm_safe_write(elm, ":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        self.elm_safe_write(elm, f":SENS:CURR:RANG {elm_current_range:E}")
        if elm_zero_correction:
            self.elm_safe_write(elm, ":SYST:ZCOR ON") # perform zero correction
        # Auto range
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO {elm_current_autorange_enable:d}")
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO:LLIM {elm_current_autorange_minimum:E}")
        self.elm_safe_write(elm, f":SENS:CURR:RANG:AUTO:ULIM {elm_current_autorange_maximum:E}")

        self.elm_set_zero_check(elm, False)
        assert self.elm_get_zero_check(elm) is False, "failed to disable zero check"

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        logger.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step_before)
        for voltage in comet.Range(voltage, voltage_start, voltage_step_before):
            self.process.emit("message", f"{voltage:.3f} V")
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", {"hvsrc_voltage": voltage})

            time.sleep(waiting_time_before)

            # Compliance tripped?
            self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

        self.process.emit("progress", 3, 5)

    def measure(self, hvsrc, elm):
        # Parameters
        voltage_start = self.get_parameter("voltage_start")
        voltage_stop = self.get_parameter("voltage_stop")
        voltage_step = self.get_parameter("voltage_step")
        waiting_time = self.get_parameter("waiting_time")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")
        elm_read_timeout = self.get_parameter("elm_read_timeout")

        if not self.process.running:
            return

        voltage = self.hvsrc_get_voltage_level(hvsrc)

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

        logger.info("HV Source ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            with benchmark_step:
                self.hvsrc_clear(hvsrc)
                self.hvsrc_set_voltage_level(hvsrc, voltage)

                time.sleep(waiting_time)

                dt = time.time() - t0

                est.advance()
                self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                self.process.emit("progress", *est.progress)

                self.environment_update()

                # read HV Source
                with benchmark_hvsrc:
                    hvsrc_reading = self.hvsrc_read_current(hvsrc)
                self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, hvsrc_reading)

                # read ELM
                with benchmark_elm:
                    try:
                        elm_reading = self.elm_read(elm, timeout=elm_read_timeout)
                    except Exception as exc:
                        raise RuntimeError(f"Failed to read from ELM: {exc}") from exc
                self.elm_check_error(elm)
                logger.info("ELM reading: %s", format_metric(elm_reading, "A"))
                self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                self.process.emit("update")
                self.process.emit("state", {
                    "hvsrc_voltage": voltage,
                    "hvsrc_current": hvsrc_reading,
                    "elm_current": elm_reading,
                })

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
        logger.info(benchmark_elm)
        logger.info(benchmark_hvsrc)
        logger.info(benchmark_environ)

        self.process.emit("progress", 4, 5)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        i = np.array(self.get_series("current_elm"))
        v = np.array(self.get_series("voltage"))
        self.analysis_iv(i, v)

        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, elm):
        self.process.emit("progress", 0, 2)
        voltage_step_after = self.get_parameter("voltage_step_after") or self.get_parameter("voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")
        waiting_time_end = self.get_parameter("waiting_time_end")

        try:
            self.elm_set_zero_check(elm, True)
            assert self.elm_get_zero_check(elm) is True, "failed to enable zero check"
        finally:
            self.process.emit("message", "Ramp to zero...")
            self.process.emit("progress", 1, 2)
            self.process.emit("state", {
                "hvsrc_current": None,
                "elm_current": None,
            })

            voltage = self.hvsrc_get_voltage_level(hvsrc)

            logger.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step_after)
            for voltage in comet.Range(voltage, 0, voltage_step_after):
                self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                self.process.emit("state", {"hvsrc_voltage": voltage})
                time.sleep(waiting_time_after)

            # Waiting time after ramp down.
            self.wait(waiting_time_end)

            self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)

            self.process.emit("state", {
                "hvsrc_output": self.hvsrc_get_output_state(hvsrc),
                "env_chuck_temperature": None,
                "env_box_temperature": None,
                "env_box_humidity": None,
            })

            self.process.emit("progress", 2, 2)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=self.hvsrc_create(es.enter_context(self.resources.get("hvsrc"))),
                elm=K6517B(es.enter_context(self.resources.get("elm")))
            )

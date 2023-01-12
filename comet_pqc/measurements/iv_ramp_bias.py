import logging
import time

import comet
import numpy as np

from ..core.estimate import Estimate
from ..core.functions import LinearRange
from ..utils import format_metric
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .mixins import (
    AnalysisMixin,
    EnvironmentMixin,
    HVSourceMixin,
    VSourceMixin,
)

__all__ = ["IVRampBiasMeasurement"]

logger = logging.getLogger(__name__)


class IVRampBiasMeasurement(MatrixMeasurement, HVSourceMixin, VSourceMixin, EnvironmentMixin, AnalysisMixin):
    """Bias IV ramp measurement."""

    type_name = "iv_ramp_bias"

    required_instruments = ["hvsrc", "vsrc"]

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
        self.register_parameter("bias_voltage", unit="V", required=True)
        self.register_parameter("bias_mode", "constant", values=("constant", "offset"))
        self.register_parameter("hvsrc_current_compliance", unit="A", required=True)
        self.register_parameter("hvsrc_accept_compliance", False, type=bool)
        self.register_parameter("vsrc_current_compliance", unit="A", required=True)
        self.register_parameter("vsrc_accept_compliance", False, type=bool)
        self.register_hvsource()
        self.register_vsource()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc, vsrc):
        self.set_progress(1, 5)

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
        bias_voltage = self.get_parameter("bias_voltage")
        bias_mode = self.get_parameter("bias_mode")
        hvsrc_current_compliance = self.get_parameter("hvsrc_current_compliance")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")
        vsrc_current_compliance = self.get_parameter("vsrc_current_compliance")
        vsrc_accept_compliance = self.get_parameter("vsrc_accept_compliance")

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
        self.set_meta("bias_voltage", f"{bias_voltage:G} V")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
        self.set_meta("hvsrc_accept_compliance", hvsrc_accept_compliance)
        self.hvsrc_update_meta()
        self.set_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
        self.set_meta("vsrc_accept_compliance", vsrc_accept_compliance)
        self.vsrc_update_meta()
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage", "V")
        self.set_series_unit("current_vsrc", "A")
        self.set_series_unit("bias_voltage", "V")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage")
        self.register_series("current_vsrc")
        self.register_series("bias_voltage")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        # Initialize HV Source

        self.hvsrc_reset(hvsrc)
        self.hvsrc_setup(hvsrc)
        self.hvsrc_set_current_compliance(hvsrc, hvsrc_current_compliance)

        self.update_state({
            "hvsrc_voltage": self.hvsrc_get_voltage_level(hvsrc),
            "hvsrc_current": None,
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc),
        })

        if not self.process.running:
            return

        # Initialize V Source

        self.vsrc_reset(vsrc)
        self.vsrc_setup(vsrc)

        # Voltage source
        self.vsrc_set_function_voltage(vsrc)

        self.vsrc_set_current_compliance(vsrc, vsrc_current_compliance)

        if not self.process.running:
            return

        # Output enable

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_ON)
        time.sleep(.100)
        self.update_state({
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc)
        })
        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_ON)
        time.sleep(.100)
        self.update_state({
            "vsrc_output": self.vsrc_get_output_state(vsrc)
        })

        self.set_message("Ramp to start...")

        # Ramp HV Spource to bias voltage
        voltage = self.vsrc_get_voltage_level(vsrc)

        logger.info("V Source ramp to bias voltage: from %E V to %E V with step %E V", voltage, bias_voltage, voltage_step_before)
        for voltage in LinearRange(voltage, bias_voltage, voltage_step_before):
            self.set_message("Ramp to bias... {}".format(format_metric(voltage, "V")))
            self.vsrc_set_voltage_level(vsrc, voltage)
            self.update_state({"vsrc_voltage": voltage})
            time.sleep(waiting_time_before)

            # Compliance tripped?
            self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

        # Ramp HV Source to start voltage
        voltage = self.hvsrc_get_voltage_level(hvsrc)

        logger.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step_before)
        for voltage in LinearRange(voltage, voltage_start, voltage_step_before):
            self.set_message("Ramp to start... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.update_state({"hvsrc_voltage": voltage})
            time.sleep(waiting_time_before)

            # Compliance tripped?
            self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

        self.set_progress(5, 5)

    def measure(self, hvsrc, vsrc):
        self.set_progress(1, 2)

        # Parameters
        voltage_start = self.get_parameter("voltage_start")
        voltage_stop = self.get_parameter("voltage_stop")
        voltage_step = self.get_parameter("voltage_step")
        waiting_time = self.get_parameter("waiting_time")
        bias_voltage = self.get_parameter("bias_voltage")
        bias_mode = self.get_parameter("bias_mode")
        hvsrc_accept_compliance = self.get_parameter("hvsrc_accept_compliance")
        vsrc_accept_compliance = self.get_parameter("vsrc_accept_compliance")

        if not self.process.running:
            return

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        ramp = LinearRange(voltage, voltage_stop, voltage_step)
        est = Estimate(len(ramp))
        self.set_progress(*est.progress)

        t0 = time.time()

        logger.info("HV Source ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.update_state({"hvsrc_voltage": voltage})
            # Move bias TODO
            if bias_mode == "offset":
                bias_voltage += abs(ramp.step) if ramp.begin <= ramp.end else -abs(ramp.step)
                self.vsrc_set_voltage_level(vsrc, bias_voltage)
                self.update_state({"vsrc_voltage": bias_voltage})

            time.sleep(waiting_time)

            dt = time.time() - t0

            est.advance()
            self.set_message("{} | HV Source {} | Bias {}".format(format_estimate(est), format_metric(voltage, "V"), format_metric(bias_voltage, "V")))
            self.set_progress(*est.progress)

            self.environment_update()

            # read V Source
            vsrc_reading = self.vsrc_read_current(vsrc)
            self.append_reading("vsrc", abs(voltage) if ramp.step < 0 else voltage, vsrc_reading)

            # read HV Source
            hvsrc_reading = self.hvsrc_read_current(hvsrc)

            self.update_plots()
            self.update_state({
                "hvsrc_current": hvsrc_reading,
                "vsrc_current": vsrc_reading
            })

            # Append series data
            self.append_series(
                timestamp=dt,
                voltage=voltage,
                current_vsrc=vsrc_reading,
                bias_voltage=bias_voltage,
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
            if vsrc_accept_compliance:
                if self.vsrc_compliance_tripped(vsrc):
                    logger.info("V Source compliance tripped, gracefully stopping measurement.")
                    break
            else:
                self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

        self.set_progress(2, 2)

    def analyze(self, **kwargs):
        self.set_progress(0, 1)

        i = np.array(self.get_series("current_vsrc"))
        v = np.array(self.get_series("voltage"))
        self.analysis_iv(i, v)

        self.set_progress(1, 1)

    def finalize(self, hvsrc, vsrc):
        self.set_progress(1, 2)
        self.set_message("Ramp to zero...")

        voltage_step_after = self.get_parameter("voltage_step_after") or self.get_parameter("voltage_step")
        waiting_time_after = self.get_parameter("waiting_time_after")
        waiting_time_end = self.get_parameter("waiting_time_end")

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        logger.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step_after)
        for voltage in LinearRange(voltage, 0, voltage_step_after):
            self.set_message("Ramp to zero... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.update_state({"hvsrc_voltage": voltage})
            time.sleep(waiting_time_after)

        bias_voltage = self.vsrc_get_voltage_level(vsrc)

        logger.info("V Source ramp bias to zero: from %E V to %E V with step %E V", bias_voltage, 0, voltage_step_after)
        for voltage in LinearRange(bias_voltage, 0, voltage_step_after):
            self.set_message("Ramp bias to zero... {}".format(format_metric(voltage, "V")))
            self.vsrc_set_voltage_level(vsrc, voltage)
            self.update_state({"vsrc_voltage": voltage})
            time.sleep(waiting_time_after)

        # Waiting time after ramp down.
        self.wait(waiting_time_end)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)
        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_OFF)

        self.update_state({
            "hvsrc_output": self.hvsrc_get_output_state(hvsrc),
            "hvsrc_voltage": None,
            "hvsrc_current": None,
            "vsrc_output": self.vsrc_get_output_state(vsrc),
            "vsrc_voltage": None,
            "vsrc_current": None,
            "env_chuck_temperature": None,
            "env_box_temperature": None,
            "env_box_humidity": None,
        })

        self.set_progress(2, 2)

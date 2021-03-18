import contextlib
import logging
import time

import comet

import numpy as np

from ..utils import format_metric
from ..estimate import Estimate

from .matrix import MatrixMeasurement
from .measurement import format_estimate

from .mixins import VSourceMixin
from .mixins import EnvironmentMixin
from .mixins import AnalysisMixin

__all__ = ["IVRamp4WireMeasurement"]

class IVRamp4WireMeasurement(MatrixMeasurement, VSourceMixin, EnvironmentMixin, AnalysisMixin):
    """IV ramp 4wire with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start current
    * ramps to end current
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_4_wire"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter('current_start', unit='A', required=True)
        self.register_parameter('current_stop', unit='A', required=True)
        self.register_parameter('current_step', unit='A', required=True)
        self.register_parameter('waiting_time', 1.0, unit='s')
        self.register_parameter('current_step_before', comet.ureg('0 A'), unit='A')
        self.register_parameter('waiting_time_before', comet.ureg('100 ms'), unit='s')
        self.register_parameter('current_step_after', comet.ureg('0 A'), unit='A')
        self.register_parameter('waiting_time_after', comet.ureg('100 ms'), unit='s')
        self.register_parameter('waiting_time_start', comet.ureg('0 s'), unit='s')
        self.register_parameter('waiting_time_end', comet.ureg('0 s'), unit='s')
        self.register_parameter('vsrc_voltage_compliance', unit='V', required=True)
        self.register_parameter('vsrc_accept_compliance', False, type=bool)
        self.register_vsource()
        self.register_environment()
        self.register_analysis()

    def initialize(self, vsrc):
        self.process.emit("progress", 0, 5)

        # Parameters
        current_start = self.get_parameter('current_start')
        current_stop = self.get_parameter('current_stop')
        current_step = self.get_parameter('current_step')
        waiting_time = self.get_parameter('waiting_time')
        current_step_before = self.get_parameter('current_step_before') or self.get_parameter('current_step')
        waiting_time_before = self.get_parameter('waiting_time_before')
        current_step_after = self.get_parameter('current_step_after') or self.get_parameter('current_step')
        waiting_time_after = self.get_parameter('waiting_time_after')
        waiting_time_start = self.get_parameter('waiting_time_start')
        waiting_time_end = self.get_parameter('waiting_time_end')
        vsrc_voltage_compliance = self.get_parameter('vsrc_voltage_compliance')
        vsrc_accept_compliance = self.get_parameter('vsrc_accept_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        # Extend meta data
        self.set_meta("current_start", f"{current_start:G} A")
        self.set_meta("current_stop", f"{current_stop:G} A")
        self.set_meta("current_step", f"{current_step:G} A")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("current_step_before", f"{current_step_before:G} A")
        self.set_meta("waiting_time_before", f"{waiting_time_before:G} s")
        self.set_meta("current_step_after", f"{current_step_after:G} A")
        self.set_meta("waiting_time_after", f"{waiting_time_after:G} s")
        self.set_meta("waiting_time_start", f"{waiting_time_start:G} s")
        self.set_meta("waiting_time_end", f"{waiting_time_end:G} s")
        self.set_meta("vsrc_voltage_compliance", f"{vsrc_voltage_compliance:G} V")
        self.set_meta("vsrc_accept_compliance", vsrc_accept_compliance)
        self.vsrc_update_meta()
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("current", "A")
        self.set_series_unit("voltage_vsrc", "V")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("current")
        self.register_series("voltage_vsrc")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        self.process.emit("state", dict(
            vsrc_voltage=self.vsrc_get_voltage_level(vsrc),
            vsrc_current=self.vsrc_get_current_level(vsrc),
            vsrc_output=self.vsrc_get_output_state(vsrc)
        ))

        # Initialize V Source

        self.process.emit("progress", 1, 5)

        self.vsrc_reset(vsrc)
        self.process.emit("progress", 2, 5)

        self.vsrc_setup(vsrc)

        # Current source
        self.vsrc_set_function_current(vsrc)

        self.vsrc_set_voltage_compliance(vsrc, vsrc_voltage_compliance)

        self.process.emit("progress", 3, 5)

        # Override display
        self.vsrc_set_display(vsrc, 'voltage')

        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_ON)
        time.sleep(.100)
        self.process.emit("state", dict(
            vsrc_output=self.vsrc_get_output_state(vsrc),
        ))

        self.process.emit("progress", 4, 5)

        current = self.vsrc_get_current_level(vsrc)

        logging.info("V Source ramp to start current: from %E A to %E A with step %E A", current, current_start, current_step_before)
        for current in comet.Range(current, current_start, current_step_before):
            self.process.emit("message", "Ramp to start... {}".format(format_metric(current, "A")))
            self.vsrc_set_current_level(vsrc, current)
            time.sleep(waiting_time_before)

            self.process.emit("state", dict(
                vsrc_current=current,
            ))

            # Compliance tripped?
            self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

        self.process.emit("progress", 5, 5)

    def measure(self, vsrc):
        current_start = self.get_parameter('current_start')
        current_step = self.get_parameter('current_step')
        current_stop = self.get_parameter('current_stop')
        waiting_time = self.get_parameter('waiting_time')
        vsrc_voltage_compliance = self.get_parameter('vsrc_voltage_compliance')
        vsrc_accept_compliance = self.get_parameter('vsrc_accept_compliance')

        if not self.process.running:
            return

        current = self.vsrc_get_current_level(vsrc)

        ramp = comet.Range(current, current_stop, current_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        logging.info("V Source ramp to end current: from %E A to %E A with step %E A", current, ramp.end, ramp.step)
        for current in ramp:
            self.vsrc_clear(vsrc)
            self.vsrc_set_current_level(vsrc, current)
            self.process.emit("state", dict(
                vsrc_current=current,
            ))

            time.sleep(waiting_time)
            dt = time.time() - t0

            est.advance()
            self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(current, "A")))
            self.process.emit("progress", *est.progress)

            self.environment_update()

            # read V Source
            vsrc_reading = self.vsrc_read_voltage(vsrc)
            self.process.emit("reading", "vsrc", abs(current) if ramp.step < 0 else current, vsrc_reading)

            self.process.emit("update")
            self.process.emit("state", dict(
                vsrc_voltage=vsrc_reading
            ))

            # Append series data
            self.append_series(
                timestamp=dt,
                current=current,
                voltage_vsrc=vsrc_reading,
                temperature_box=self.environment_temperature_box,
                temperature_chuck=self.environment_temperature_chuck,
                humidity_box=self.environment_humidity_box
            )

            # Compliance tripped?
            if vsrc_accept_compliance:
                if self.vsrc_compliance_tripped(vsrc):
                    logging.info("V Source compliance tripped, gracefully stopping measurement.")
                    break
            else:
                self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        i = np.array(self.get_series('current'))
        v = np.array(self.get_series('voltage_vsrc'))
        self.analysis_iv(i, v)

        self.process.emit("progress", 1, 1)

    def finalize(self, vsrc):
        self.process.emit("progress", 1, 2)

        self.process.emit("state", dict(
            vsrc_voltage=None
        ))

        current_step_after = self.get_parameter('current_step_after') or self.get_parameter('current_step')
        waiting_time_after = self.get_parameter('waiting_time_after')
        waiting_time_end = self.get_parameter('waiting_time_end')

        current = self.vsrc_get_current_level(vsrc)

        logging.info("V Source ramp to zero: from %E A to %E A with step %E A", current, 0, current_step_after)
        for current in comet.Range(current, 0, current_step_after):
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(current, "A")))
            self.vsrc_set_current_level(vsrc, current)
            self.process.emit("state", dict(
                vsrc_current=current,
            ))
            time.sleep(waiting_time_after)

        # Waiting time after ramp down.
        self.wait(waiting_time_end)

        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_OFF)
        self.vsrc_check_error(vsrc)

        self.process.emit("state", dict(
            vsrc_output=self.vsrc_get_output_state(vsrc),
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                vsrc=self.vsrc_create(es.enter_context(self.resources.get("vsrc")))
            )

import contextlib
import logging
import time

import numpy as np

import comet

from ..utils import format_metric
from ..estimate import Estimate

from .matrix import MatrixMeasurement
from .measurement import format_estimate

from .mixins import HVSourceMixin
from .mixins import EnvironmentMixin
from .mixins import AnalysisMixin

__all__ = ["IVRampMeasurement"]

class IVRampMeasurement(MatrixMeasurement, HVSourceMixin, EnvironmentMixin, AnalysisMixin):
    """IV ramp measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_parameter('voltage_start', unit='V', required=True)
        self.register_parameter('voltage_stop', unit='V', required=True)
        self.register_parameter('voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', 1.0, unit='s')
        self.register_parameter('voltage_step_before', comet.ureg('0 V'), unit='V')
        self.register_parameter('waiting_time_before', comet.ureg('100 ms'), unit='s')
        self.register_parameter('voltage_step_after', comet.ureg('0 V'), unit='V')
        self.register_parameter('waiting_time_after', comet.ureg('100 ms'), unit='s')
        self.register_parameter('waiting_time_start', comet.ureg('0 s'), unit='s')
        self.register_parameter('waiting_time_end', comet.ureg('0 s'), unit='s')
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('hvsrc_accept_compliance', False, type=bool)
        self.register_hvsource()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc):
        self.process.emit("progress", 1, 4)

        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        voltage_step_before = self.get_parameter('voltage_step_before') or self.get_parameter('voltage_step')
        waiting_time_before = self.get_parameter('waiting_time_before')
        voltage_step_after = self.get_parameter('voltage_step_after') or self.get_parameter('voltage_step')
        waiting_time_after = self.get_parameter('waiting_time_after')
        waiting_time_start = self.get_parameter('waiting_time_start')
        waiting_time_end = self.get_parameter('waiting_time_end')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        hvsrc_accept_compliance = self.get_parameter('hvsrc_accept_compliance')

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
        self.environment_update_meta()

        # Series units
        self.set_series_unit("timestamp", "s")
        self.set_series_unit("voltage", "V")
        self.set_series_unit("current_hvsrc", "A")
        self.set_series_unit("temperature_box", "degC")
        self.set_series_unit("temperature_chuck", "degC")
        self.set_series_unit("humidity_box", "%")

        # Series
        self.register_series("timestamp")
        self.register_series("voltage")
        self.register_series("current_hvsrc")
        self.register_series("temperature_box")
        self.register_series("temperature_chuck")
        self.register_series("humidity_box")

        self.process.emit("state", dict(
            hvsrc_voltage=self.hvsrc_get_voltage_level(hvsrc),
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.hvsrc_reset(hvsrc)
        self.hvsrc_setup(hvsrc)

        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        self.hvsrc_set_current_compliance(hvsrc, hvsrc_current_compliance)

        self.process.emit("progress", 2, 4)

        voltage = self.hvsrc_get_voltage_level(hvsrc)
        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_ON)
        time.sleep(.100)

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 3, 4)

        if self.process.running:

            voltage = self.hvsrc_get_voltage_level(hvsrc)

            logging.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step_before)
            for voltage in comet.Range(voltage, voltage_start, voltage_step_before):
                self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                time.sleep(waiting_time_before)

                # Compliance tripped?
                self.hvsrc_check_compliance(hvsrc)

                if not self.process.running:
                    break

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        # Waiting time before measurement ramp.
        self.wait(waiting_time_start)

        self.process.emit("progress", 4, 4)

    def measure(self, hvsrc):
        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_accept_compliance = self.get_parameter('hvsrc_accept_compliance')

        if not self.process.running:
            return

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        t0 = time.time()

        ramp = comet.Range(voltage, voltage_stop, voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        logging.info("HV Source ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            self.hvsrc_set_voltage_level(hvsrc, voltage)

            time.sleep(waiting_time)

            td = time.time() - t0

            self.environment_update()

            reading_current = self.hvsrc_read_current(hvsrc)
            self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, reading_current)

            self.process.emit("update")
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
                hvsrc_current=reading_current
            ))

            # Append series data
            self.append_series(
                timestamp=td,
                voltage=voltage,
                current_hvsrc=reading_current,
                temperature_box=self.environment_temperature_box,
                temperature_chuck=self.environment_temperature_chuck,
                humidity_box=self.environment_humidity_box
            )
            est.advance()
            self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
            self.process.emit("progress", *est.progress)

            # Compliance tripped?
            if hvsrc_accept_compliance:
                if self.hvsrc_compliance_tripped(hvsrc):
                    logging.info("HV Source compliance tripped, gracefully stopping measurement.")
                    break
            else:
                self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        self.process.emit("progress", 0, 0)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        i = np.array(self.get_series('current_hvsrc'))
        v = np.array(self.get_series('voltage'))
        self.analysis_iv(i, v)

        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc):
        voltage_step_after = self.get_parameter('voltage_step_after') or self.get_parameter('voltage_step')
        waiting_time_after = self.get_parameter('waiting_time_after')
        waiting_time_end = self.get_parameter('waiting_time_end')

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        logging.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step_after)
        for voltage in comet.Range(voltage, 0, voltage_step_after):
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage
            ))
            time.sleep(waiting_time_after)

        # Waiting time after ramp down.
        self.wait(waiting_time_end)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)

        self.process.emit("state", dict(
            hvsrc_voltage=self.hvsrc_get_voltage_level(hvsrc),
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 5, 5)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=self.hvsrc_create(es.enter_context(self.resources.get("hvsrc")))
            )

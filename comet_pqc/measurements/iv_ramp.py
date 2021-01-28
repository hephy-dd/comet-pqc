import contextlib
import logging
import time

import numpy as np

import comet
from ..driver import K2410

from ..utils import format_metric
from ..estimate import Estimate

from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

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
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
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
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')

        # Extend meta data
        self.set_meta("voltage_start", f"{voltage_start:G} V")
        self.set_meta("voltage_stop", f"{voltage_stop:G} V")
        self.set_meta("voltage_step", f"{voltage_step:G} V")
        self.set_meta("waiting_time", f"{waiting_time:G} s")
        self.set_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
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

        # If output enabled
        if self.hvsrc_get_output_state(hvsrc):
            voltage = self.hvsrc_get_voltage_level(hvsrc)

            logging.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
            for voltage in comet.Range(voltage, 0, voltage_step):
                self.process.emit("message", f"{voltage:.3f} V")
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                time.sleep(QUICK_RAMP_DELAY)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.hvsrc_set_output_state(hvsrc, True)
            time.sleep(.100)

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 3, 4)

        if self.process.running:

            voltage = self.hvsrc_get_voltage_level(hvsrc)

            logging.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                time.sleep(QUICK_RAMP_DELAY)

                # Compliance tripped?
                self.hvsrc_check_compliance(hvsrc)

                if not self.process.running:
                    break

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 4, 4)

    def measure(self, hvsrc):
        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')

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
            reading_current = self.hvsrc_read_current(hvsrc)
            self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, reading_current)

            self.process.emit("update")
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
                hvsrc_current=reading_current
            ))

            self.environment_update()

            self.process.emit("state", dict(
                env_chuck_temperature=self.environment_temperature_chuck,
                env_box_temperature=self.environment_temperature_box,
                env_box_humidity=self.environment_humidity_box
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
            self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        self.process.emit("progress", 0, 0)

    def analyze(self, **kwargs):
        self.process.emit("progress", 1, 2)

        status = None

        i = np.array(self.get_series('current_hvsrc'))
        v = np.array(self.get_series('voltage'))

        if len(i) > 1 and len(v) > 1:

            for f in self.analysis_functions():
                r = f(v=v, i=i)
                logging.info(r)
                key, values = type(r).__name__, r._asdict()
                self.set_analysis(key, values)
                self.process.emit("append_analysis", key, values)
                if 'x_fit' in r._asdict():
                    for x, y in [(x, r.a * x + r.b) for x in r.x_fit]:
                        self.process.emit("reading", "xfit", x, y)
                    self.process.emit("update")

    def finalize(self, hvsrc):
        voltage_step = self.get_parameter('voltage_step')

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        logging.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage
            ))
            time.sleep(QUICK_RAMP_DELAY)

        self.hvsrc_set_output_state(hvsrc, False)

        self.process.emit("state", dict(
            hvsrc_voltage=self.hvsrc_get_voltage_level(hvsrc),
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 5, 5)

    def run(self):
        with contextlib.ExitStack() as es:
            super().run(
                hvsrc=K2410(es.enter_context(self.resources.get("hvsrc")))
            )

import contextlib
import logging
import time

import numpy as np

import comet

from comet.driver.keithley import K2657A

from ..utils import format_metric
from ..estimate import Estimate

from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

from .mixins import HVSourceMixin
from .mixins import VSourceMixin
from .mixins import EnvironmentMixin
from .mixins import AnalysisMixin

__all__ = ["IVRampBiasMeasurement"]

class IVRampBiasMeasurement(MatrixMeasurement, HVSourceMixin, VSourceMixin, EnvironmentMixin, AnalysisMixin):
    """Bias IV ramp measurement."""

    type = "iv_ramp_bias"

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
        self.register_parameter('bias_voltage', unit='V', required=True)
        self.register_parameter('bias_mode', 'constant', values=('constant', 'offset'))
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_hvsource()
        self.register_vsource()
        self.register_environment()
        self.register_analysis()

    def initialize(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 5)

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
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')

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
        self.hvsrc_update_meta()
        self.set_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
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

        self.process.emit("state", dict(
            hvsrc_voltage=self.hvsrc_get_voltage_level(hvsrc),
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

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
        self.process.emit("state", dict(
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))
        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_ON)
        time.sleep(.100)
        self.process.emit("state", dict(
            vsrc_output=self.vsrc_get_output_state(vsrc)
        ))

        self.process.emit("message", "Ramp to start...")

        # Ramp HV Spource to bias voltage
        voltage = self.vsrc_get_voltage_level(vsrc)

        logging.info("V Source ramp to bias voltage: from %E V to %E V with step %E V", voltage, bias_voltage, voltage_step_before)
        for voltage in comet.Range(voltage, bias_voltage, voltage_step_before):
            self.process.emit("message", "Ramp to bias... {}".format(format_metric(voltage, "V")))
            self.vsrc_set_voltage_level(vsrc, voltage)
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(waiting_time_before)

            # Compliance tripped?
            self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

        # Ramp HV Source to start voltage
        voltage = self.hvsrc_get_voltage_level(hvsrc)

        logging.info("HV Source ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step_before)
        for voltage in comet.Range(voltage, voltage_start, voltage_step_before):
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(waiting_time_before)

            # Compliance tripped?
            self.hvsrc_check_compliance(hvsrc)

            if not self.process.running:
                break

        # Waiting time before measurement ramp.
        time.sleep(waiting_time_start)

        self.process.emit("progress", 5, 5)

    def measure(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 2)

        # Parameters
        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')

        if not self.process.running:
            return

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        ramp = comet.Range(voltage, voltage_stop, voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        t0 = time.time()

        logging.info("HV Source ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            # Move bias TODO
            if bias_mode == "offset":
                bias_voltage += abs(ramp.step) if ramp.begin <= ramp.end else -abs(ramp.step)
                self.vsrc_set_voltage_level(vsrc, bias_voltage)
                self.process.emit("state", dict(
                    vsrc_voltage=bias_voltage,
                ))

            time.sleep(waiting_time)

            dt = time.time() - t0

            est.advance()
            self.process.emit("message", "{} | HV Source {} | Bias {}".format(format_estimate(est), format_metric(voltage, "V"), format_metric(bias_voltage, "V")))
            self.process.emit("progress", *est.progress)

            # read V Source
            vsrc_reading = self.vsrc_read_current(vsrc)
            self.process.emit("reading", "vsrc", abs(voltage) if ramp.step < 0 else voltage, vsrc_reading)

            # read HV Source
            hvsrc_reading = self.hvsrc_read_current(hvsrc)

            self.process.emit("update")
            self.process.emit("state", dict(
                hvsrc_current=hvsrc_reading,
                vsrc_current=vsrc_reading
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
                current_vsrc=vsrc_reading,
                bias_voltage=bias_voltage,
                temperature_box=self.environment_temperature_box,
                temperature_chuck=self.environment_temperature_chuck,
                humidity_box=self.environment_humidity_box
            )

            # Compliance tripped?
            self.hvsrc_check_compliance(hvsrc)
            self.vsrc_check_compliance(vsrc)

            if not self.process.running:
                break

        self.process.emit("progress", 2, 2)

    def analyze(self, **kwargs):
        self.process.emit("progress", 0, 1)

        status = None

        i = np.array(self.get_series('current_vsrc'))
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

        self.process.emit("progress", 1, 1)

    def finalize(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to zero...")

        voltage_step_after = self.get_parameter('voltage_step_after') or self.get_parameter('voltage_step')
        waiting_time_after = self.get_parameter('waiting_time_after')
        waiting_time_end = self.get_parameter('waiting_time_end')

        voltage = self.hvsrc_get_voltage_level(hvsrc)

        logging.info("HV Source ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step_after)
        for voltage in comet.Range(voltage, 0, voltage_step_after):
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(waiting_time_after)

        bias_voltage = self.vsrc_get_voltage_level(vsrc)

        logging.info("V Source ramp bias to zero: from %E V to %E V with step %E V", bias_voltage, 0, voltage_step_after)
        for voltage in comet.Range(bias_voltage, 0, voltage_step_after):
            self.process.emit("message", "Ramp bias to zero... {}".format(format_metric(voltage, "V")))
            self.vsrc_set_voltage_level(vsrc, voltage)
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(waiting_time_after)

        # Waiting time after ramp down.
        time.sleep(waiting_time_end)

        self.hvsrc_set_output_state(hvsrc, hvsrc.OUTPUT_OFF)
        self.vsrc_set_output_state(vsrc, vsrc.OUTPUT_OFF)

        self.process.emit("state", dict(
            hvsrc_output=self.hvsrc_get_output_state(hvsrc),
            hvsrc_voltage=None,
            hvsrc_current=None,
            vsrc_output=self.vsrc_get_output_state(vsrc),
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
                hvsrc=self.hvsrc_create(es.enter_context(self.resources.get("hvsrc"))),
                vsrc=self.vsrc_create(es.enter_context(self.resources.get("vsrc")))
            )

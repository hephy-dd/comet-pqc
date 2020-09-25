import datetime
import logging
import math
import time
import os
import re

import comet
from comet.driver.keithley import K2410

from ..proxy import create_proxy
from ..utils import format_metric
from ..formatter import PQCFormatter
from ..estimate import Estimate

from .matrix import MatrixMeasurement
from .measurement import ComplianceError
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

from .mixins import HVSourceMixin
from .mixins import EnvironmentMixin

__all__ = ["IVRampMeasurement"]

class IVRampMeasurement(MatrixMeasurement, HVSourceMixin, EnvironmentMixin):
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

    def initialize(self, hvsrc):
        self.process.emit("message", "Initialize...")
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

        hvsrc_proxy = create_proxy(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc_proxy.source_voltage_level,
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.hvsrc_reset(hvsrc)
        self.hvsrc_setup(hvsrc)

        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        self.hvsrc_set_compliance(hvsrc, hvsrc_current_compliance)

        self.process.emit("progress", 2, 4)

        # If output enabled
        if self.hvsrc_get_output_state(hvsrc):
            voltage = hvsrc_proxy.source_voltage_level

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
            for voltage in comet.Range(voltage, 0, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", f"{voltage:.3f} V")
                hvsrc_proxy.source_voltage_level = voltage
                # hvsrc_proxy.assert_success()
                time.sleep(QUICK_RAMP_DELAY)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            hvsrc_proxy.source_voltage_level = voltage
            hvsrc_proxy.assert_success()
            self.hvsrc_set_output_state(hvsrc, True)
            time.sleep(.100)

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 3, 4)

        if self.process.running:

            voltage = hvsrc_proxy.source_voltage_level

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, hvsrc.resource.query(":FORM:ELEM?").split(",")))
            hvsrc_proxy.assert_success()

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
                hvsrc_proxy.source_voltage_level = voltage
                # hvsrc_proxy.assert_success()
                # Returns <elements> comma separated
                #values = list(map(float, hvsrc.resource.query(":READ?").split(",")))
                #data = zip(elements, values)
                time.sleep(QUICK_RAMP_DELAY)
                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("compliance tripped")
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

        hvsrc_proxy = create_proxy(hvsrc)

        if not self.process.running:
            return

        voltage = hvsrc_proxy.source_voltage_level

        # HV Source reading format: CURR
        hvsrc.resource.write(":FORM:ELEM CURR")
        hvsrc.resource.query("*OPC?")

        t0 = time.time()

        ramp = comet.Range(voltage, voltage_stop, voltage_step)
        est = Estimate(ramp.count)
        self.process.emit("progress", *est.progress)

        logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
        for voltage in ramp:
            logging.info("set voltage: %E V", voltage)
            hvsrc_proxy.source_voltage_level = voltage
            # hvsrc_proxy.assert_success()

            time.sleep(waiting_time)

            td = time.time() - t0
            reading_current = float(hvsrc.resource.query(":READ?").split(',')[0])
            logging.info("HV Source reading: %E A", reading_current)
            self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, reading_current)

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
            est.next()
            self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
            self.process.emit("progress", *est.progress)

            # Compliance?
            compliance_tripped = hvsrc.sense.current.protection.tripped
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ComplianceError("compliance tripped")
            # hvsrc_proxy.assert_success()
            if not self.process.running:
                break

        self.process.emit("progress", 0, 0)

    def finalize(self, hvsrc):
        voltage_step = self.get_parameter('voltage_step')

        hvsrc_proxy = create_proxy(hvsrc)

        voltage = hvsrc_proxy.source_voltage_level

        self.process.emit("state", dict(
            hvsrc_voltage=voltage,
            hvsrc_current=None,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            hvsrc_proxy.source_voltage_level = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage
            ))
            time.sleep(QUICK_RAMP_DELAY)
            # hvsrc_proxy.assert_success()

        self.hvsrc_set_output_state(hvsrc, False)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc_proxy.source_voltage_level,
            hvsrc_output=self.hvsrc_get_output_state(hvsrc)
        ))

        self.process.emit("progress", 5, 5)

    def run(self):
        with self.resources.get("hvsrc") as hvsrc_res:
            hvsrc = K2410(hvsrc_res)
            super().run(hvsrc=hvsrc)

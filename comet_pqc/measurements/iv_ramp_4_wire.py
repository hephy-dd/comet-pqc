import datetime
import logging
import time
import os
import re

import comet

from ..driver import K2657A
from ..utils import auto_unit
from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["IVRamp4WireMeasurement"]

def check_error(hvsrc):
    if hvsrc.errorqueue.count:
        error = hvsrc.errorqueue.next()
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRamp4WireMeasurement(MatrixMeasurement):
    """IV ramp 4wire with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start current
    * ramps to end current
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_4_wire"

    default_hvsrc_sense_mode = "remote"
    default_hvsrc_filter_enable = False
    default_hvsrc_filter_count = 10
    default_hvsrc_filter_type = "repeat"

    def env_detect_model(self, env):
        try:
            env_idn = env.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access Environment Box", env.resource_name, e)
        logging.info("Detected Environment Box: %s", env_idn)
        # TODO
        self.process.emit("state", dict(
            env_model=env_idn
        ))

    def initialize(self, hvsrc):
        self.process.emit("progress", 0, 5)

        parameters = self.measurement_item.parameters
        current_start = parameters.get("current_start").to("A").m
        current_step = parameters.get("current_step").to("A").m
        waiting_time = parameters.get("waiting_time").to("s").m
        hvsrc_voltage_compliance = parameters.get("hvsrc_voltage_compliance").to("V").m
        hvsrc_sense_mode = parameters.get("hvsrc_sense_mode", self.default_hvsrc_sense_mode)
        hvsrc_filter_enable = bool(parameters.get("hvsrc_filter_enable", self.default_hvsrc_filter_enable))
        hvsrc_filter_count = int(parameters.get("hvsrc_filter_count", self.default_hvsrc_filter_count))
        hvsrc_filter_type = parameters.get("hvsrc_filter_type", self.default_hvsrc_filter_type)

        hvsrc_idn = hvsrc.identification
        logging.info("Detected HVSource: %s", hvsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', hvsrc_idn, re.IGNORECASE).groups()
        hvsrc_model = ''.join(result) or None

        self.process.emit("progress", 1, 5)

        if self.process.get("use_environ"):
            with self.resources.get("environ") as environ:
                self.env_detect_model(environ)

        self.process.emit("progress", 2, 5)

        self.process.emit("state", dict(
            hvsrc_model=hvsrc_model,
            hvsrc_voltage=hvsrc.source.levelv,
            hvsrc_current=hvsrc.source.leveli,
            hvsrc_output=hvsrc.source.output
        ))

        # Beeper off
        hvsrc.reset()
        hvsrc.clear()
        hvsrc.beeper.enable = False
        check_error(hvsrc)

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.levelv,
            hvsrc_current=hvsrc.source.leveli,
            hvsrc_output=hvsrc.source.output
        ))

        # set sense mode
        logging.info("set sense mode: '%s'", hvsrc_sense_mode)
        if hvsrc_sense_mode == "remote":
            hvsrc.sense = 'REMOTE'
        elif hvsrc_sense_mode == "local":
            hvsrc.sense = 'LOCAL'
        else:
            raise ValueError(f"invalid sense mode: {hvsrc_sense_mode}")
        check_error(hvsrc)

        # Current source
        hvsrc.source.func = 'DCAMPS'
        check_error(hvsrc)

        # Compliance
        logging.info("set compliance: %E V", hvsrc_voltage_compliance)
        hvsrc.source.limitv = hvsrc_voltage_compliance
        check_error(hvsrc)

        # Range
        # TODO

        # Filter
        hvsrc.measure.filter.count = hvsrc_filter_count
        check_error(hvsrc)

        if hvsrc_filter_type == "repeat":
            hvsrc.measure.filter.type = 'REPEAT'
        elif hvsrc_filter_type == "moving":
            hvsrc.measure.filter.type = 'MOVING'
        check_error(hvsrc)

        hvsrc.measure.filter.enable = hvsrc_filter_enable
        check_error(hvsrc)

        self.process.emit("progress", 1, 5)

        # Enable output
        hvsrc.source.leveli = 0
        check_error(hvsrc)
        hvsrc.source.output = 'ON'
        check_error(hvsrc)
        time.sleep(.100)

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.source.output
        ))

        self.process.emit("progress", 2, 5)

        if self.process.running:

            current = hvsrc.source.leveli

            logging.info("ramp to start current: from %E A to %E A with step %E A", current, current_start, current_step)
            for current in comet.Range(current, current_start, current_step):
                logging.info("set current: %E A", current)
                self.process.emit("message", "Ramp to start... {}".format(auto_unit(current, "A")))
                hvsrc.source.leveli = current
                # check_error(hvsrc)
                time.sleep(.100)
                time.sleep(waiting_time)

                self.process.emit("state", dict(
                    hvsrc_current=current,
                ))
                # Compliance?
                compliance_tripped = hvsrc.source.compliance
                if compliance_tripped:
                    logging.error("HVSource in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 3, 5)

    def measure(self, hvsrc):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_start = parameters.get("current_start").to("A").m
        current_step = parameters.get("current_step").to("A").m
        current_stop = parameters.get("current_stop").to("A").m
        waiting_time = parameters.get("waiting_time").to("s").m
        hvsrc_voltage_compliance = parameters.get("hvsrc_voltage_compliance").to("V").m

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("current", "E")
            fmt.add_column("voltage_hvsrc", "E")
            fmt.add_column("temperature_box", "E")
            fmt.add_column("temperature_chuck", "E")
            fmt.add_column("humidity_box", "E")

            # Write meta data
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("current_start", f"{current_start:G} A")
            fmt.write_meta("current_stop", f"{current_stop:G} A")
            fmt.write_meta("current_step", f"{current_step:G} A")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("hvsrc_voltage_compliance", f"{hvsrc_voltage_compliance:G} V")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            current = hvsrc.source.leveli

            ramp = comet.Range(current, current_stop, current_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            logging.info("ramp to end current: from %E A to %E A with step %E A", current, ramp.end, ramp.step)
            for current in ramp:
                logging.info("set current: %E A", current)
                hvsrc.clear()
                hvsrc.source.leveli = current
                time.sleep(.100)
                # check_error(hvsrc)
                dt = time.time() - t0

                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.emit("message", "Elapsed {} | Remaining {} | {}".format(elapsed, remaining, auto_unit(current, "A")))
                self.process.emit("progress", *est.progress)

                # read HVSource
                hvsrc_reading = hvsrc.measure.v()
                logging.info("HVSource reading: %E V", hvsrc_reading)
                self.process.emit("reading", "hvsrc", abs(current) if ramp.step < 0 else current, hvsrc_reading)

                self.process.emit("update", )
                self.process.emit("state", dict(
                    hvsrc_current=current,
                    hvsrc_voltage=hvsrc_reading
                ))

                # Environment
                if self.process.get("use_environ"):
                    with self.resources.get("environ") as environ:
                        pc_data = environ.query("GET:PC_DATA ?").split(",")
                    temperature_box = float(pc_data[2])
                    logging.info("temperature box: %s degC", temperature_box)
                    temperature_chuck = float(pc_data[33])
                    logging.info("temperature chuck: %s degC", temperature_chuck)
                    humidity_box = float(pc_data[1])
                    logging.info("humidity box: %s degC", humidity_box)
                else:
                    temperature_box = float('nan')
                    temperature_chuck = float('nan')
                    humidity_box = float('nan')

                self.process.emit("state", dict(
                    env_chuck_temperature=temperature_chuck,
                    env_box_temperature=temperature_box,
                    env_box_humidity=humidity_box
                ))

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    current=current,
                    voltage_hvsrc=hvsrc_reading,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                # Compliance?
                compliance_tripped = hvsrc.source.compliance
                if compliance_tripped:
                    logging.error("HVSource in compliance")
                    raise ValueError("compliance tripped")
                # check_error(hvsrc)
                if not self.process.running:
                    break

        self.process.emit("progress", 4, 5)

    def finalize(self, hvsrc):
        self.process.emit("state", dict(
            hvsrc_voltage=None
        ))

        parameters = self.measurement_item.parameters
        current_step = parameters.get("current_step").to("A").m
        current = hvsrc.source.leveli

        logging.info("ramp to zero: from %E A to %E A with step %E A", current, 0, current_step)
        for current in comet.Range(current, 0, current_step):
            logging.info("set current: %E A", current)
            self.process.emit("message", "Ramp to zero... {}".format(auto_unit(current, "A")))
            hvsrc.source.leveli = current
            time.sleep(.100)
            # check_error(hvsrc)
            self.process.emit("state", dict(
                hvsrc_current=current,
            ))

        hvsrc.source.output = 'OFF'
        check_error(hvsrc)

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.source.output,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("hvsrc") as hvsrc_res:
            hvsrc = K2657A(hvsrc_res)
            try:
                self.initialize(hvsrc)
                self.measure(hvsrc)
            finally:
                self.finalize(hvsrc)

import datetime
import logging
import time
import os
import re

import comet

from ..driver import K2657A
from ..utils import format_metric
from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

__all__ = ["IVRamp4WireMeasurement"]

def check_error(vsrc):
    if vsrc.errorqueue.count:
        error = vsrc.errorqueue.next()
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

    default_vsrc_sense_mode = "remote"
    default_vsrc_filter_enable = False
    default_vsrc_filter_count = 10
    default_vsrc_filter_type = "repeat"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('current_start', unit='A', required=True)
        self.register_parameter('current_stop', unit='A', required=True)
        self.register_parameter('current_step', unit='A', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('vsrc_voltage_compliance', unit='V', required=True)
        self.register_parameter('vsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('vsrc_filter_enable', False, type=bool)
        self.register_parameter('vsrc_filter_count', 10, type=int)
        self.register_parameter('vsrc_filter_type','repeat', values=('repeat', 'moving'))

    def initialize(self, vsrc):
        self.process.emit("progress", 0, 5)

        current_start = self.get_parameter('current_start')
        current_step = self.get_parameter('current_step')
        waiting_time = self.get_parameter('waiting_time')
        vsrc_voltage_compliance = self.get_parameter('vsrc_voltage_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        self.process.emit("progress", 1, 5)

        self.process.emit("progress", 2, 5)

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.levelv,
            vsrc_current=vsrc.source.leveli,
            vsrc_output=vsrc.source.output
        ))

        # Beeper off
        vsrc.reset()
        vsrc.clear()
        vsrc.beeper.enable = False
        check_error(vsrc)

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.levelv,
            vsrc_current=vsrc.source.leveli,
            vsrc_output=vsrc.source.output
        ))

        # set sense mode
        logging.info("set sense mode: '%s'", vsrc_sense_mode)
        if vsrc_sense_mode == "remote":
            vsrc.sense = 'REMOTE'
        elif vsrc_sense_mode == "local":
            vsrc.sense = 'LOCAL'
        else:
            raise ValueError(f"invalid sense mode: {vsrc_sense_mode}")
        check_error(vsrc)

        # Current source
        vsrc.source.func = 'DCAMPS'
        check_error(vsrc)

        # Compliance
        logging.info("set compliance: %E V", vsrc_voltage_compliance)
        vsrc.source.limitv = vsrc_voltage_compliance
        check_error(vsrc)

        # Range
        # TODO

        # Filter
        vsrc.measure.filter.count = vsrc_filter_count
        check_error(vsrc)

        if vsrc_filter_type == "repeat":
            vsrc.measure.filter.type = 'REPEAT'
        elif vsrc_filter_type == "moving":
            vsrc.measure.filter.type = 'MOVING'
        check_error(vsrc)

        vsrc.measure.filter.enable = vsrc_filter_enable
        check_error(vsrc)

        self.process.emit("progress", 1, 5)

        # Enable output
        vsrc.source.leveli = 0
        check_error(vsrc)
        vsrc.source.output = 'ON'
        check_error(vsrc)
        time.sleep(.100)

        self.process.emit("state", dict(
            vsrc_output=vsrc.source.output
        ))

        self.process.emit("progress", 2, 5)

        if self.process.running:

            current = vsrc.source.leveli

            logging.info("ramp to start current: from %E A to %E A with step %E A", current, current_start, current_step)
            for current in comet.Range(current, current_start, current_step):
                logging.info("set current: %E A", current)
                self.process.emit("message", "Ramp to start... {}".format(format_metric(current, "A")))
                vsrc.source.leveli = current
                # check_error(vsrc)
                time.sleep(QUICK_RAMP_DELAY)

                self.process.emit("state", dict(
                    vsrc_current=current,
                ))
                # Compliance?
                compliance_tripped = vsrc.source.compliance
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 3, 5)

    def measure(self, vsrc):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        current_start = self.get_parameter('current_start')
        current_step = self.get_parameter('current_step')
        current_stop = self.get_parameter('current_stop')
        waiting_time = self.get_parameter('waiting_time')
        vsrc_voltage_compliance = self.get_parameter('vsrc_voltage_compliance')

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f", unit="s")
            fmt.add_column("current", "E", unit="A")
            fmt.add_column("voltage_vsrc", "E", unit="V")
            fmt.add_column("temperature_box", "E", unit="degC")
            fmt.add_column("temperature_chuck", "E", unit="degC")
            fmt.add_column("humidity_box", "E", unit="%")

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
            fmt.write_meta("vsrc_voltage_compliance", f"{vsrc_voltage_compliance:G} V")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            current = vsrc.source.leveli

            ramp = comet.Range(current, current_stop, current_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            logging.info("ramp to end current: from %E A to %E A with step %E A", current, ramp.end, ramp.step)
            for current in ramp:
                logging.info("set current: %E A", current)
                vsrc.clear()
                vsrc.source.leveli = current
                self.process.emit("state", dict(
                    vsrc_current=current,
                ))

                time.sleep(waiting_time)
                # check_error(vsrc)
                dt = time.time() - t0

                est.next()
                self.process.emit("message", "{} | V Source {}".format(format_estimate(est), format_metric(current, "A")))
                self.process.emit("progress", *est.progress)

                # read V Source
                vsrc_reading = vsrc.measure.v()
                logging.info("V Source reading: %E V", vsrc_reading)
                self.process.emit("reading", "vsrc", abs(current) if ramp.step < 0 else current, vsrc_reading)

                self.process.emit("update")
                self.process.emit("state", dict(
                    vsrc_voltage=vsrc_reading
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
                    voltage_vsrc=vsrc_reading,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()

                # Compliance?
                compliance_tripped = vsrc.source.compliance
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("compliance tripped")
                # check_error(vsrc)
                if not self.process.running:
                    break

        self.process.emit("progress", 4, 5)

    def finalize(self, vsrc):
        self.process.emit("state", dict(
            vsrc_voltage=None
        ))

        current_step = self.get_parameter('current_step')
        current = vsrc.source.leveli

        logging.info("ramp to zero: from %E A to %E A with step %E A", current, 0, current_step)
        for current in comet.Range(current, 0, current_step):
            logging.info("set current: %E A", current)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(current, "A")))
            vsrc.source.leveli = current
            # check_error(vsrc)
            self.process.emit("state", dict(
                vsrc_current=current,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        vsrc.source.output = 'OFF'
        check_error(vsrc)

        self.process.emit("state", dict(
            vsrc_output=vsrc.source.output,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 5, 5)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            vsrc = K2657A(vsrc_res)
            try:
                self.initialize(vsrc)
                self.measure(vsrc)
            finally:
                self.finalize(vsrc)

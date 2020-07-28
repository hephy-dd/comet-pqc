import logging
import datetime
import time
import os
import re

import comet
from comet.driver.keysight import E4980A

from ..driver import K2410
from ..utils import format_metric
from ..formatter import PQCFormatter
from ..estimate import Estimate
from ..benchmark import Benchmark

from .matrix import MatrixMeasurement
from .measurement import HVSourceMixin
from .measurement import LCRMixin
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

__all__ = ["CVRampMeasurement"]

class CVRampMeasurement(MatrixMeasurement, HVSourceMixin, LCRMixin):
    """CV ramp measurement."""

    type = "cv_ramp"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('bias_voltage_start', unit='V', required=True)
        self.register_parameter('bias_voltage_stop', unit='V', required=True)
        self.register_parameter('bias_voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_hvsource()
        self.register_lcr()

    def quick_ramp_zero(self, hvsrc):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)

        bias_voltage_step = self.get_parameter('bias_voltage_step')

        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state
        ))
        if hvsrc_output_state:
            hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)
            ramp = comet.Range(hvsrc_voltage_level, 0, bias_voltage_step)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, ramp.count)
                self.hvsrc_set_voltage_level(hvsrc, voltage)
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage
                ))
                time.sleep(QUICK_RAMP_DELAY)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state
        ))
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def initialize(self, hvsrc, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 1, 6)

        # Initialize HV Source

        # Bring down HV Source voltage if output enabeled
        # Prevents a voltage jump for at device reset.
        self.quick_ramp_zero(hvsrc)
        self.hvsrc_set_output_state(hvsrc, False)
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 2, 6)

        self.hvsrc_reset(hvsrc)
        self.process.emit("progress", 3, 6)

        self.hvsrc_setup(hvsrc)
        self.process.emit("progress", 4, 6)

        self.hvsrc_set_output_state(hvsrc, True)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state,
        ))

        # Initialize LCR

        self.lcr_reset(lcr)
        self.process.emit("progress", 5, 6)

        self.lcr_setup(lcr)
        self.process.emit("progress", 6, 6)

    def measure(self, hvsrc, lcr):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        bias_voltage_start = self.get_parameter('bias_voltage_start')
        bias_voltage_step = self.get_parameter('bias_voltage_step')
        bias_voltage_stop = self.get_parameter('bias_voltage_stop')
        waiting_time = self.get_parameter('waiting_time')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        lcr_soft_filter = self.get_parameter('lcr_soft_filter')
        lcr_frequency = self.get_parameter('lcr_frequency')
        lcr_amplitude = self.get_parameter('lcr_amplitude')

        # Ramp to start voltage

        hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, bias_voltage_start, bias_voltage_step)
        for voltage in comet.Range(hvsrc_voltage_level, bias_voltage_start, bias_voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            self.hvsrc_set_voltage_level(hvsrc, voltage)
            time.sleep(QUICK_RAMP_DELAY)
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            # Compliance?
            compliance_tripped = self.hvsrc_compliance_tripped(hvsrc)
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ValueError("compliance tripped!")

            if not self.process.running:
                break

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f", unit="s")
            fmt.add_column("voltage_hvsrc", "E", unit="V")
            fmt.add_column("current_hvsrc", "E", unit="A")
            fmt.add_column("capacitance", "E", unit="F")
            fmt.add_column("capacitance2", "E", unit="1")
            fmt.add_column("resistance", "E", unit="Ohm")
            fmt.add_column("temperature_box", "E", unit="degC")
            fmt.add_column("temperature_chuck", "E", unit="degC")
            fmt.add_column("humidity_box", "E", unit="%")

            # Write meta data
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("bias_voltage_start", f"{bias_voltage_start:G} V")
            fmt.write_meta("bias_voltage_stop", f"{bias_voltage_stop:G} V")
            fmt.write_meta("bias_voltage_step", f"{bias_voltage_step:G} V")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
            fmt.write_meta("ac_frequency", f"{lcr_frequency:G} Hz")
            fmt.write_meta("ac_amplitude", f"{lcr_amplitude:G} V")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)

            ramp = comet.Range(hvsrc_voltage_level, bias_voltage_stop, bias_voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            self.hvsrc_safe_write(hvsrc, "*CLS")
            # HV Source reading format: CURR
            self.hvsrc_safe_write(hvsrc, ":FORM:ELEM CURR")

            benchmark_step = Benchmark("Single_Step")
            benchmark_lcr = Benchmark("Read_LCR")
            benchmark_hvsrc = Benchmark("Read_HV_Source")
            benchmark_environ = Benchmark("Read_Environment")

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", hvsrc_voltage_level, ramp.end, ramp.step)
            for voltage in ramp:
                with benchmark_step:
                    self.hvsrc_set_voltage_level(hvsrc, voltage)

                    # Delay
                    time.sleep(waiting_time)

                    # hvsrc_voltage_level = self.hvsrc_get_voltage_level(hvsrc)
                    dt = time.time() - t0
                    est.next()
                    self.process.emit("message", "{} | HV Source {}".format(format_estimate(est), format_metric(voltage, "V")))
                    self.process.emit("progress", *est.progress)

                    # read LCR, for CpRp -> prim: Cp, sec: Rp
                    with benchmark_lcr:
                        if lcr_soft_filter:
                            lcr_prim, lcr_sec = self.lcr_acquire_filter_reading(lcr)
                        else:
                            lcr_prim, lcr_sec = self.lcr_acquire_reading(lcr)
                        try:
                            lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                        except ZeroDivisionError:
                            lcr_prim2 = 0.0

                    # read HV Source
                    with benchmark_hvsrc:
                        hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                    logging.info("HV Source reading: %E", hvsrc_reading)

                    self.process.emit("reading", "lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                    self.process.emit("reading", "lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

                    self.process.emit("update", )
                    self.process.emit("state", dict(
                        hvsrc_voltage=voltage,
                        hvsrc_current=hvsrc_reading
                    ))

                    # Environment
                    if self.process.get("use_environ"):
                        with benchmark_environ:
                            with self.resources.get("environ") as env:
                                pc_data = env.query("GET:PC_DATA ?").split(",")
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
                        voltage_hvsrc=voltage,
                        current_hvsrc=hvsrc_reading,
                        capacitance=lcr_prim,
                        capacitance2=lcr_prim2,
                        resistance=lcr_sec,
                        temperature_box=temperature_box,
                        temperature_chuck=temperature_chuck,
                        humidity_box=humidity_box
                    ))
                    fmt.flush()

                    # Compliance?
                    compliance_tripped = self.hvsrc_compliance_tripped(hvsrc)
                    if compliance_tripped:
                        logging.error("HV Source in compliance")
                        raise ValueError("compliance tripped!")

                    if not self.process.running:
                        break

            logging.info(benchmark_step)
            logging.info(benchmark_lcr)
            logging.info(benchmark_hvsrc)
            logging.info(benchmark_environ)

    def finalize(self, hvsrc, lcr):
        self.process.emit("progress", 1, 2)
        self.process.emit("state", dict(
            hvsrc_current=None,
        ))

        self.quick_ramp_zero(hvsrc)
        self.hvsrc_set_output_state(hvsrc, False)
        hvsrc_output_state = self.hvsrc_get_output_state(hvsrc)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc_output_state,
        ))

        self.process.emit("state", dict(
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def code(self, *args, **kwargs):
        with self.resources.get("hvsrc") as hvsrc_res:
            with self.resources.get("lcr") as lcr_res:
                hvsrc = K2410(hvsrc_res)
                lcr = E4980A(lcr_res)
                try:
                    self.initialize(hvsrc, lcr)
                    self.measure(hvsrc, lcr)
                finally:
                    self.finalize(hvsrc, lcr)

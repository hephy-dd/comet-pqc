import datetime
import logging
import time
import os

import comet

from comet.driver.keithley import K2410
from comet.driver.keithley import K2657A

from ..utils import format_metric
from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement
from .measurement import ComplianceError
from .measurement import EnvironmentMixin
from .measurement import format_estimate
from .measurement import QUICK_RAMP_DELAY

__all__ = ["IVRampBiasMeasurement"]

def check_error(vsrc):
    if vsrc.errorqueue.count:
        error = vsrc.errorqueue.next()
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampBiasMeasurement(MatrixMeasurement, EnvironmentMixin):
    """Bias IV ramp measurement."""

    type = "iv_ramp_bias"

    def __init__(self, process):
        super().__init__(process)
        self.register_parameter('voltage_start', unit='V', required=True)
        self.register_parameter('voltage_stop', unit='V', required=True)
        self.register_parameter('voltage_step', unit='V', required=True)
        self.register_parameter('waiting_time', unit='s', required=True)
        self.register_parameter('bias_voltage', unit='V', required=True)
        self.register_parameter('bias_mode', 'constant', values=('constant', 'offset'))
        self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('hvsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('hvsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('hvsrc_filter_enable', False, type=bool)
        self.register_parameter('hvsrc_filter_count', 10, type=int)
        self.register_parameter('hvsrc_filter_type', 'repeat', values=('repeat', 'moving'))
        self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('vsrc_filter_enable', False, type=bool)
        self.register_parameter('vsrc_filter_count', 10, type=int)
        self.register_parameter('vsrc_filter_type','repeat', values=('repeat', 'moving'))
        self.register_environment()

    def initialize(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 5)
        self.process.emit("message", "Ramp to start...")

        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_filter_enable = self.get_parameter('hvsrc_filter_enable')
        hvsrc_filter_count = self.get_parameter('hvsrc_filter_count')
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        # Initialize HV Source

        hvsrc.reset()
        hvsrc.clear()
        hvsrc.system.beeper.status = False

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.voltage.level,
            hvsrc_current=None,
            hvsrc_output=hvsrc.output
        ))

        # Select rear terminal
        logging.info("set route termination: '%s'", hvsrc_route_termination)
        if hvsrc_route_termination == "front":
            hvsrc.resource.write(":ROUT:TERM FRONT")
        elif hvsrc_route_termination == "rear":
            hvsrc.resource.write(":ROUT:TERM REAR")
        hvsrc.resource.query("*OPC?")

        # set sense mode
        logging.info("set sense mode: '%s'", hvsrc_sense_mode)
        if hvsrc_sense_mode == "remote":
            hvsrc.resource.write(":SYST:RSEN ON")
        elif hvsrc_sense_mode == "local":
            hvsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {hvsrc_sense_mode}")
        hvsrc.resource.query("*OPC?")

        # Compliance
        logging.info("set compliance: %E A", hvsrc_current_compliance)
        hvsrc.sense.current.protection.level = hvsrc_current_compliance

        # Range
        current_range = 1.05E-6
        hvsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        hvsrc.resource.query("*OPC?")
        hvsrc.resource.write(":SENS:VOLT:RANG:AUTO ON")
        hvsrc.resource.query("*OPC?")

        # Filter
        hvsrc.resource.write(f":SENS:AVER:COUN {hvsrc_filter_count:d}")
        hvsrc.resource.query("*OPC?")

        if hvsrc_filter_type == "repeat":
            hvsrc.resource.write(":SENS:AVER:TCON REP")
        elif hvsrc_filter_type == "moving":
            hvsrc.resource.write(":SENS:AVER:TCON MOV")
        hvsrc.resource.query("*OPC?")

        if hvsrc_filter_enable:
            hvsrc.resource.write(":SENS:AVER:STATE ON")
        else:
            hvsrc.resource.write(":SENS:AVER:STATE OFF")
        hvsrc.resource.query("*OPC?")

        if not self.process.running:
            return

        # Initialize V Source

        vsrc.reset()
        vsrc.clear()
        vsrc.beeper.enable = False

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.levelv,
            vsrc_current=None,
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
        vsrc.source.func = 'DCVOLTS'
        check_error(vsrc)

        # Compliance
        logging.info("set compliance: %E A", vsrc_current_compliance)
        vsrc.source.limiti = vsrc_current_compliance
        check_error(vsrc)
        logging.info("compliance: %E A", vsrc.source.limiti)

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

        if not self.process.running:
            return

        # Output enable

        hvsrc.output = True
        time.sleep(.100)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output
        ))
        vsrc.source.output = 'ON'
        time.sleep(.100)
        self.process.emit("state", dict(
            vsrc_output=vsrc.source.output
        ))

        # Ramp HV Spource to bias voltage
        voltage = vsrc.source.levelv

        logging.info("ramp to bias voltage: from %E V to %E V with step %E V", voltage, bias_voltage, 1.0)
        for voltage in comet.Range(voltage, bias_voltage, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp to bias... {}".format(format_metric(voltage, "V")))
            vsrc.source.levelv = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

            # Compliance?
            compliance_tripped = vsrc.source.compliance
            if compliance_tripped:
                logging.error("V Source in compliance")
                raise ComplianceError("V Source compliance tripped")

            if not self.process.running:
                break

        # Ramp HV Source to start voltage
        voltage = hvsrc.source.voltage.level

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, 1.0)
        for voltage in comet.Range(voltage, voltage_start, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(format_metric(voltage, "V")))
            hvsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            # check_error(hvsrc)
            time.sleep(QUICK_RAMP_DELAY)

            # Compliance?
            compliance_tripped = hvsrc.sense.current.protection.tripped
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ComplianceError("HV Source compliance tripped")

            if not self.process.running:
                break

        self.process.emit("progress", 5, 5)

    def measure(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to...")

        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        voltage_start = self.get_parameter('voltage_start')
        voltage_stop = self.get_parameter('voltage_stop')
        voltage_step = self.get_parameter('voltage_step')
        waiting_time = self.get_parameter('waiting_time')
        bias_voltage = self.get_parameter('bias_voltage')
        bias_mode = self.get_parameter('bias_mode')
        hvsrc_current_compliance = self.get_parameter('hvsrc_current_compliance')
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_filter_enable = bool(self.get_parameter('hvsrc_filter_enable'))
        hvsrc_filter_count = int(self.get_parameter('hvsrc_filter_count'))
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')
        vsrc_current_compliance = self.get_parameter('vsrc_current_compliance')
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = bool(self.get_parameter('vsrc_filter_enable'))
        vsrc_filter_count = int(self.get_parameter('vsrc_filter_count'))
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        if not self.process.running:
            return

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f", unit="s")
            fmt.add_column("voltage", "E", unit="V")
            fmt.add_column("current", "E", unit="A")
            fmt.add_column("bias_voltage", "E", unit="V")
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
            fmt.write_meta("voltage_start", f"{voltage_start:G} V")
            fmt.write_meta("voltage_stop", f"{voltage_stop:G} V")
            fmt.write_meta("voltage_step", f"{voltage_step:G} V")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("bias_voltage", f"{bias_voltage:G} V")
            fmt.write_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
            fmt.write_meta("hvsrc_sense_mode", hvsrc_sense_mode)
            fmt.write_meta("hvsrc_route_termination", hvsrc_route_termination)
            fmt.write_meta("hvsrc_filter_enable", format(hvsrc_filter_enable).lower())
            fmt.write_meta("hvsrc_filter_count", format(hvsrc_filter_count))
            fmt.write_meta("hvsrc_filter_type", hvsrc_filter_type)
            fmt.write_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
            fmt.write_meta("vsrc_sense_mode", vsrc_sense_mode)
            fmt.write_meta("vsrc_filter_enable", format(vsrc_filter_enable).lower())
            fmt.write_meta("vsrc_filter_count", format(vsrc_filter_count))
            fmt.write_meta("vsrc_filter_type", vsrc_filter_type)
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            # HV Source reading format: CURR
            hvsrc.resource.write(":FORM:ELEM CURR")
            hvsrc.resource.query("*OPC?")

            voltage = hvsrc.source.voltage.level

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                hvsrc.source.voltage.level = voltage
                self.process.emit("state", dict(
                    hvsrc_voltage=voltage,
                ))
                # Move bias TODO
                if bias_mode == "offset":
                    bias_voltage += abs(ramp.step) if ramp.begin <= ramp.end else -abs(ramp.step)
                    logging.info("set bias voltage: %E V", bias_voltage)
                    vsrc.source.levelv = bias_voltage
                    self.process.emit("state", dict(
                        vsrc_voltage=bias_voltage,
                    ))

                time.sleep(waiting_time)

                dt = time.time() - t0

                est.next()
                self.process.emit("message", "{} | HV Source {} | Bias {}".format(format_estimate(est), format_metric(voltage, "V"), format_metric(bias_voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read V Source
                vsrc_reading = vsrc.measure.i()
                logging.info("V Source reading: %E A", vsrc_reading)
                self.process.emit("reading", "vsrc", abs(voltage) if ramp.step < 0 else voltage, vsrc_reading)

                # read HV Source
                hvsrc_reading = float(hvsrc.resource.query(":READ?").split(',')[0])
                logging.info("HV Source bias reading: %E A", hvsrc_reading)

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

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    voltage=voltage,
                    current=vsrc_reading,
                    bias_voltage=bias_voltage,
                    temperature_box=self.environment_temperature_box,
                    temperature_chuck=self.environment_temperature_chuck,
                    humidity_box=self.environment_humidity_box
                ))
                fmt.flush()

                # Compliance?
                compliance_tripped = hvsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ComplianceError("HV Source compliance tripped")
                compliance_tripped = vsrc.source.compliance
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ComplianceError("V Source compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 2, 2)

    def finalize(self, hvsrc, vsrc):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to zero...")

        voltage_step = self.get_parameter('voltage_step')

        voltage = hvsrc.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, 1.0)
        for voltage in comet.Range(voltage, 0, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(format_metric(voltage, "V")))
            hvsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        bias_voltage = vsrc.source.levelv

        logging.info("ramp bias to zero: from %E V to %E V with step %E V", bias_voltage, 0, 1.0)
        for voltage in comet.Range(bias_voltage, 0, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp bias to zero... {}".format(format_metric(voltage, "V")))
            vsrc.source.levelv = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(QUICK_RAMP_DELAY)

        hvsrc.output = False
        vsrc.source.output = 'OFF'

        self.process.emit("state", dict(
            hvsrc_output=hvsrc.output,
            hvsrc_voltage=None,
            hvsrc_current=None,
            vsrc_output=vsrc.source.output,
            vsrc_voltage=None,
            vsrc_current=None,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def code(self, *args, **kwargs):
        with self.resources.get("hvsrc") as hvsrc_res:
            with self.resources.get("vsrc") as vsrc_res:
                hvsrc = K2410(hvsrc_res)
                vsrc = K2657A(vsrc_res)
                try:
                    self.initialize(hvsrc, vsrc)
                    self.measure(hvsrc, vsrc)
                finally:
                    self.finalize(hvsrc, vsrc)

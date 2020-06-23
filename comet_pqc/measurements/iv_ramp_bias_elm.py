import datetime
import logging
import time
import os
import re

import comet
from comet.driver.keithley import K6517B

from ..driver import K2410
from ..driver import K2657A
from ..utils import auto_unit
from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["IVRampBiasElmMeasurement"]

def check_error(hvsrc):
    if hvsrc.errorqueue.count:
        error = hvsrc.errorqueue.next()
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampBiasElmMeasurement(MatrixMeasurement):
    """Bias IV ramp measurement."""

    type = "iv_ramp_bias_elm"

    default_bias_mode = "constant"
    default_vsrc_sense_mode = "local"
    default_vsrc_route_termination = "rear"
    default_vsrc_filter_enable = False
    default_vsrc_filter_count = 10
    default_vsrc_filter_type = "repeat"
    default_hvsrc_sense_mode = "local"
    default_hvsrc_filter_enable = False
    default_hvsrc_filter_count = 10
    default_hvsrc_filter_type = "repeat"
    default_elm_filter_enable = False
    default_elm_filter_count = 10
    default_elm_filter_type = "repeat"
    default_elm_zero_correction = False
    default_elm_integration_rate = 50
    default_elm_autorange_current_minimum = comet.ureg("20 pA")
    default_elm_autorange_current_maximum = comet.ureg("20 mA")

    def initialize(self, vsrc, hvsrc, elm):
        self.process.emit("progress", 1, 5)
        self.process.emit("message", "Ramp to start...")

        parameters = self.measurement_item.parameters
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_stop = parameters.get("voltage_stop").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        bias_voltage = parameters.get("bias_voltage").to("V").m
        bias_mode = parameters.get("bias_mode", self.default_bias_mode)
        vsrc_current_compliance = parameters.get("vsrc_current_compliance").to("A").m
        vsrc_sense_mode = parameters.get("vsrc_sense_mode", self.default_vsrc_sense_mode)
        vsrc_route_termination = parameters.get("vsrc_route_termination", self.default_vsrc_route_termination)
        vsrc_filter_enable = bool(parameters.get("vsrc_filter_enable", self.default_vsrc_filter_enable))
        vsrc_filter_count = int(parameters.get("vsrc_filter_count", self.default_vsrc_filter_count))
        vsrc_filter_type = parameters.get("vsrc_filter_type", self.default_vsrc_filter_type)
        hvsrc_current_compliance = parameters.get("hvsrc_current_compliance").to("A").m
        hvsrc_sense_mode = parameters.get("hvsrc_sense_mode", self.default_hvsrc_sense_mode)
        hvsrc_filter_enable = bool(parameters.get("hvsrc_filter_enable", self.default_hvsrc_filter_enable))
        hvsrc_filter_count = int(parameters.get("hvsrc_filter_count", self.default_hvsrc_filter_count))
        hvsrc_filter_type = parameters.get("hvsrc_filter_type", self.default_hvsrc_filter_type)
        elm_filter_enable = bool(parameters.get("elm_filter_enable", self.default_elm_filter_enable))
        elm_filter_count = int(parameters.get("elm_filter_count", self.default_elm_filter_count))
        elm_filter_type = parameters.get("elm_filter_type", self.default_elm_filter_type)
        elm_zero_correction = bool(parameters.get("elm_zero_correction", self.default_elm_zero_correction))
        elm_integration_rate = int(parameters.get("elm_integration_rate", self.default_elm_integration_rate))
        elm_autorange_current_minimum = parameters.get("elm_autorange_current_minimum", self.default_elm_autorange_current_minimum).to("A").m
        elm_autorange_current_maximum = parameters.get("elm_autorange_current_maximum", self.default_elm_autorange_current_maximum).to("A").m

        vsrc_idn = vsrc.identification
        logging.info("Detected V Source: %s", vsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', vsrc_idn, re.IGNORECASE).groups()
        vsrc_model = ''.join(result) or None

        hvsrc_idn = hvsrc.identification
        logging.info("Detected HV Source: %s", hvsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', hvsrc_idn, re.IGNORECASE).groups()
        hvsrc_model = ''.join(result) or None

        elm_idn = elm.identification
        logging.info("Detected Electrometer: %s", elm_idn)
        result = re.search(r'model\s+([\d\w]+)', elm_idn, re.IGNORECASE).groups()
        elm_model = ''.join(result) or None

        self.process.emit("state", dict(
            vsrc_model=vsrc_model,
            hvsrc_model=hvsrc_model,
            elm_model=elm_model
        ))

        # Initialize V Source

        vsrc.reset()
        vsrc.clear()
        vsrc.system.beeper.status = False

        self.process.emit("state", dict(
            vsrc_voltage=vsrc.source.voltage.level,
            vsrc_current=None,
            vsrc_output=vsrc.output
        ))

        # Select rear terminal
        logging.info("set route termination: '%s'", vsrc_route_termination)
        if vsrc_route_termination == "front":
            vsrc.resource.write(":ROUT:TERM FRONT")
        elif vsrc_route_termination == "rear":
            vsrc.resource.write(":ROUT:TERM REAR")
        vsrc.resource.query("*OPC?")

        # set sense mode
        logging.info("set sense mode: '%s'", vsrc_sense_mode)
        if vsrc_sense_mode == "remote":
            vsrc.resource.write(":SYST:RSEN ON")
        elif vsrc_sense_mode == "local":
            vsrc.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {vsrc_sense_mode}")
        vsrc.resource.query("*OPC?")

        # Compliance
        logging.info("set compliance: %E A", vsrc_current_compliance)
        vsrc.sense.current.protection.level = vsrc_current_compliance

        # Range
        current_range = 1.05E-6
        vsrc.resource.write(":SENS:CURR:RANG:AUTO ON")
        vsrc.resource.query("*OPC?")
        vsrc.resource.write(":SENS:VOLT:RANG:AUTO ON")
        vsrc.resource.query("*OPC?")

        # Filter
        vsrc.resource.write(f":SENS:AVER:COUN {vsrc_filter_count:d}")
        vsrc.resource.query("*OPC?")

        if vsrc_filter_type == "repeat":
            vsrc.resource.write(":SENS:AVER:TCON REP")
        elif vsrc_filter_type == "repeat":
            vsrc.resource.write(":SENS:AVER:TCON MOV")
        vsrc.resource.query("*OPC?")

        if vsrc_filter_enable:
            vsrc.resource.write(":SENS:AVER:STATE ON")
        else:
            vsrc.resource.write(":SENS:AVER:STATE OFF")
        vsrc.resource.query("*OPC?")

        if not self.process.running:
            return

        # Initialize HV Source

        hvsrc.reset()
        hvsrc.clear()
        hvsrc.beeper.enable = False

        self.process.emit("state", dict(
            hvsrc_voltage=hvsrc.source.levelv,
            hvsrc_current=None,
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
        hvsrc.source.func = 'DCVOLTS'
        check_error(hvsrc)

        # Compliance
        logging.info("set compliance: %E A", hvsrc_current_compliance)
        hvsrc.source.limiti = hvsrc_current_compliance
        check_error(hvsrc)
        logging.info("compliance: %E A", hvsrc.source.limiti)

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

        if not self.process.running:
            return

        # Initialize Electrometer

        def elm_safe_write(message):
            """Write, wait for operation complete, test for errors."""
            elm.resource.write(message)
            elm.resource.query("*OPC?")
            code, label = elm.resource.query(":SYST:ERR?").split(",", 1)
            code = int(code)
            label = label.strip("\"")
            if code != 0:
                logging.error(f"error {code}: {label} returned by '{message}'")
                raise RuntimeError(f"error {code}: {label} returned by '{message}'")

        elm_safe_write("*RST")
        elm_safe_write("*CLS")

        # Filter
        elm_safe_write(f":SENS:CURR:AVER:COUN {elm_filter_count:d}")

        if elm_filter_type == "repeat":
            elm_safe_write(":SENS:CURR:AVER:TCON REP")
        elif elm_filter_type == "repeat":
            elm_safe_write(":SENS:CURR:AVER:TCON MOV")

        if elm_filter_enable:
            elm_safe_write(":SENS:CURR:AVER:STATE ON")
        else:
            elm_safe_write(":SENS:CURR:AVER:STATE OFF")

        nplc = elm_integration_rate / 10.
        elm_safe_write(f":SENS:CURR:NPLC {nplc:02f}")

        elm_safe_write(":SYST:ZCH ON") # enable zero check
        assert elm.resource.query(":SYST:ZCH?") == '1', "failed to enable zero check"

        elm_safe_write(":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        elm_safe_write(":SENS:CURR:RANG 20e-12") # 20pA
        if elm_zero_correction:
            elm_safe_write(":SYST:ZCOR ON") # perform zero correction
        elm_safe_write(":SENS:CURR:RANG:AUTO ON")
        elm_safe_write(f":SENS:CURR:RANG:AUTO:LLIM {elm_autorange_current_minimum:E}")
        elm_safe_write(f":SENS:CURR:RANG:AUTO:ULIM {elm_autorange_current_maximum:E}")

        elm_safe_write(":SYST:ZCH OFF") # disable zero check
        assert elm.resource.query(":SYST:ZCH?") == '0', "failed to disable zero check"

        # Output enable

        vsrc.output = True
        time.sleep(.100)
        self.process.emit("state", dict(
            vsrc_output=vsrc.output
        ))
        hvsrc.source.output = 'ON'
        time.sleep(.100)
        self.process.emit("state", dict(
            hvsrc_output=hvsrc.source.output
        ))

        # Ramp HV Spource to bias voltage
        voltage = hvsrc.source.levelv

        logging.info("ramp to bias voltage: from %E V to %E V with step %E V", voltage, bias_voltage, 1.0)
        for voltage in comet.Range(voltage, bias_voltage, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp to bias... {}".format(auto_unit(voltage, "V")))
            hvsrc.source.levelv = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(waiting_time)

            # Compliance?
            compliance_tripped = hvsrc.source.compliance
            if compliance_tripped:
                logging.error("HV Source in compliance")
                raise ValueError("HV Source compliance tripped")

            if not self.process.running:
                break

        # Ramp V Source to start voltage
        voltage = vsrc.source.voltage.level

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, 1.0)
        for voltage in comet.Range(voltage, voltage_start, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(auto_unit(voltage, "V")))
            vsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            # check_error(vsrc)
            time.sleep(waiting_time)

            # Compliance?
            compliance_tripped = vsrc.sense.current.protection.tripped
            if compliance_tripped:
                logging.error("V Source in compliance")
                raise ValueError("V Source compliance tripped")

            if not self.process.running:
                break

        self.process.emit("progress", 5, 5)

    def measure(self, vsrc, hvsrc, elm):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to...")

        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name

        parameters = self.measurement_item.parameters
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_stop = parameters.get("voltage_stop").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        bias_voltage = parameters.get("bias_voltage").to("V").m
        bias_mode = parameters.get("bias_mode", self.default_bias_mode)
        vsrc_current_compliance = parameters.get("vsrc_current_compliance").to("A").m
        vsrc_sense_mode = parameters.get("vsrc_sense_mode", self.default_vsrc_sense_mode)
        vsrc_route_termination = parameters.get("vsrc_route_termination", self.default_vsrc_route_termination)
        vsrc_filter_enable = bool(parameters.get("vsrc_filter_enable", self.default_vsrc_filter_enable))
        vsrc_filter_count = int(parameters.get("vsrc_filter_count", self.default_vsrc_filter_count))
        vsrc_filter_type = parameters.get("vsrc_filter_type", self.default_vsrc_filter_type)
        hvsrc_current_compliance = parameters.get("hvsrc_current_compliance").to("A").m
        hvsrc_sense_mode = parameters.get("hvsrc_sense_mode", self.default_hvsrc_sense_mode)
        hvsrc_filter_enable = bool(parameters.get("hvsrc_filter_enable", self.default_hvsrc_filter_enable))
        hvsrc_filter_count = int(parameters.get("hvsrc_filter_count", self.default_hvsrc_filter_count))
        hvsrc_filter_type = parameters.get("hvsrc_filter_type", self.default_hvsrc_filter_type)
        elm_filter_enable = bool(parameters.get("elm_filter_enable", self.default_elm_filter_enable))
        elm_filter_count = int(parameters.get("elm_filter_count", self.default_elm_filter_count))
        elm_filter_type = parameters.get("elm_filter_type", self.default_elm_filter_type)
        elm_zero_correction = bool(parameters.get("elm_zero_correction", self.default_elm_zero_correction))
        elm_integration_rate = int(parameters.get("elm_integration_rate", self.default_elm_integration_rate))
        elm_autorange_current_minimum = parameters.get("elm_autorange_current_minimum", self.default_elm_autorange_current_minimum).to("A").m
        elm_autorange_current_maximum = parameters.get("elm_autorange_current_maximum", self.default_elm_autorange_current_maximum).to("A").m

        if not self.process.running:
            return

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("elm_current", "E")
            fmt.add_column("hvsrc_current", "E")
            fmt.add_column("vsrc_current", "E")
            fmt.add_column("bias_voltage", "E")
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
            fmt.write_meta("voltage_start", f"{voltage_start:G} V")
            fmt.write_meta("voltage_stop", f"{voltage_stop:G} V")
            fmt.write_meta("voltage_step", f"{voltage_step:G} V")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("bias_voltage", f"{bias_voltage:G} V")
            fmt.write_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
            fmt.write_meta("vsrc_sense_mode", vsrc_sense_mode)
            fmt.write_meta("vsrc_route_termination", vsrc_route_termination)
            fmt.write_meta("vsrc_filter_enable", format(vsrc_filter_enable).lower())
            fmt.write_meta("vsrc_filter_count", format(vsrc_filter_count))
            fmt.write_meta("vsrc_filter_type", vsrc_filter_type)
            fmt.write_meta("hvsrc_current_compliance", f"{hvsrc_current_compliance:G} A")
            fmt.write_meta("hvsrc_sense_mode", hvsrc_sense_mode)
            fmt.write_meta("hvsrc_filter_enable", format(hvsrc_filter_enable).lower())
            fmt.write_meta("hvsrc_filter_count", format(hvsrc_filter_count))
            fmt.write_meta("hvsrc_filter_type", hvsrc_filter_type)
            fmt.write_meta("elm_filter_enable", format(elm_filter_enable).lower())
            fmt.write_meta("elm_filter_count", format(elm_filter_count))
            fmt.write_meta("elm_filter_type", elm_filter_type)
            fmt.write_meta("elm_zero_correction", format(elm_zero_correction))
            fmt.write_meta("elm_integration_rate", format(elm_integration_rate))
            fmt.write_meta("elm_autorange_current_minimum", format(elm_autorange_current_minimum))
            fmt.write_meta("elm_autorange_current_maximum", format(elm_autorange_current_maximum))
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            # V Source reading format: CURR
            vsrc.resource.write(":FORM:ELEM CURR")
            vsrc.resource.query("*OPC?")

            # Electrometer reading format: READ
            elm.resource.write(":FORM:ELEM READ")
            elm.resource.query("*OPC?")

            voltage = vsrc.source.voltage.level

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                vsrc.source.voltage.level = voltage
                self.process.emit("state", dict(
                    vsrc_voltage=voltage,
                ))
                # Move bias TODO
                if bias_mode == "offset":
                    bias_voltage += abs(ramp.step) if ramp.begin <= ramp.end else -abs(ramp.step)
                    logging.info("set bias voltage: %E V", bias_voltage)
                    hvsrc.source.levelv = bias_voltage
                    self.process.emit("state", dict(
                        hvsrc_voltage=bias_voltage,
                    ))
                time.sleep(.100)
                dt = time.time() - t0

                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.emit("message", "Elapsed {} | Remaining {} | {} | Bias {}".format(elapsed, remaining, auto_unit(voltage, "V"), auto_unit(bias_voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read ELM
                elm_reading = float(elm.resource.query(":READ?").split(',')[0])
                logging.info("ELM reading: %E", elm_reading)
                self.process.emit("reading", "elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                # read HV Source
                hvsrc_reading = hvsrc.measure.i()
                logging.info("HV Source reading: %E A", hvsrc_reading)
                ### self.process.emit("reading", "hvsrc", abs(voltage) if ramp.step < 0 else voltage, hvsrc_reading)

                # read V Source
                vsrc_reading = float(vsrc.resource.query(":READ?").split(',')[0])
                logging.info("V Source bias reading: %E A", vsrc_reading)
                ### self.process.emit("reading", "src", abs(voltage) if ramp.step < 0 else voltage, hvsrc_reading)

                self.process.emit("update")
                self.process.emit("state", dict(
                    elm_current=elm_reading,
                    vsrc_current=vsrc_reading,
                    hvsrc_current=hvsrc_reading,
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
                    voltage=voltage,
                    elm_current=hvsrc_reading,
                    hvsrc_current=hvsrc_reading,
                    vsrc_current=vsrc_reading,
                    bias_voltage=bias_voltage,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                # Compliance?
                compliance_tripped = vsrc.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("V Source in compliance")
                    raise ValueError("V Source compliance tripped")
                compliance_tripped = hvsrc.source.compliance
                if compliance_tripped:
                    logging.error("HV Source in compliance")
                    raise ValueError("HV Source compliance tripped")
                if not self.process.running:
                    break

        self.process.emit("progress", 2, 2)

    def finalize(self, vsrc, hvsrc, elm):
        self.process.emit("progress", 1, 2)
        self.process.emit("message", "Ramp to zero...")

        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        self.process.emit("state", dict(
            elm_current=None,
            hvsrc_current=None,
            vsrc_current=None
        ))

        parameters = self.measurement_item.parameters
        voltage_step = parameters.get("voltage_step").to("V").m

        voltage = vsrc.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, 1.0)
        for voltage in comet.Range(voltage, 0, 1.0):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to zero... {}".format(auto_unit(voltage, "V")))
            vsrc.source.voltage.level = voltage
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            time.sleep(.100)

        bias_voltage = hvsrc.source.levelv

        logging.info("ramp bias to zero: from %E V to %E V with step %E V", bias_voltage, 0, 1.0)
        for voltage in comet.Range(bias_voltage, 0, 1.0):
            logging.info("set bias voltage: %E V", voltage)
            self.process.emit("message", "Ramp bias to zero... {}".format(auto_unit(voltage, "V")))
            hvsrc.source.levelv = voltage
            self.process.emit("state", dict(
                hvsrc_voltage=voltage,
            ))
            time.sleep(.100)

        vsrc.output = False
        hvsrc.source.output = 'OFF'

        self.process.emit("state", dict(
            vsrc_output=vsrc.output,
            vsrc_voltage=None,
            vsrc_current=None,
            hvsrc_output=hvsrc.source.output,
            hvsrc_voltage=None,
            hvsrc_current=None,
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            with self.resources.get("hvsrc") as hvsrc_res:
                with self.resources.get("elm") as elm_res:
                    vsrc = K2410(vsrc_res)
                    hvsrc = K2657A(hvsrc_res)
                    elm = K6517B(elm_res)
                    try:
                        self.initialize(vsrc, hvsrc, elm)
                        self.measure(vsrc, hvsrc, elm)
                    finally:
                        self.finalize(vsrc, hvsrc, elm)

import logging
import time
import os

import comet

from ..utils import auto_step, safe_filename
from .matrix import MatrixMeasurement

__all__ = ["IVRampElmMeasurement"]

def check_error(smu):
    error = smu.system.error
    if error[0]:
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampElmMeasurement(MatrixMeasurement):
    """IV ramp with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_elm"

    def initialize(self, smu, elm):
        self.process.events.progress(0, 5)

        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        sense_mode = parameters.get("sense_mode")
        route_termination = parameters.get("route_termination")
        average_enabled = bool(parameters.get("average_enabled"))
        average_count = int(parameters.get("average_count"))
        average_type = parameters.get("average_type")
        zero_correction = parameters.get("zero_correction")
        integration_rate = parameters.get("integration_rate")

        logging.info("Using SMU: %s", smu.identification)
        logging.info("Using Electrometer: %s", elm.identification)

        # Beeper off
        smu.system.beeper.status = False
        smu.clear()
        check_error(smu)

        # Select rear terminal
        if route_termination == "front":
            smu.resource.write(":ROUT:TERM FRONT")
        elif route_termination == "rear":
            smu.resource.write(":ROUT:TERM REAR")
        smu.resource.query("*OPC?")
        check_error(smu)

        # set sense mode
        logging.info("set sense mode: '%s'", sense_mode)
        if sense_mode == "remote":
            smu.resource.write(":SYST:RSEN ON")
        elif sense_mode == "local":
            smu.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {sense_mode}")
        smu.resource.query("*OPC?")
        check_error(smu)

        # Compliance
        logging.info("set compliance: %E A", current_compliance)
        smu.sense.current.protection.level = current_compliance
        check_error(smu)

        # Range
        current_range = 1.05E-6
        smu.resource.write(":SENS:CURR:RANG:AUTO ON")
        smu.resource.query("*OPC?")
        check_error(smu)
        #smu.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #smu.resource.query("*OPC?")
        #check_error(smu)

        # Filter
        if average_enabled:
            smu.resource.write(":SENS:AVER:STATE ON")
        else:
            smu.resource.write(":SENS:AVER:STATE OFF")
        smu.resource.query("*OPC?")
        check_error(smu)
        smu.resource.write(f":SENS:AVER:COUN {average_count:d}")
        smu.resource.query("*OPC?")
        check_error(smu)
        if average_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON REP")
        elif average_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON MOV")
        smu.resource.query("*OPC?")
        check_error(smu)

        self.process.events.progress(1, 5)

        # If output enabled
        if smu.output:
            voltage = smu.source.voltage.level
            step = auto_step(voltage, 0, voltage_step)

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, step)
            for voltage in comet.Range(voltage, 0, step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
                # check_error(smu)
                time.sleep(.100)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            smu.source.voltage.level = voltage
            check_error(smu)
            smu.output = True
            check_error(smu)
            time.sleep(.100)

        self.process.events.progress(2, 5)

        if self.process.running:

            voltage = smu.source.voltage.level
            step = auto_step(voltage, voltage_start, voltage_step)

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))
            check_error(smu)

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, step)
            for voltage in comet.Range(voltage, voltage_start, step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
                # check_error(smu)
                time.sleep(.100)
                # Returns <elements> comma separated
                #values = list(map(float, smu.resource.query(":READ?").split(",")))
                #data = zip(elements, values)
                time.sleep(waiting_time)
                # Compliance?
                compliance_tripped = smu.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        def elm_safe_write(message):
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

        nplc = integration_rate / 10.
        elm_safe_write(f":SENS:VOLT:NPLC {nplc:02f}") # 20pA

        elm_safe_write(":SYST:ZCH ON") # enable zero check
        assert elm.resource.query(":SYST:ZCH?") == '1', "failed to enable zero check"

        elm_safe_write(":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        elm_safe_write(":SENS:CURR:RANG 20e-12") # 20pA
        if zero_correction:
            elm_safe_write(":SYST:ZCOR ON") # perform zero correction
        elm_safe_write(":SENS:CURR:RANG:AUTO ON")
        elm_safe_write(":SENS:CURR:RANG:AUTO:LLIM 2.000000E-11")
        elm_safe_write(":SENS:CURR:RANG:AUTO:ULIM 2.000000E-2")

        elm_safe_write(":SYST:ZCH OFF") # disable zero check
        assert elm.resource.query(":SYST:ZCH?") == '0', "failed to disable zero check"

        self.process.events.progress(3, 5)

    def measure(self, smu, elm):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name =  self.measurement_item.contact.name
        measurement_name =  self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage_stop = parameters.get("voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m

        if self.process.running:
            iso_timestamp = comet.make_iso()
            filename = safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
            with open(os.path.join(output_dir, filename), "w") as f:
                # TODO
                f.write(f"sample_name: {sample_name}\n")
                f.write(f"sample_type: {sample_type}\n")
                f.write(f"contact_name: {contact_name}\n")
                f.write(f"measurement_name: {measurement_name}\n")
                f.write(f"measurement_type: {self.type}\n")
                f.write(f"voltage_start: {voltage_start:E} V\n")
                f.write(f"voltage_stop: {voltage_stop:E} V\n")
                f.write(f"voltage_step: {voltage_step:E} V\n")
                f.write(f"current_compliance: {current_compliance:E} A\n")
                f.write("timestamp [s],voltage [V],current_smu [A],current_elm [A],temperature [°C],humidity [%rH]\n")
                f.flush()

                voltage = smu.source.voltage.level
                step = auto_step(voltage, voltage_stop, voltage_step)

                def read_elements(device):
                    """Perform READ and return dictionary of elements.
                    :FROM:ELEM -> A, B, C
                    :INIT
                    :FETC? -> 1, 2, 3
                    Returns {'A': 1, 'B': 2, 'C': 3}
                    """
                    elements = list(map(str.strip, device.resource.query(":FORM:ELEM?").split(",")))
                    logging.info("%s: %s", device.__class__.__name__, elements)
                    device.resource.write(":INIT")
                    device.resource.query("*OPC?")
                    values = list(map(float, device.resource.query(":FETC?").split(",")))
                    logging.info("%s: %s", device.__class__.__name__, values)
                    result = dict(zip(elements, values))
                    logging.info("%s: %s", device.__class__.__name__, result)
                    return result

                logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, voltage_stop, step)
                for voltage in comet.Range(voltage, voltage_stop, step):
                    logging.info("set voltage: %E V", voltage)
                    self.process.events.message(f"{voltage:.3f} V")
                    smu.clear()
                    smu.source.voltage.level = voltage
                    time.sleep(.100)
                    # check_error(smu)
                    timestamp = time.time()

                    # read SMU
                    smu_data = read_elements(smu)
                    reading_voltage = smu_data.get("VOLT")
                    reading_current = smu_data.get("CURR")
                    logging.info("SMU reading: %E V %E A", reading_voltage, reading_current)
                    self.process.events.reading("smu", abs(voltage) if step < 0 else voltage, reading_current)

                    # read ELM
                    elm_data = read_elements(elm)
                    reading_elm = elm_data.get("READ")# * 1.0E-9
                    logging.info("ELM reading: %E READ", reading_current)
                    self.process.events.reading("elm", abs(voltage) if step < 0 else voltage, reading_elm)

                    self.process.events.update()

                    # TODO
                    temperature = float('nan')
                    humidity = float('nan')
                    f.write(f"{timestamp:.3f},{voltage:E},{reading_current:E},{reading_elm:E},{temperature:E},{humidity:E}\n")
                    f.flush()
                    time.sleep(waiting_time)
                    # Compliance?
                    compliance_tripped = smu.sense.current.protection.tripped
                    if compliance_tripped:
                        logging.error("SMU in compliance")
                        raise ValueError("compliance tripped")
                    # check_error(smu)
                    if not self.process.running:
                        break

        self.process.events.progress(4, 5)

    def finalize(self, smu, elm):
        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        parameters = self.measurement_item.parameters
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage = smu.source.voltage.level
        step = auto_step(voltage, 0, voltage_step)

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, step)
        for voltage in comet.Range(voltage, 0, step):
            logging.info("set voltage: %E V", voltage)
            self.process.events.message(f"{voltage:.3f} V")
            smu.source.voltage.level = voltage
            time.sleep(.100)
            # check_error(smu)

        smu.output = False
        check_error(smu)

        self.process.events.progress(5, 5)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("k6517") as elm:
                try:
                    self.initialize(smu, elm)
                    self.measure(smu, elm)
                finally:
                    self.finalize(smu, elm)

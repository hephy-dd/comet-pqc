from .smu import SMUInstrument
from comet.driver.keithley import K2657A

__all__ = ['K2657AInstrument']

class K2657AInstrument(SMUInstrument):

    def __init__(self, context):
        super().__init__(K2657A(context))

    def reset(self):
        self.context.reset()
        self.context.clear()
        self.context.beeper.enable = False

    def clear(self):
        self.context.clear()

    def get_error(self):
        if self.context.errorqueue.count:
            code, message = self.context.errorqueue.next()
            return code, message
        return 0, "no error"

    # Output

    def get_output(self):
        value = self.context.source.output
        return {
            'ON': self.OUTPUT_ON,
            'OFF': self.OUTPUT_OFF
        }.get(value)

    def set_output(self, value):
        value = {
            self.OUTPUT_ON: 'ON',
            self.OUTPUT_OFF: 'OFF'
        }.get(value)
        self.context.source.output = value

    # Source function

    def get_source_function(self):
        value = self.context.source.func
        return {
            'DCVOLTS': self.SOURCE_FUNCTION_VOLTAGE,
            'DCAMPS': self.SOURCE_FUNCTION_CURRENT
        }.get(value)

    def set_source_function(self, value):
        value = {
            self.SOURCE_FUNCTION_VOLTAGE: 'DCVOLTS',
            self.SOURCE_FUNCTION_CURRENT: 'DCAMPS'
        }.get(value)
        self.context.source.func = value

    # Source voltage

    def get_source_voltage(self):
        return self.context.source.levelv

    def set_source_voltage(self, value):
        self.context.source.levelv = value

    # Source current

    def get_source_current(self):
        return self.context.source.leveli

    def set_source_current(self, value):
        self.context.source.leveli = value

    # Source voltage range

    def get_source_voltage_range(self):
        return self.context.source.rangev

    def set_source_voltage_range(self, value):
        self.context.source.rangev = value

    # Source voltage autorange

    def get_source_voltage_autorange(self):
        return self.context.source.autorangev

    def set_source_voltage_autorange(self, value):
        self.context.source.autorangev = value

    # Source current range

    def get_source_current_range(self):
        return self.context.source.rangei

    def set_source_current_range(self, value):
        self.context.source.rangei = value

    # Source current autorange

    def get_source_current_autorange(self):
        return self.context.source.autorangei

    def set_source_current_autorange(self, value):
        self.context.source.autorangei = value

    # Sense mode

    def get_sense_mode(self, value):
        value = self.context.sense
        return {
            'REMOTE': self.SENSE_MODE_REMOTE,
            'LOCAL': self.SENSE_MODE_LOCAL
        }.get(value)

    def set_sense_mode(self, value):
        value = {
            self.SENSE_MODE_REMOTE: 'REMOTE',
            self.SENSE_MODE_LOCAL: 'LOCAL'
        }.get(value)
        self.context.sense = value

    # Compliance tripped

    def compliance_tripped(self):
        return self.context.source.compliance

    # Compliance voltage

    def get_compliance_voltage(self):
        return self.context.source.limitv

    def set_compliance_voltage(self, value):
        self.context.source.limitv = value

    # Compliance current

    def get_compliance_current(self):
        return self.context.source.limiti

    def set_compliance_current(self, value):
        self.context.source.limiti = value

    # Filter enable

    def get_filter_enable(self):
        return self.context.measure.filter.enable

    def set_filter_enable(self, value):
        self.context.measure.filter.enable = value

    # Filter count

    def get_filter_count(self):
        return self.context.measure.filter.count

    def set_filter_count(self, value):
        self.context.measure.filter.count = value

    # Filter type

    def get_filter_type(self):
        value = self.context.sense.average.tcontrol
        return {
            'REPEAT': self.FILTER_TYPE_REPEAT,
            'MOVING': self.FILTER_TYPE_MOVING
        }.get(value)

    def set_filter_type(self, value):
        value = {
            self.FILTER_TYPE_REPEAT: 'REPEAT',
            self.FILTER_TYPE_MOVING: 'MOVING'
        }.get(value)
        self.context.measure.filter.type = value

    # Terminal

    TERMINAL_OPTIONS = (
        SMUInstrument.TERMINAL_FRONT,
    )

    def get_terminal(self):
        return self.TERMINAL_FRONT

    def set_terminal(self, value):
        pass

    # Reading

    def read_current(self):
        return self.context.measure.i()

    def read_voltage(self):
        return self.context.measure.v()

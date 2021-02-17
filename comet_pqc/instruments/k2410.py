from .smu import SMUInstrument
from ..driver import K2410

__all__ = ['K2410Instrument']

class K2410Instrument(SMUInstrument):

    def __init__(self, context):
        super().__init__(K2410(context))

    def reset(self):
        self.context.reset()
        self.context.clear()
        self.context.system.beeper.status = False

    def clear(self):
        self.context.clear()

    def get_error(self):
        code, message = self.context.system.error
        return code, message

    # Output

    def get_output(self):
        value = self.context.output
        return {
            True: self.OUTPUT_ON,
            False: self.OUTPUT_OFF
        }.get(value)

    def set_output(self, value):
        value = {
            self.OUTPUT_ON: True,
            self.OUTPUT_OFF: False
        }.get(value)
        self.context.output = value

    # Source function

    def get_source_function(self):
        value = self.context.source.function.mode
        return {
            'VOLTAGE': self.SOURCE_FUNCTION_VOLTAGE,
            'CURRENT': self.SOURCE_FUNCTION_CURRENT
        }.get(value)

    def set_source_function(self, value):
        value = {
            self.SOURCE_FUNCTION_VOLTAGE: 'VOLTAGE',
            self.SOURCE_FUNCTION_CURRENT: 'CURRENT'
        }.get(value)
        self.context.source.function.mode = value

    # Source voltage

    def get_source_voltage(self):
        return self.context.source.voltage.level

    def set_source_voltage(self, value):
        self.context.source.voltage.level = value

    # Source current

    def get_source_current(self):
        return self.context.source.current.level

    def set_source_current(self, value):
        self.context.source.current.level = value

    # Source voltage range

    def get_source_voltage_range(self):
        return self.context.source.voltage.range.level

    def set_source_voltage_range(self, value):
        self.context.source.voltage.range.level = value

    # Source voltage autorange

    def get_source_voltage_autorange(self):
        return self.context.source.voltage.range.auto

    def set_source_voltage_autorange(self, value):
        self.context.source.voltage.range.auto = value

    # Source current range

    def get_source_current_range(self):
        return self.context.source.current.range.level

    def set_source_current_range(self, value):
        self.context.source.current.range.level = value

    # Source current autorange

    def get_source_current_autorange(self):
        return self.context.source.current.range.auto

    def set_source_current_autorange(self, value):
        self.context.source.current.range.auto = value

    # Sense mode

    def get_sense_mode(self):
        value = self.context.system.rsense
        return {
            'ON': self.SENSE_MODE_REMOTE,
            'OFF': self.SENSE_MODE_LOCAL
        }.get(value)

    def set_sense_mode(self, value):
        value = {
            self.SENSE_MODE_REMOTE: 'ON',
            self.SENSE_MODE_LOCAL: 'OFF'
        }.get(value)
        self.context.system.rsense = value

    # Compliance tripped

    def compliance_tripped(self):
        # TODO: how to distinguish?
        return self.context.sense.current.protection.tripped or \
            self.context.sense.voltage.protection.tripped

    # Compliance voltage

    def get_compliance_voltage(self):
        return self.context.sense.voltage.protection.level

    def set_compliance_voltage(self, value):
        self.context.sense.voltage.protection.level = value

    # Compliance current

    def get_compliance_current(self):
        return self.context.sense.current.protection.level

    def set_compliance_current(self, value):
        self.context.sense.current.protection.level = value

    # Filter enable

    def get_filter_enable(self):
        return self.context.sense.average.state

    def set_filter_enable(self, value):
        self.context.sense.average.state = value

    # Filter count

    def get_filter_count(self):
        return self.context.sense.average.count

    def set_filter_count(self, value):
        self.context.sense.average.count = value

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
        self.context.sense.average.tcontrol = value

    # Terminal

    def get_terminal(self):
        value = self.context.route.terminals
        return {
            'FRONT': self.TERMINAL_FRONT,
            'REAR': self.TERMINAL_REAR
        }.get(value)

    def set_terminal(self, value):
        value = {
            self.TERMINAL_FRONT: 'FRONT',
            self.TERMINAL_REAR: 'REAR'
        }.get(value)
        self.context.route.terminals = value

    # Reading

    def read_current(self):
        self.context.format.elements = ['CURRENT']
        return self.context.read()[0]

    def read_voltage(self):
        self.context.format.elements = ['VOLTAGE']
        return self.context.read()[0]

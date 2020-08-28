from comet.emulator.emulator import message, run
from comet.emulator.hephy.environmentbox import EnvironmentBoxHandler

class PQCEnvironmentBoxHandler(EnvironmentBoxHandler):

    test_led = False

    map_on_off = {'OFF': False, 'ON': True}

    message_ok = "OK"

    @classmethod
    @message(r'GET:TEST_LED \?')
    def get_test_led(cls):
        return cls.test_led

    @classmethod
    @message(r'SET:TEST_LED (ON|OFF)')
    def set_test_led(cls, value):
        cls.test_led = cls.map_on_off.get(value, False)
        return cls.message_ok

if __name__ == '__main__':
    run(PQCEnvironmentBoxHandler)

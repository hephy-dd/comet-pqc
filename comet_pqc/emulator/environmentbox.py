import random

from comet.emulator.emulator import message, run
from comet.emulator.hephy.environmentbox import EnvironmentBoxHandler


class PQCEnvironmentBoxHandler(EnvironmentBoxHandler):

    test_led = False

    map_on_off = {"OFF": False, "ON": True}

    message_ok = "OK"

    @classmethod
    def pc_data(cls):
        pc_data = super().pc_data()
        pc_data[1] = random.uniform(55.0, 60.0)
        pc_data[2] = random.uniform(22.0, 23.0)
        pc_data[33] = random.uniform(21.5, 22.5)
        return pc_data

    @classmethod
    @message(r"GET:TEST_LED \?")
    def get_test_led(cls):
        return cls.test_led

    @classmethod
    @message(r"SET:TEST_LED (ON|OFF)")
    def set_test_led(cls, value):
        cls.test_led = cls.map_on_off.get(value, False)
        return cls.message_ok


if __name__ == "__main__":
    run(PQCEnvironmentBoxHandler)

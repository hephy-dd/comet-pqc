"""Proxy wrappers providing a generic instrument interface."""

import logging
from abc import ABC, abstractmethod

from comet.driver import Driver

__all__ = ['create_proxy', 'ProxyError']

def create_proxy(context):
    """Return proxy instance matching provided context.

    Raises a `TypeError` on error.

    >>> smu = create_proxy(device)
    >>> smu.identification
    'Keithley Inc., Model 2410, 1234567, r1'
    """
    assert isinstance(context, Driver)
    basename = context.__class__.__name__
    for key, value in globals().items():
        if key == f'{basename}Proxy':
            return value(context)
    raise TypeError(type(context).__name__)

class ProxyError(Exception):
    """Proxy error."""

    def __init__(self, context, code, message):
        context = context.context.__class__.__name__
        super().__init__(context, code, message)

    @property
    def context(self):
        return self.args[0]

    @property
    def code(self):
        return self.args[1]

    @property
    def message(self):
        return self.args[2]

    def __str__(self):
        return f"{self.context} error: {self.code}: {self.message}"

class Proxy(ABC):
    """Proxy

    Properties:
     - identification
     - beeper_enable

    Actions:
     - assert_success

    """

    def __init__(self, context):
        assert isinstance(context, Driver)
        self.__context = context

    @property
    def context(self):
        return self.__context

    @property
    @abstractmethod
    def identification(self):
        pass

    @property
    @abstractmethod
    def beeper_enable(self):
        pass

    @beeper_enable.setter
    @abstractmethod
    def beeper_enable(self, value):
        pass

    @abstractmethod
    def reset(self):
        """Reset instrument state."""

    @abstractmethod
    def clear(self):
        """Clear error queues and buffers."""

    @abstractmethod
    def assert_success(self):
        """Assert that no errors in queue."""

# Generic proxies

class SMUProxy(Proxy):
    """Generic Source Meter Unit proxy.

    Properties:
     - identification
     - beeper_enable
     - source_function
     - source_voltage_level
     - source_current_level
     - output_enable

    Actions:
     - assert_success

    """

    FUNCTION_CURRENT = 'CURRENT'
    FUNCTION_VOLTAGE = 'VOLTAGE'

    FILTER_MOVING = 'MOVING'
    FILTER_REPEAT = 'REPEAT'

    @property
    @abstractmethod
    def filter_enable(self):
        pass

    @filter_enable.setter
    @abstractmethod
    def filter_enable(self, value):
        pass

    @property
    @abstractmethod
    def filter_count(self):
        pass

    @filter_count.setter
    @abstractmethod
    def filter_count(self, value):
        pass

    @property
    @abstractmethod
    def filter_type(self):
        pass

    @filter_type.setter
    @abstractmethod
    def filter_type(self, value):
        pass

    @property
    @abstractmethod
    def source_function(self):
        pass

    @source_function.setter
    @abstractmethod
    def source_function(self, value):
        pass

    @property
    @abstractmethod
    def source_voltage_level(self):
        pass

    @property
    @abstractmethod
    def source_current_level(self):
        pass

    @property
    @abstractmethod
    def output_enable(self):
        pass

class ELMProxy(Proxy):
    """Generic Electrometer proxy."""

class LCRProxy(Proxy):
    """Generic LCR Meter proxy."""

class MatrixProxy(Proxy):
    """Generic Switching Matrix proxy."""

# Context specific implementations

class K2410Proxy(SMUProxy):
    """Source Meter Unit proxy for Keithley Model 2410."""

    @property
    def identification(self):
        return self.context.identification

    @property
    def beeper_enable(self):
        return self.context.system.beeper.status

    @beeper_enable.setter
    def beeper_enable(self, value):
        self.context.system.beeper.status = value

    def reset(self):
        self.context.reset()

    def clear(self):
        self.context.clear()

    def assert_success(self):
        code, message = self.context.system.error
        if code:
            ProxyError(self, code, message)

    @property
    def filter_enable(self):
        return self.context.sense.average.state

    @filter_enable.setter
    def filter_enable(self, value):
        self.context.sense.average.state = value

    @property
    def filter_count(self):
        return self.context.sense.average.count

    @filter_count.setter
    def filter_count(self, value):
        self.context.sense.average.count = value

    @property
    def filter_type(self):
        d = {self.FILTER_MOVING: 'MOVING', self.FILTER_REPEAT: 'REPEAT'}
        return d[self.context.sense.average.tcontrol]

    @filter_type.setter
    def filter_type(self, value):
        d = {'MOVING': self.FILTER_MOVING, 'REPEAT': self.FILTER_REPEAT}
        self.context.sense.average.tcontrol = d[value]

    @property
    def source_function(self) -> int:
        d = {'VOLTAGE': self.FUNCTION_VOLTAGE, 'CURRENT': self.FUNCTION_CURRENT}
        return d[self.context.source.function.mode]

    @source_function.setter
    def source_function(self, value: int):
        d = {self.FUNCTION_VOLTAGE: 'VOLTAGE', self.FUNCTION_CURRENT: 'CURRENT'}
        self.context.source.function.mode = d[value]

    @property
    def source_voltage_level(self):
        return self.context.source.voltage.level

    @source_voltage_level.setter
    def source_voltage_level(self, value):
        self.context.source.voltage.level = value

    @property
    def source_current_level(self):
        return self.context.source.current.level

    @source_current_level.setter
    def source_current_level(self, value):
        self.context.source.current.level = value

    @property
    def output_enable(self):
        return self.context.output

    @output_enable.setter
    def output_enable(self, value):
        self.context.output = value

class K2657AProxy(SMUProxy):
    """Source Meter Unit proxy for Keithley Model 2657A."""

    @property
    def identification(self):
        return self.context.identification

    @property
    def beeper_enable(self):
        return self.context.beeper.enable

    @beeper_enable.setter
    def beeper_enable(self, value):
        self.context.beeper.enable = value

    def reset(self):
        self.context.reset()

    def clear(self):
        self.context.clear()

    def assert_success(self):
        if self.context.errorqueue.count:
            code, message = self.context.errorqueue.next()
            ProxyError(self, code, message)

    @property
    def filter_enable(self):
        return self.context.measure.filter.enable

    @filter_enable.setter
    def filter_enable(self, value):
        self.context.measure.filter.enable = value

    @property
    def filter_count(self):
        return self.context.measure.filter.count

    @filter_count.setter
    def filter_count(self, value):
        self.context.measure.filter.count = value

    @property
    def filter_type(self):
        d = {self.FILTER_MOVING: 'MOVING', self.FILTER_REPEAT: 'REPEAT'}
        return d[self.context.sense.average.tcontrol]

    @filter_type.setter
    def filter_type(self, value):
        d = {'MOVING': self.FILTER_MOVING, 'REPEAT': self.FILTER_REPEAT}
        self.context.sense.average.tcontrol = d[value]

    @property
    def source_function(self):
        d = {self.FUNCTION_VOLTAGE: 'DCVOLTS', self.FUNCTION_CURRENT: 'DCAMPS'}
        return d[self.context.source.func]

    @source_function.setter
    def source_function(self, value):
        d = {'DCVOLTS': self.FUNCTION_VOLTAGE, 'DCAMPS': self.FUNCTION_CURRENT}
        self.context.source.func = d[value]

    @property
    def source_voltage_level(self):
        return self.context.source.levelv

    @source_voltage_level.setter
    def source_voltage_level(self, value):
        self.context.source.levelv = value

    @property
    def output_enable(self):
        return self.context.source.output == 'ON'

    @output_enable.setter
    def output_enable(self, value):
        self.context.source.output = 'ON' if value else 'OFF'

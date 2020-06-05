import datetime
import logging
import time

from comet.driver import Driver
from comet.driver import lock, Property, Action
from comet.driver import IEC60488

from .utils import BitField

__all__ = ['K707B', 'K2657A', 'EnvironmentBox']

class K707B(IEC60488):
    """Keithley Models 707B Switching Matrix."""

    class Channel(Driver):

        @Action()
        def getclose(self):
            result = self.resource.query('print(channel.getclose("allslots"))')
            if result == 'nil':
                return []
            return result.split(';')

        @Action()
        @lock
        def close(self, channels):
            channels = ','.join(channels)
            self.resource.write(f'channel.close("{channels}")')
            self.resource.query('*OPC?')

        @Action()
        @lock
        def open(self, channels=None):
            if channels is None:
                channels = 'allslots'
            else:
                channels = ','.join(channels)
            self.resource.write(f'channel.open("{channels}")')
            self.resource.query('*OPC?')

    def __init__(self, resource):
        super().__init__(resource)
        self.channel = self.Channel(resource)

class K2657A(IEC60488):
    """Keithley Models 2657A High Power System SourceMeter."""

    class Beeper(Driver):

        @Property(values=[False, True])
        def enable(self):
            return bool(float(self.resource.query('print(beeper.enable)')))

        @enable.setter
        @lock
        def enable(self, value):
            self.resource.write(f'beeper.enable = {value:d}')
            self.resource.query('*OPC?')

    class ErrorQueue(Driver):

        @Property()
        def count(self):
            return bool(float(self.resource.query('print(errorqueue.count)')))

        @Action()
        def next(self):
            return self.resource.query('print(errorqueue.next())').split('\t')

        @Action()
        def clear(self):
            self.resource.write('errorqueue.clear()')
            self.resource.query('*OPC?')

    class Source(Driver):

        @Property()
        def compliance(self):
            return bool(float(self.resource.query('print(smua.source.compliance)')))

        @Property()
        def leveli(self):
            return float(self.resource.query('print(smua.source.leveli)'))

        @leveli.setter
        @lock
        def leveli(self, value):
            self.resource.write(f'smua.source.leveli = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def limiti(self):
            return float(self.resource.query('print(smua.source.limiti)'))

        @limiti.setter
        @lock
        def limiti(self, value):
            self.resource.write(f'smua.source.limiti = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def levelv(self):
            return float(self.resource.query('print(smua.source.levelv)'))

        @levelv.setter
        @lock
        def levelv(self, value):
            self.resource.write(f'smua.source.levelv = {value:E}')
            self.resource.query('*OPC?')

        @Property()
        def limitv(self):
            return float(self.resource.query('print(smua.source.limitv)'))

        @limitv.setter
        @lock
        def limitv(self, value):
            self.resource.write(f'smua.source.limitv = {value:E}')
            self.resource.query('*OPC?')

        @Property(values=[False, True])
        def output(self):
            return bool(float(self.resource.query('print(smua.source.output)')))

        @output.setter
        @lock
        def output(self, value):
            self.resource.write(f'smua.source.output = {value:d}')
            self.resource.query('*OPC?')

    def __init__(self, resource):
        super().__init__(resource)
        self.beeper = self.Beeper(resource)
        self.errorqueue = self.ErrorQueue(resource)
        self.source = self.Source(resource)

class EnvironmentBox(Driver):

    class PCData:
        """Environment box status snapshot."""

        class PowerRelayStates:
            """State of power relays."""

            def __init__(self, value):
                value = BitField(value)
                self.microscope_control = value[0]
                self.box_light = value[1]
                self.probecard_light = value[2]
                self.laser_sensor = value[3]
                self.probecard_camera = value[4]
                self.microscope_camera = value[5]
                self.microscope_light = value[6]

        def __init__(self, data):
            self.n_sensors = int(data[0])
            self.box_humidity = float(data[1])
            self.box_temperature = float(data[2])
            self.box_dewpoint = float(data[3])
            self.pid_status = int(data[4])
            self.pid_setpoint = float(data[5])
            self.pid_input = float(data[6])
            self.pid_output = float(data[7])
            self.pid_kp1 = float(data[8])
            self.pid_ki1 = float(data[9])
            self.pid_kd1 = float(data[10])
            self.pid_max = float(data[11])
            self.pid_min = float(data[12])
            self.pid_mode = ['HUM', 'DEW'][int(data[13])] # HUM/DEW
            self.pid_kp2 = float(data[14])
            self.pid_ki2 = float(data[15])
            self.pid_kd2 = float(data[16])
            self.pid_active = int(data[17])
            self.pid_threshold = float(data[18])
            self.humid_flow_direction = int(data[19])
            self.pid_threshold = float(data[20])
            self.current = float(data[21]) * 1e3 # mA to A
            self.value_on = int(data[22])
            self.relay_states = self.PowerRelayStates(int(data[23]))
            self.box_light_state = bool(int(data[24]))
            self.box_door_state = bool(int(data[25]))
            self.safety_alert = int(data[26])
            self.stepper_motor_state = int(data[27])
            self.air_flow_sensor = int(data[28])
            self.vacuum_flow_sensor = int(data[29])
            self.test_led = bool(int(data[30]))
            self.discharge_time = float(data[31]) * 1e3 # ms to s
            self.box_lux = float(data[32])
            self.chuck_temperature = float(data[33]) # Pt100-1
            self.chuck_block_temperature = float(data[34]) # Pt100-2
            self.pid_sample_time = float(data[35]) * 1e3 # ms to s
            self.pid_pon_state = int(data[36])
            self.chuck_temperature_state = int(data[37])
            self.chuck_block_temperature_state = int(data[38])

    @Property()
    def identification(self):
        """Device identification.

        >>> device.identification
        'ENV Box V1.1'
        """
        return self.resource.query('*IDN?')

    @Property(values=[False, True])
    def test_led(self):
        """Test-Running LED.

        >>> device.test_led = True
        >>> device.test_led
        True
        """
        return bool(int(self.resource.query('GET:TEST_LED ?')))

    @test_led.setter
    def test_led(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:TEST_LED {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Action()
    @lock
    def discharge(self):
        """Executes AUTO discarge of decoupling box.

        >>> device.discarge()
        """
        discarge_time = self.discharge_time
        self.resource.write('SET:DISCHARGE AUTO')
        time.sleep(discarge_time)
        result = self.resource.read()
        if result != 'OK':
            raise RuntimeError(result)

    @Property(minimum=0.0, maximum=9.999)
    def discharge_time(self):
        """Discarge time in seconds.

        >>> device.discharge_time = 60.0
        >>> device.discarge_time
        60.0
        """
        return float(self.resource.query('GET:DISCHARGE_TIME ?')) / 1e3 # from milliseconds

    @discharge_time.setter
    def discharge_time(self, value):
        millisec = int(value * 1e3) # to milliseconds
        result = self.resource.query(f'SET:DISCHARGE_TIME {millisec:d}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property(values=[False, True])
    def pid_control(self):
        """PID controller state.

        >>> device.pid_control = True
        >>> device.pid_control
        True
        """
        return bool(int(self.resource.query('GET:CTRL ?')))

    @pid_control.setter
    def pid_control(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:CTRL {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property(values=['HUM', 'DEW'])
    def pid_mode(self):
        """PID controller mode.

        >>> device.pid_control_mode = 'DEW'
        >>> device.pid_control_mode
        'DEW'
        """
        return self.pc_data.pid_mode

    @pid_mode.setter
    def pid_mode(self, value):
        result = self.resource.query(f'SET:CTRL_MODE {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property(values=[False, True])
    def microscope_control(self):
        """Microscope control switch.

        >>> device.microscope_control = True
        >>> device.microscope_control
        True
        """
        return self.pc_data.relay_states.microscope_control

    @microscope_control.setter
    def microscope_control(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:MICROSCOPE_CTRL {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property(values=[False, True])
    def microscope_light(self):
        """Microscope light switch.

        >>> device.microscope_light = True
        >>> device.microscope_light
        True
        """
        return self.pc_data.relay_states.microscope_light

    @microscope_light.setter
    def microscope_light(self, value):
        value = {False: "OFF", True: "ON"}[value]
        result = self.resource.query(f"SET:MICROSCOPE_LIGHT {value:s}")
        if result != 'OK':
            raise RuntimeError(result)

    @Property(values=[False, True])
    def microscope_camera(self):
        """Microscope camera switch.

        >>> device.microscope_camera = True
        >>> device.microscope_camera
        True
        """
        return self.pc_data.relay_states.microscope_camera

    @microscope_camera.setter
    def microscope_camera(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:MICROSCOPE_CAM {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property()
    def probecard_light(self):
        """Probe card light switch and actual light relay state.

        >>> device.probecard_light = True
        >>> device.probecard_light
        True
        """
        return self.pc_data.relay_states.probecard_light

    @probecard_light.setter
    def probecard_light(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:PROBCARD_LIGHT {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property()
    def probecard_camera(self):
        """Probe card camera switch and actual camera relay state.

        >>> device.probecard_camera = True
        >>> device.probecard_camera
        True
        """
        return self.pc_data.relay_states.probecard_camera

    @probecard_camera.setter
    def probecard_camera(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:PROBCARD_CAM {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @property
    def box_light(self):
        """Box light switch and actual light relay state.

        >>> device.box_light = True
        >>> device.box_light
        True
        """
        return self.pc_data.relay_states.box_light

    @box_light.setter
    def box_light(self, value):
        value = {False: 'OFF', True: 'ON'}[value]
        result = self.resource.query(f'SET:BOX_LIGHT {value:s}')
        if result != 'OK':
            raise RuntimeError(result)

    @Property()
    def uptime(self):
        """CPU uptime in seconds.

        >>> device.uptime
        54373
        """
        dd, hh, mm, ss = self.resource.query('GET:UPTIME ?').split(',')
        dt = datetime.timedelta(
            days=int(dd),
            hours=int(hh),
            minutes=int(mm),
            seconds=int(ss)
        )
        return int(dt.total_seconds())

    @Property()
    def log(self):
        """List of log messages.

        >>> device.log
        []
        """
        return self.resource.query('GET:LOG ?')

    @Property()
    def version(self):
        """Firmware version.

        >>> device.version
        '1.1'
        """
        return self.resource.query('GET:VERSION ?')

    @Property()
    def pc_data(self):
        """Snapshot of current device state. Returns instance of type `PCData`.

        >>> device.pc_data.box_temperature
        23.5
        """
        pc_data = self.resource.query('GET:PC_DATA ?').split(',')
        return self.PCData(pc_data)

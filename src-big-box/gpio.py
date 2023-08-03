from time import sleep

import config
import log

if config.data['Board']['Type'] == 'Orange':
    import OPi.GPIO as GPIO
else:
    import RPi.GPIO as GPIO


class Gpio:
    def __init__(self):
        self.on_open_sensor_activated = None

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # LEDs

        self.red_pin = int(config.data['RedLed']['Pin'])
        if self.red_pin != 0:
            self.red_active = int(config.data['RedLed']['ActiveLevel'])
            self.red_inactive = (self.red_active != True)
            GPIO.setup(self.red_pin, GPIO.OUT)
            GPIO.output(self.red_pin, self.red_inactive)

        self.green_pin = int(config.data['GreenLed']['Pin'])
        if self.green_pin != 0:
            self.green_active = int(config.data['GreenLed']['ActiveLevel'])
            self.green_inactive = (self.green_active != True)
            GPIO.setup(self.green_pin, GPIO.OUT)
            GPIO.output(self.green_pin, self.green_inactive)

        #  Close sensors
        self.close_sensor_pin_1 = int(config.data['MotorSensor1']['Pin'])
        self.close_sensor_pin_2 = int(config.data['MotorSensor2']['Pin'])

        if self.close_sensor_pin_1 != 0:

            if int(config.data['MotorSensor1']['PullUp']) == 1:
                GPIO.setup(self.close_sensor_pin_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(self.close_sensor_pin_1, GPIO.IN)

            self.close_sensor_active_1 = int(config.data['MotorSensor1']['ActiveLevel'])

            if self.close_sensor_active_1 == 1:
                GPIO.add_event_detect(self.close_sensor_pin_1, GPIO.RISING)  # low-to-high transition
            else:
                GPIO.add_event_detect(self.close_sensor_pin_1, GPIO.FALLING)  # high-to-low transition
            GPIO.add_event_callback(self.close_sensor_pin_1, self.__on_open_sensor_activation)  ##################

        if self.close_sensor_pin_2 != 0:

            if int(config.data['MotorSensor2']['PullUp']) == 1:
                GPIO.setup(self.close_sensor_pin_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(self.close_sensor_pin_2, GPIO.IN)

            self.close_sensor_active_2 = int(config.data['MotorSensor2']['ActiveLevel'])

            if self.close_sensor_active_2 == 1:
                GPIO.add_event_detect(self.close_sensor_pin_2, GPIO.RISING)  # low-to-high transition
            else:
                GPIO.add_event_detect(self.close_sensor_pin_2, GPIO.FALLING)  # high-to-low transition
            GPIO.add_event_callback(self.close_sensor_pin_2, self.__on_open_sensor_activation)  ###################

        #  open/close motor
        self.motor_pin = int(config.data['Motor']['Pin'])

        if self.motor_pin != 0:
            self.motor_active = int(config.data['Motor']['ActiveLevel'])
            self.motor_inactive = (self.motor_active != True)
            GPIO.setup(self.motor_pin, GPIO.OUT)
            GPIO.output(self.motor_pin, self.motor_inactive)

        self.antenna_pin = int(config.data['Antenna']['Pin'])

        if self.antenna_pin != 0:
            self.antenna_active = int(config.data['Antenna']['Active_level'])
            self.antenna_inactive = (self.antenna_active != True)
            GPIO.setup(self.antenna_pin, GPIO.OUT)
            GPIO.output(self.antenna_pin, self.antenna_inactive)

    def __on_open_sensor_activation(self, pin):
        if self.on_open_sensor_activated is not None:
            self.on_open_sensor_activated()

    def red_on(self):
        if self.red_pin != 0:
            GPIO.output(self.red_pin, self.red_active)

    def red_off(self):
        if self.red_pin != 0:
            GPIO.output(self.red_pin, self.red_inactive)

    def green_on(self):
        if self.green_pin != 0:
            GPIO.output(self.green_pin, self.green_active)

    def green_off(self):
        if self.green_pin != 0:
            GPIO.output(self.green_pin, self.green_inactive)

    def blink_red(self):
        if self.red_pin != 0:
            GPIO.output(self.red_pin, self.red_active)
            sleep(0.2)
            GPIO.output(self.red_pin, self.red_inactive)

    def blink_green(self):
        if self.green_pin != 0:
            GPIO.output(self.green_pin, self.green_active)
            sleep(0.2)
            GPIO.output(self.green_pin, self.green_inactive)

    def is_close(self):  # both close sensors active - returns True
        if self.close_sensor_pin_1 != 0 and self.close_sensor_pin_2 != 0:
            if (GPIO.input(
                    self.close_sensor_pin_1) == self.close_sensor_active_1) and (GPIO.input(self.close_sensor_pin_2) == self.close_sensor_active_2):
                return True
            elif (GPIO.input(self.close_sensor_pin_1) == self.close_sensor_active_1) or (GPIO.input(self.close_sensor_pin_2) == self.close_sensor_active_2):
                return 'reopen'
            else:
                return False
        else:
            return False

    def open(self):
        if self.motor_pin != 0:
            log.debug("open cmd")
            GPIO.output(self.motor_pin, self.motor_active)

    def close(self):
        if self.motor_pin != 0:
            log.debug("close cmd")
            GPIO.output(self.motor_pin, self.motor_inactive)

    # def motor_pins_available(self):
    #     return self.close_sensor_pin_1 != 0 and self.close_sensor_pin_2 != 0 and self.motor_pin != 0

    def motor_pins_available(self):
        return self.close_sensor_pin_1 != 0 and self.motor_pin != 0

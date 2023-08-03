import config
import log

if config.data['Board']['Type'] == 'Orange':
    import OPi.GPIO as GPIO
else:
    import RPi.GPIO as GPIO


class Gpio:
    def __init__(self):
        self.onSensorChanged = None  # ??

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        self.entrySensorPin = int(config.data['EntrySensor']['Pin'])
        self.entrySensorActive = int(config.data['EntrySensor']['ActiveLevel'])

        if int(config.data['EntrySensor']['PullUp']) == 1:  # подтяжка
            GPIO.setup(self.entrySensorPin, GPIO.IN,
                       pull_up_down=GPIO.PUD_UP)  # set up every channel you are using as an input or an output
        else:
            GPIO.setup(self.entrySensorPin, GPIO.IN)

        GPIO.add_event_detect(self.entrySensorPin,
                              GPIO.BOTH)  # both - rising and falling edges; add_event_detect - отлавливает событие на пине
        GPIO.add_event_callback(self.entrySensorPin, self.__onSensorChanged)

        self.exitSensorPin = int(config.data['ExitSensor']['Pin'])
        self.exitSensorActive = int(config.data['ExitSensor']['ActiveLevel'])

        if int(config.data['ExitSensor']['PullUp']) == 1:
            GPIO.setup(self.exitSensorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(self.exitSensorPin, GPIO.IN)

        GPIO.add_event_detect(self.exitSensorPin, GPIO.BOTH)
        GPIO.add_event_callback(self.exitSensorPin, self.__onSensorChanged)


    def __onSensorChanged(self, pin):
        if self.onSensorChanged is not None:
            self.onSensorChanged()

    def isEntryActive(self):
        return GPIO.input(self.entrySensorPin) == self.entrySensorActive

    def isExitActive(self):
        return GPIO.input(self.exitSensorPin) == self.exitSensorActive

import log
import sys
import time
import config
import gpio
import uhf
import server
import usb
from enum import Enum
import threading
import datetime


class Monitor:
    def __init__(self):
        usbPorts = usb.Usb()

        self.mutex = threading.Lock()

        # последнее значение, прочитанное с датчиков
        self.lastEntry = False
        self.lastExit = False
        self.last_act_sensor = str()

        # true, если проход сейчас в процессе.
        # проход в процессе начинается как только из нейтрального состояния активируется какой-нибудь из датчиков
        self.passInProgress = False

        # если passInProgress==true, признаки того что в процессе текущего прохода хоть раз активировался тот и другой датчик
        self.seenEntry = False
        self.seenExit = False

        # True - when the data was sent
        self.dataIsSend = False

        self.flag = False

        # если passInProgress==true, направление текущего прохода или None если оно не известно
        self.direction = None

        # если passInProgress==true, время когда оба датчика деактивировались или None если это еще не наступило
        self.passDeactTime = None

        self.gpio = gpio.Gpio()
        self.gpio.onSensorChanged = self.__tick

        self.server = server.Server()

        self.uhf = uhf.Collector(usbPorts.getUhfPorts())

        self.__tick()

    def __tick(self):
        # entry = self.gpio.isEntryActive()
        # exit = self.gpio.isExitActive()

        with self.mutex:
            entry = self.gpio.isEntryActive()
            exit = self.gpio.isExitActive()
            anyActive1 = entry or exit  # bounce check

            time.sleep(int(config.data['Logic']['BounceTime']))

            entry = self.gpio.isEntryActive()
            exit = self.gpio.isExitActive()
            anyActive2 = entry or exit

            anyActiveNow = anyActive1 and anyActive2

            if self.passInProgress:
                # проход в процессе
                if self.passDeactTime is not None:
                    # determine direction
                    if self.flag:
                        # проход в процессе, ни один датчик сейчас не активен, деактивация датчика(ов) произошла только что.
                        if self.lastEntry:
                            log.debug(f"sensors have deactivated, it is 'entry', waiting for the timeout to pass")
                            self.direction = "entry"
                            self.flag = False
                        elif self.lastExit:
                            log.debug(f"sensors have deactivated, it is 'exit', waiting for the timeout to pass")
                            self.direction = "exit"
                            self.flag = False

                    else:
                        if (datetime.datetime.now() - self.passDeactTime).total_seconds() >= int(
                                config.data['Logic']['Timeout']):
                            log.debug(f"timeout has passed, stopping the reader. direction: {self.direction}")
                            tags = self.uhf.stop()
                            if self.direction is not None:
                                self.server.sendReport(self.direction, tags)
                            self.passDeactTime = None
                            self.direction = None
                            self.expiring_time = datetime.datetime.now()  ###

                else:
                    if entry != self.lastEntry or exit != self.lastExit or exit or entry:
                        if entry:
                            self.last_act_sensor = 'entry'
                        elif exit:
                            self.last_act_sensor = 'exit'

                        self.expiring_time = datetime.datetime.now()

                    else:
                        if (datetime.datetime.now() - self.expiring_time).total_seconds() >= int(
                                config.data['Logic']['WaitingTime']):
                            log.debug(f'waiting time is over, last active sensor is {self.last_act_sensor}')
                            self.passInProgress = False
                            self.direction = None
                            self.passDeactTime = None
                            self.expiring_time = None
                            self.last_act_sensor = 'None'


            else:
                # проход не в процессе
                if anyActiveNow:
                    print(f'entry:{entry}, exit:{exit}')
                    # проход начинается
                    log.debug(f"starting the reader")
                    self.passInProgress = True
                    self.seenEntry = entry
                    self.seenExit = exit
                    self.direction = None
                    self.passDeactTime = datetime.datetime.now()
                    self.uhf.start()
                    self.flag = True

            self.lastEntry = entry
            self.lastExit = exit

    def run(self):
        while True:
            self.__tick()
            time.sleep(0.2)


if __name__ == '__main__':
    log.info("Starting")
    m = Monitor()
    m.run()

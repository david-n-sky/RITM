import log
from time import sleep
import config
import gpio
import nfc
import server
import usb
from enum import Enum
import threading
import datetime


class State(Enum):
    # Только запустились, еще ничего не сделали
    INIT = 1

    # Стоим закрытые ничего не делаем.
    IDLE = 2

    # Движемся на открытие. Ждем пока активируется датчик открытия, чтобы потом начать ждать пока он деактивируется.
    OPENING = 3

    # Стоим в открытом положении. Ждем пока сработает таймер на начало закрытия.
    OPENED = 4

    # Движемся на закрытие. Ждем пока пройдет время, отведенное на закрытие.
    CLOSING = 5

    # Датчик открытия неожиданно активировался без команды на открытие.
    # Ждем пока он деактивируется назад.
    OPENED_UNEXPECTED = 6


class StateMachine:

    def __init__(self):
        self.mutex = threading.Lock()

        self.state = State.INIT
        self.stateBeginTime = None
        self.stateEndTime = None
        self.time = 0  # for blink
        self.running_time = 2  # первое время движения на открытие and closing
        self.was_opened = False  # флажок для определения, когда был задействован датчик
        self.match_flag = 0  # флажок для определения поломки датчика

        self.uuuid = None

        self.closeTime = int(config.data['CloseMotor']['FirstCloseTime'])

        self.gpio = gpio.Gpio()
        self.gpio.onOpenSensorActivated = self.__onOpenSensorActivated

        self.gpio.close()
        sleep(5)
        self.gpio.stop()

        if int(config.data['Nfc']['Active']) == 1:
            self.nfc = nfc.Reader()
            self.nfc.onRead = self.__onNfcRead

        self.server = server.Server()

        self.usbPorts = usb.Usb()
        self.usbPorts.onCard = self.__onNfcRead

    def __onOpenSensorActivated(self):
        with self.mutex:
            if self.state == State.IDLE:
                self.__switchState(State.OPENED_UNEXPECTED, None)
            elif self.state == State.OPENING:
                self.was_opened = True

    def __onNfcRead(self, uuuid):
        if uuuid is not None:
            th = threading.Thread(target=self.__db, args=(uuuid,))
            th.start()

    def __db(self, uuuid):
        with open("db", "r+") as db:
            allowed_uuids = db.read().splitlines()

        if uuuid in allowed_uuids:
            log.info(f"Карта {uuuid} - доступ разрешен")

            self.__switchState(State.OPENING, self.running_time)
            self.gpio.open()

            with open("last_card.txt", "w") as f:
                f.write(uuuid)

        else:
            log.info(f"Карта {uuuid} - доступ запрещен")

            self.gpio.redOff()
            self.gpio.greenOff()

            self.time = 0
            while self.time < 10:
                self.gpio.blink_red()
                sleep(0.2)
                self.time += 1

        self.server.changeUuidDb(uuuid)

    def __onTick(self):
        with self.mutex:

            if self.state == State.INIT:
                self.gpio.greenOff()
                self.gpio.redOn()
                if self.gpio.isOpen():
                    log.info("Starting with active open sensor. Closing.")
                    self.gpio.close()
                    self.__switchState(State.CLOSING, self.closeTime)
                else:
                    log.info("Starting with inactive open sensor.")
                    self.gpio.stop()
                    self.__switchState(State.IDLE, None)

            elif self.state == State.IDLE:
                if 0 < self.time < 10:
                    self.gpio.greenOff()
                else:
                    self.gpio.greenOff()
                    self.gpio.redOn()

            elif self.state == State.OPENING:
                if 0 < self.time < 10:
                    self.gpio.greenOff()
                else:
                    self.gpio.redOff()
                    self.gpio.greenOn()

                if not self.gpio.isOpen() and self.was_opened:  # sets the opening time via opening sensor and checks the sensor for breaking
                    self.was_opened = False
                    t = (datetime.datetime.now() - self.stateBeginTime).total_seconds()  # время от начала открытия и до окончания срабатывания датчика

                    if self.running_time == t * 1.1:
                        self.match_flag += 1
                        if self.match_flag > 2:
                            log.info('Please check the opening sensor, it may be broken')  # придумать куда это отослать
                            self.match_flag = 0

                    self.running_time = t * 1.1  # новое время открытия

                if datetime.datetime.now() >= self.stateEndTime:
                    self.gpio.greenOn()
                    self.gpio.redOff()
                    self.gpio.stop()
                    self.__switchState(State.OPENED, int(config.data['CloseMotor']['DelayBeforeClose']))

            elif self.state == State.OPENED:
                if 0 < self.time < 10:
                    self.gpio.greenOff()
                else:
                    self.gpio.redOff()
                    self.gpio.greenOn()

                if datetime.datetime.now() >= self.stateEndTime:
                    self.gpio.greenOff()
                    self.gpio.close()
                    self.__switchState(State.CLOSING, self.running_time)

            elif self.state == State.CLOSING:
                if 0 < self.time < 10:
                    self.gpio.greenOff()
                else:
                    self.gpio.greenOff()
                    self.gpio.redOn()

                if datetime.datetime.now() >= self.stateEndTime:
                    self.gpio.stop()
                    if self.gpio.isOpen():
                        self.__switchState(State.OPENED_UNEXPECTED, None)
                    else:
                        self.__switchState(State.IDLE, None)

            elif self.state == State.OPENED_UNEXPECTED:
                if 0 < self.time < 10:
                    self.gpio.greenOff()
                else:
                    self.gpio.redOff()
                    self.gpio.blink_green()

                if not self.gpio.isOpen():
                    self.gpio.redOn()
                    self.__switchState(State.IDLE, None)

    def __switchState(self, state, duration):
        log.debug(f"switching state to {state}, duration limit: {duration}")
        self.state = state
        self.stateBeginTime = datetime.datetime.now()
        if duration is None:
            self.stateEndTime = datetime.datetime.now()
        else:
            self.stateEndTime = self.stateBeginTime + datetime.timedelta(seconds=duration)

    def run(self):
        while True:
            self.__onTick()
            sleep(0.2)


if __name__ == '__main__':
    log.info("Starting")
    sm = StateMachine()
    sm.run()

import datetime
import sys
import threading
from enum import Enum
from time import sleep

import config
import gpio
import inputsmap
import log

import nfc
import server
import usb


class State(Enum):
    """Только запустились, еще ничего не сделали"""
    INIT = 1

    """Стоим закрытые ничего не делаем."""
    IDLE = 2

    """Открываем. Ждем пока активируется датчик открытия, чтобы потом начать ждать пока он деактивируется."""
    OPENING = 3

    """Стоим в открытом положении. Ждем пока сработает таймер на начало закрытия."""
    OPENED = 4

    """Движемся на закрытие. Ждем пока пройдет время, отведенное на закрытие."""
    CLOSING = 5

    """Находимся в закрытом положении и собираем данные по активации входов и наличию в поле UHF меток.
    Ждем пока пройдет установленное время на инвентаризацию."""
    INVENTORY = 6

    """Один из датчиков закрытия не сработал, нужно перезакрыть"""
    ONE_OF_TWO_ACTIVE = 7


class StateMachine:

    def __init__(self):
        self.mutex = threading.Lock()

        self.state = State.INIT
        log.debug(f"switching state to {self.state}")
        self.state_begin_time = None
        self.state_end_time = None
        self.time = 0  # for blink led

        self.card_uid = None
        self.inventory_pending = False

        self.gpio = gpio.Gpio()

        if self.gpio.is_close():
            self.gpio.green_off()
            self.gpio.red_on()
        else:
            self.gpio.red_off()
            self.gpio.green_on()

        if int(config.data['Nfc']['Active']) == 1:  # запускается ожидание nfc карточки
            self.nfc = nfc.Reader()
            self.nfc.on_read = self.__on_nfc_read

        self.server = server.Server()

        self.usb_ports = usb.Usb()
        self.usb_ports.on_card = self.__on_nfc_read
        self.usb_ports.start()

        if int(config.data['Inputs']['Remap']) == 1:
            self.__inputs_map = inputsmap.InputsMap()
        else:
            self.__inputs_map = None

        self.inventarization_durations = [
            int(duration) for duration in config.data['Inventory']['Duration'].replace(' ', '').split(',')
        ]
        self.inventarization_timeout = int(config.data['Inventory']['Timeout'])
        self.current_inventarization = 0
        self.inventory = []
        self.tags_inventory = []

    def __on_nfc_read(self, uid):
        """Срабатывает при чтении ключ-карты"""
        is_allowed = self.server.is_uid_allowed(uid)
        log.debug('Card has been attached')

        log.debug('access is allowed!')
        with self.mutex:
            if self.state == State.INVENTORY:
                self.__finish_inventory(unexpected=True)
            if self.state == State.INVENTORY or self.state == State.IDLE or self.state == State.ONE_OF_TWO_ACTIVE:
                self.card_uid = uid
                self.inventory_pending = True
                self.current_inventarization = 1
                log.debug(f'Cureent inventarization {self.current_inventarization}')
                self.__switch_state(State.OPENING, None)

            if not is_allowed:
                log.debug('not allowed :(')
                self.gpio.red_off()
                self.gpio.green_off()

                self.time = 0
                while self.time < 15:
                    self.gpio.blink_red()
                    sleep(0.1)
                    self.time += 1

    def __on_tick(self):
        with self.mutex:

            if self.state == State.INIT:

                if self.gpio.is_close() == 'reopen':
                    log.info('One of the sensors is inactive.')
                    self.gpio.open()
                    self.__switch_state(State.ONE_OF_TWO_ACTIVE, int(config.data['Motor']['DelayBeforeClose']))
                elif not self.gpio.is_close():
                    log.info("Starting with inactive close sensors. Closing.")
                    self.__switch_state(State.OPENED, None)
                else:
                    log.info("Starting with active close sensors.")
                    self.__switch_state(State.IDLE, None)

            elif self.state == State.IDLE:
                self.gpio.green_off()

                if not self.gpio.is_close():
                    self.current_inventarization = 1
                    self.inventory_pending = True
                    self.inventory = []
                    self.tags_inventory = []
                    self.__switch_state(State.OPENING, None)
                elif self.inventory_pending and datetime.datetime.now() >= self.state_end_time:
                    self.inventory_pending = False
                    self.usb_ports.start_uhf()

                    self.__switch_state(State.INVENTORY,
                                        self.inventarization_durations[self.current_inventarization - 1])

                if 0 < self.time < 15:
                    self.gpio.green_off()
                else:
                    self.gpio.red_on()

            elif self.state == State.OPENING:
                self.gpio.open()
                self.gpio.green_on()
                self.gpio.red_off()
                self.__switch_state(State.OPENED, int(config.data['Motor']['DelayBeforeClose']))

            elif self.state == State.OPENED:
                if self.gpio.is_close() == 'reopen':
                    if 0 < self.time < 15:
                        self.gpio.green_off()
                    else:
                        self.gpio.blink_green()
                        self.gpio.blink_green()
                elif self.gpio.is_close():
                    self.gpio.green_off()
                    self.gpio.red_on()
                elif not self.gpio.is_close():
                    self.gpio.red_off()
                    self.gpio.green_on()

                if datetime.datetime.now() >= self.state_end_time:
                    self.gpio.close()
                    self.__switch_state(State.CLOSING, None)

            elif self.state == State.CLOSING:
                if self.gpio.is_close() == 'reopen':
                    log.info('One of the sensors is not active, reopen the locker')
                    # self.gpio.open()
                    self.__switch_state(State.ONE_OF_TWO_ACTIVE, int(config.data['Motor']['DelayBeforeClose']))

                elif self.gpio.is_close():
                    self.gpio.green_off()
                    self.gpio.red_on()
                    self.__switch_state(State.IDLE, int(config.data['Inventory']['DelayBeforeInventarization']))

                if 0 < self.time < 15:
                    self.gpio.green_off()
                else:
                    self.gpio.green_on()

            elif self.state == State.INVENTORY:
                if datetime.datetime.now() >= self.state_end_time:
                    self.__finish_inventory()
                    self.__switch_state(State.IDLE, self.inventarization_timeout)

            elif self.state == State.ONE_OF_TWO_ACTIVE:
                self.gpio.close()
                if self.gpio.is_close() == 'reopen':
                    if 0 < self.time < 15:
                        self.gpio.green_off()
                    else:
                        self.gpio.red_off()
                        self.gpio.blink_green()
                elif self.gpio.is_close():
                    self.gpio.green_off()
                    self.gpio.red_on()
                    self.__switch_state(State.IDLE, int(config.data['Inventory']['DelayBeforeInventarization']))
                elif not self.gpio.is_close():
                    self.gpio.green_on()
                    self.__switch_state(State.OPENED, None)

    def __finish_inventory(self, unexpected=False):
        lodegments = self.usb_ports.get_inputs()
        log.debug(
            f'Finishing inventorization on {self.current_inventarization} iteration logements:{lodegments}, inputsMap: {self.__inputs_map}')
        if lodegments is not None and self.__inputs_map is not None:
            lodegments = self.__inputs_map.apply(lodegments)
            self.inventory += lodegments
        tags = self.usb_ports.stop_uhf()
        if tags is not None:
            self.tags_inventory += tags
        log.info(
            f"finishing inventory. card: {self.card_uid}, lodegments: {self.inventory}, tags: {list(set(self.tags_inventory))}")
        try:
            self.server.send_inventory(self.card_uid, list(set(self.inventory)), list(set(self.tags_inventory)))
        except Exception as e:
            log.error(f"finishing inventory. failed to send inventory update to the server: {e}")
        if self.current_inventarization == len(
                self.inventarization_durations) or unexpected or not self.current_inventarization:
            self.inventory = []
            self.tags_inventory = []
            self.current_inventarization = 0
        else:
            self.inventory_pending = True
            self.current_inventarization += 1

    def __switch_state(self, state, duration):
        log.debug(f"switching state to {state}, duration limit: {duration}")
        self.state = state
        self.state_begin_time = datetime.datetime.now()
        if duration is None:
            self.state_end_time = datetime.datetime.now()
        else:
            self.state_end_time = self.state_begin_time + datetime.timedelta(seconds=duration)

    def run(self):
        while True:
            self.__on_tick()
            sleep(0.2)


if __name__ == '__main__':
    log.info("Starting")
    sm = StateMachine()
    sm.run()

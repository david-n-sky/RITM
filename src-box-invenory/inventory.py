import datetime
import threading
import config
import gpio
import log
import usb
import server
from time import sleep


class Inventory():
    """"""

    def __init__(self, ):
        """Constructor for Inventory"""

        self.cardUid = None
        self.inventoryPending = False
        self.inventarization_durations = [int(duration) for duration in config.data['Inventory']['Duration'].split(',')]
        self.inventarization_timeout = [int(timeout) for timeout in config.data['Inventory']['Timeout'].split(',')]
        self.delay_before_inventory = int(config.data['Inventory']['DelayBeforeInventory'])
        self.current_inventarization = 0
        self.tags_inventory = []

        self.mutex = threading.Lock()

        self.usbPorts = usb.Usb()
        self.usbPorts.start()

        self.gpio = gpio.Gpio()
        self.gpio.onOpenSensorActivatedInv = self.__onOpenSensorActivated

        self.server = server.Server()

        t = threading.Thread(target=self.__run_inv())
        t.start()

    def __onOpenSensorActivated(self):
        with self.mutex:
            if self.inventoryPending:
                self.__finishInventory(unexpected=True)

            self.__set_time(self.delay_before_inventory)
            self.current_inventarization = 1
            self.inventoryPending = False

    def __startInventory(self):
        log.info("Inventory has begun")
        self.usbPorts.startUhf()
        self.gpio.pull_antenna(self.inventarization_durations[self.current_inventarization - 1])

    def __finishInventory(self, unexpected=False):
        log.debug(
            f'Finishing inventorization on {self.current_inventarization}')

        with open("last_card.txt", "r") as f:  # read the last applied card from file
            self.cardUid = f.read()

        tags = self.usbPorts.stopUhf()
        self.tags_inventory += tags
        log.info(
            f"finishing inventory. card: {self.cardUid}, tags: {list(set(self.tags_inventory))}")

        try:
            self.server.sendInventory(self.cardUid, list(set(self.tags_inventory)))
        except Exception as e:
            log.error(f"finishing inventory. failed to send inventory update to the server: {e}")

        if self.current_inventarization == len(
                self.inventarization_durations) or unexpected or not self.current_inventarization:
            self.tags_inventory = []
            self.current_inventarization = 0
        else:
            self.current_inventarization += 1

        self.inventoryPending = False

    def __set_time(self, duration=None):
        log.debug(f"Now inventory pending is {self.inventoryPending} and duration of stage is {duration} sec")
        self.BeginTime = datetime.datetime.now()
        if duration is None:
            self.EndTime = datetime.datetime.now()
        else:
            self.EndTime = self.BeginTime + datetime.timedelta(seconds=duration)

    def __run_inv(self):
        while True:
            with self.mutex:
                if self.current_inventarization and not self.inventoryPending and datetime.datetime.now() >= self.EndTime:  # timeout between inv
                    self.inventoryPending = True
                    self.__set_time(self.inventarization_durations[self.current_inventarization - 1])
                    self.__startInventory()

                elif self.inventoryPending and datetime.datetime.now() >= self.EndTime:  # inv
                    self.__finishInventory()
                    self.__set_time(self.inventarization_timeout[self.current_inventarization - 1])

            sleep(0.2)


if __name__ == '__main__':
    log.info("Starting inventory")
    inv = Inventory()

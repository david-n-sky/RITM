import glob
import subprocess
import config
import log
from enum import Enum
import threading
import time
import usb_generic
import usb_oldinputs
import usb_uhf

VENDOR_ID_PREFIX = "E: ID_VENDOR_ID="


class DeviceType(Enum):
    GENERIC = 1  # контроллер замка или ложемента, поддерживает команду T для определения что это
    OLD_INPUTS = 2  # старый контроллер ложемента, не поддерживает команду T
    UHF = 3  # UHF считыватель


class Device:
    def __init__(self, devType, impl):
        self.__devType = devType
        self.__impl = impl

    def getDevType(self):
        return self.__devType

    def start(self):
        self.__impl.start()

    def stop(self):
        self.__impl.stop()

    def isRunning(self):
        return self.__impl.isRunning()

    def sendOpen(self):
        if self.__devType == DeviceType.GENERIC:
            self.__impl.sendOpen()

    def getInput(self):
        if self.__devType == DeviceType.GENERIC:
            return self.__impl.getLastInputReport()
        elif self.__devType == DeviceType.OLD_INPUTS:
            return self.__impl.getLastInputReport()
        else:
            return None

    def startUhf(self):
        if self.__devType == DeviceType.UHF:
            self.__impl.startUhf()

    def stopUhf(self):
        if self.__devType == DeviceType.UHF:
            return self.__impl.stopUhf()
        return None


class Usb:
    def __init__(self):
        self.__vidToDeviceType = dict()
        self.__addVids('GenericPeripheral', DeviceType.GENERIC)
        self.__addVids('Inputs', DeviceType.OLD_INPUTS)
        self.__addVids('Uhf', DeviceType.UHF)
        log.debug(f"USB VID to Device type: {self.__vidToDeviceType}")

        self.__portToDevice = dict()
        self.__portToDeviceMutex = threading.Lock()

        self.onCard = None

    def start(self):
        t = threading.Thread(target=self.__runDetect)
        t.start()

    def __addVids(self, section, deviceType):
        for vid in config.data[section]['UsbVids'].split(' '):
            vid = vid.strip()
            if len(vid) > 0:
                self.__vidToDeviceType[vid] = deviceType

    def __runDetect(self):
        while True:
            ports = glob.glob('/dev/ttyUSB*')
            for port in ports:
                result = subprocess.run(['udevadm', 'info', port], stdout=subprocess.PIPE)
                out = result.stdout
                out = out.decode('utf-8')
                vid = None
                for line in out.split("\n"):
                    line = line.strip()
                    if line.startswith(VENDOR_ID_PREFIX):
                        vid = line[len(VENDOR_ID_PREFIX):]
                        break
                if vid is None:
                    log.debug(f"{port}: no vendor id in udevadm output")
                    continue
                devType = self.__vidToDeviceType.get(vid)
                if devType is None:
                    continue

                oldDev = None
                newDev = None
                with self.__portToDeviceMutex:
                    oldDev = self.__portToDevice.get(port)
                    if oldDev is None or oldDev.getDevType() != devType:
                        log.info(f"{port}: device type is now {devType}")
                        if oldDev is not None:
                            log.info(f"{port}: stopping old handler")
                            oldDev.stop()
                        newImpl = self.__createImpl(port, devType)
                        newDev = Device(devType, newImpl)
                        self.__portToDevice[port] = newDev
                if newDev is not None:
                    if oldDev is not None:
                        while oldDev.isRunning():
                            time.sleep(1)
                        log.info(f"{port}: old handler is now stopped")
                    log.info(f"{port}: starting the handler")
                    newDev.start()

            with self.__portToDeviceMutex:
                toDelete = []
                for port in self.__portToDevice:
                    if port not in ports:
                        log.info(f"{port}: port is not available anymore, stopping the handler")
                        oldDev = self.__portToDevice[port]
                        oldDev.stop()
                        while oldDev.isRunning():
                            time.sleep(1)
                        log.info(f"{port}: the handler is now stopped")
                        toDelete.append(port)
                for port in toDelete:
                    del self.__portToDevice[port]

            time.sleep(20)

    def __createImpl(self, port, devType):
        impl = None
        if devType == DeviceType.GENERIC:
            impl = usb_generic.Device(port)
            impl.onCard = self.__onCard
        elif devType == DeviceType.OLD_INPUTS:
            impl = usb_oldinputs.Device(port)
        elif devType == DeviceType.UHF:
            impl = usb_uhf.Device(port)
        return impl

    def __onCard(self, uid):
        if self.onCard is not None:
            self.onCard(uid)

    def sendOpen(self):
        with self.__portToDeviceMutex:
            for port, dev in self.__portToDevice.items():
                dev.sendOpen()

    def getInputs(self):
        res = []

        with self.__portToDeviceMutex:
            for port, dev in self.__portToDevice.items():
                imp = dev.getInput()
                if imp is not None:
                    res.append(imp)

        if len(res) > 0:
            return res
        else:
            return None

    def startUhf(self):
        with self.__portToDeviceMutex:
            for port, dev in self.__portToDevice.items():
                dev.startUhf()

    def stopUhf(self):
        with self.__portToDeviceMutex:
            for port, dev in self.__portToDevice.items():
                r = dev.stopUhf()
                if r is not None:
                    return r
        return None

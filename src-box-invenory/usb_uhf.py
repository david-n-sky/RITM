import config
import log
import struct
import serial
import os
import datetime
import threading
import time

DEBUG = False


def calcCrc(pkt):
    PRESET_VALUE = 0xFFFF
    POLYNOMIAL = 0x8408
    uiCrcValue = PRESET_VALUE
    for ucI in range(len(pkt)):
        uiCrcValue = uiCrcValue ^ (pkt[ucI] & 0xFF)
        for ucJ in range(8):
            if (uiCrcValue & 0x0001) != 0:
                uiCrcValue = (uiCrcValue >> 1) ^ POLYNOMIAL
            else:
                uiCrcValue = (uiCrcValue >> 1)
    return uiCrcValue


def createPkt(cmd, data):
    # Len Adr Cmd Data[] LSB-CRC16 MSB-CRC16
    pkt = struct.pack('BBB', len(data) + 4, 0xFF, cmd) + data
    pkt = pkt + struct.pack('<H', calcCrc(pkt))
    return pkt


def debugLog(s):
    if DEBUG:
        log.debug(s)


class Client:
    def __init__(self, port):
        self.ser = None
        self.port = port

    def __ensureOpen(self):
        if self.ser != None:
            return

        try:
            if self.port is None:
                raise RuntimeError('port is not set')

            antennas = config.data['Uhf']['Antennas'].strip().split(" ")
            antMask = 0x00
            for astr in antennas:
                a = int(astr)
                if a < 1 or a > 4:
                    raise RuntimeError(f"wrong antenna number in the .cfg: {a}")
                antMask = antMask | (1 << (a - 1))

            os.system(f"stty -F {self.port} -hupcl")

            self.ser = serial.Serial(
                port=self.port,
                baudrate=int(config.data['Uhf']['BaudRate']),
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                rtscts=False,
                dsrdtr=False,
                timeout=5,
                write_timeout=5)

            # set frequency
            self.__sendPkt(createPkt(0x22, b'\x4e00'))
            self.__expectPkt(0x22)

            # switch on antennas
            self.__sendPkt(createPkt(0x3F, struct.pack('B', antMask)))
            self.__expectPkt(0x3F)

            # buzz off
            self.__sendPkt(createPkt(0x40, struct.pack('B', 0)))
            self.__expectPkt(0x40)

            debugLog(f"open succ")
        except Exception as e:
            debugLog(f"open error: {e}")
            x = self.ser
            self.ser = None
            x.close()
            raise e

    def __sendPkt(self, pkt):
        self.__ensureOpen()
        debugLog(f"__sendPkt(). pkt: {pkt.hex()}")
        self.ser.write(pkt)
        self.ser.flush()

    def __recvPkt(self):
        self.__ensureOpen()

        pkt1 = self.ser.read(1)
        if len(pkt1) < 1:
            raise RuntimeError('timed out')

        pktLen = pkt1[0] + 1
        pkt2 = self.ser.read(pktLen - 1)
        if len(pkt2) < (pktLen - 1):
            raise RuntimeError('timed out')

        pkt = pkt1 + pkt2

        debugLog(f"__recvPkt(). pkt: {pkt.hex()}")
        return pkt

    def __expectPkt(self, cmd):
        t0 = datetime.datetime.now()
        while True:
            pkt = self.__recvPkt()
            if pkt[2] == cmd:
                return
            if datetime.datetime.now() - t0 > datetime.timedelta(seconds=5):
                raise RuntimeError('timed out')

    # Выполняет однократное сканирование. Возвращает список обнаруженных меток.
    def scan(self):
        reqPkt = createPkt(0x01, struct.pack('BB', 0x27, 0xff))
        self.__sendPkt(reqPkt)

        result = []

        t0 = datetime.datetime.now()
        while True:
            pkt = self.__recvPkt()

            # 0  1  2  3  4  5  6  7
            # 15 00 01 03 01 01 0c e280689400005005b2210861 4d 2f50
            # 07 00 01 01 01 00 1e 4b

            if pkt[2] != 1:
                raise RuntimeError('unexpected scan reply')

            if pkt[3] == 3:
                count = pkt[5]
                if count != 1:
                    raise RuntimeError(f"unexpected scan reply, count: {count}")

                numlen = pkt[6]
                if (7 + numlen + 1 + 2) != len(pkt):
                    raise RuntimeError(f"unexpected scan reply, wrong pkt length")

                num = pkt[7:7 + numlen].hex()

                result.append(num)
            elif pkt[3] == 1:
                return result

            if datetime.datetime.now() - t0 > datetime.timedelta(seconds=10):
                raise RuntimeError('timed out')


class Device:
    def __init__(self, port):
        self.__port = port
        self.__stop = False
        self.__isRunning = False

        self.client = Client(port)

        self.buffer = set()
        self.active = False
        self.mutex = threading.Lock()

    def start(self):
        self.__isRunning = True
        t = threading.Thread(target=self.__run)
        t.start()

    def stop(self):
        self.__stop = True

    def isRunning(self):
        return self.__isRunning

    def __run(self):
        while True:
            with self.mutex:
                _active = self.active

            if not _active:
                time.sleep(0.5)
                continue

            try:
                scanRes = self.client.scan()
            except Exception as e:
                debugLog(f"scan exception: {e}")
                time.sleep(5)
                continue

            with self.mutex:
                if self.active:
                    for x in scanRes:
                        self.buffer.add(x)

    # очищает буфер накопления меток.
    # запускает сканирование, если оно еще не запушено.
    def startUhf(self):
        log.debug("uhf: scan started")
        with self.mutex:
            self.buffer = set()
            self.active = True

    # останавливает сканирование.
    # возвращает накопленный список обнаруженных меток.
    # возвращает None, UHF если считывателя нет.
    def stopUhf(self):
        with self.mutex:
            result = self.buffer
            self.buffer = set()
            self.active = False

        if result is None:
            log.debug(f"uhf: scan stopped, result is None")
            return None
        else:
            log.debug(f"uhf: scan stopped, result size: {len(result)}")
            return list(result)

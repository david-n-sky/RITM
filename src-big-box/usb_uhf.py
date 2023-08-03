import datetime
import os
import serial
import struct
import threading
import time

import config
import log

DEBUG = False


def calc_crc(pkt):
    PRESET_VALUE = 0xFFFF
    POLYNOMIAL = 0x8408
    ui_crc_value = PRESET_VALUE
    for ucI in range(len(pkt)):
        ui_crc_value = ui_crc_value ^ (pkt[ucI] & 0xFF)
        for ucJ in range(8):
            if (ui_crc_value & 0x0001) != 0:
                ui_crc_value = (ui_crc_value >> 1) ^ POLYNOMIAL
            else:
                ui_crc_value = (ui_crc_value >> 1)
    return ui_crc_value


def create_pkt(cmd, data):
    # Len Adr Cmd Data[] LSB-CRC16 MSB-CRC16
    pkt = struct.pack('BBB', len(data) + 4, 0xFF, cmd) + data
    pkt = pkt + struct.pack('<H', calc_crc(pkt))
    return pkt


def debug_log(s):
    if DEBUG:
        log.debug(s)


class Client:
    def __init__(self, port):
        self.ser = None
        self.port = port

    def __ensure_open(self):
        if self.ser is not None:
            return

        try:
            if self.port is None:
                raise RuntimeError('port is not set')

            antennas = config.data['Uhf']['Antennas'].strip().split(" ")
            ant_mask = 0x00
            for astr in antennas:
                a = int(astr)
                if a < 1 or a > 4:
                    raise RuntimeError(f"wrong antenna number in the .cfg: {a}")
                ant_mask = ant_mask | (1 << (a - 1))

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
                write_timeout=5
            )

            """set frequency"""
            self.__send_pkt(create_pkt(0x22, b'\x4e00'))
            self.__expect_pkt(0x22)

            """switch on antennas"""
            self.__send_pkt(create_pkt(0x3F, struct.pack('B', ant_mask)))
            self.__expect_pkt(0x3F)

            """buzz off"""
            self.__send_pkt(create_pkt(0x40, struct.pack('B', 0)))
            self.__expect_pkt(0x40)

            debug_log(f"open success")
        except Exception as e:
            debug_log(f"open error: {e}")
            x = self.ser
            self.ser = None
            x.close()
            raise e

    def __send_pkt(self, pkt):
        self.__ensure_open()
        debug_log(f"__sendPkt(). pkt: {pkt.hex()}")
        self.ser.write(pkt)
        self.ser.flush()

    def __recv_pkt(self):
        self.__ensure_open()

        pkt_1 = self.ser.read(1)
        if len(pkt_1) < 1:
            raise RuntimeError('timed out')

        pkt_len = pkt_1[0] + 1
        pkt_2 = self.ser.read(pkt_len - 1)
        if len(pkt_2) < (pkt_len - 1):
            raise RuntimeError('timed out')

        pkt = pkt_1 + pkt_2

        debug_log(f"__recvPkt(). pkt: {pkt.hex()}")
        return pkt

    def __expect_pkt(self, cmd):
        t0 = datetime.datetime.now()
        while True:
            pkt = self.__recv_pkt()
            if pkt[2] == cmd:
                return
            if datetime.datetime.now() - t0 > datetime.timedelta(seconds=5):
                raise RuntimeError('timed out')

    """Выполняет однократное сканирование. Возвращает список обнаруженных меток."""

    def scan(self):
        req_pkt = create_pkt(0x01, struct.pack('BB', 0x27, 0xff))
        self.__send_pkt(req_pkt)

        result = []

        t0 = datetime.datetime.now()
        while True:
            pkt = self.__recv_pkt()

            # 0  1  2  3  4  5  6  7
            # 15 00 01 03 01 01 0c e280689400005005b2210861 4d 2f50
            # 07 00 01 01 01 00 1e 4b

            if pkt[2] != 1:
                raise RuntimeError('unexpected scan reply')

            if pkt[3] == 3:
                count = pkt[5]
                if count != 1:
                    raise RuntimeError(f"unexpected scan reply, count: {count}")

                num_len = pkt[6]
                if (7 + num_len + 1 + 2) != len(pkt):
                    raise RuntimeError(f"unexpected scan reply, wrong pkt length")

                num = pkt[7:7 + num_len].hex()

                result.append(num)
            elif pkt[3] == 1:
                return result

            if datetime.datetime.now() - t0 > datetime.timedelta(seconds=10):
                raise RuntimeError('timed out')


class Device:
    def __init__(self, port):
        self.__port = port
        self.__stop = False
        self.__is_running = False

        self.client = Client(port)

        self.buffer = set()
        self.active = False
        self.mutex = threading.Lock()

    def start(self):
        self.__is_running = True
        t = threading.Thread(target=self.__run)
        t.start()

    def stop(self):
        self.__stop = True

    def is_running(self):
        return self.__is_running

    def __run(self):
        while True:
            with self.mutex:
                _active = self.active

            if not _active:
                time.sleep(0.5)
                continue

            try:
                scan_res = self.client.scan()
            except Exception as e:
                debug_log(f"scan exception: {e}")
                time.sleep(5)
                continue

            with self.mutex:
                if self.active:
                    for x in scan_res:
                        self.buffer.add(x)

    """очищает буфер накопления меток.
	запускает сканирование, если оно еще не запушено."""

    def start_uhf(self):
        log.debug("uhf: scan started")
        with self.mutex:
            self.buffer = set()
            self.active = True

    """останавливает сканирование.
	возвращает накопленный список обнаруженных меток.
	# возвращает None, UHF если считывателя нет."""

    def stop_uhf(self):
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

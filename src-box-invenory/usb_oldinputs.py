import log
import threading
import json
import config
import time
import os
import serial


class Device:
    def __init__(self, port):
        self.__port = port
        self.__stop = False
        self.__isRunning = False

        self.__lastInputReport = None

    def start(self):
        self.__isRunning = True
        t = threading.Thread(target=self.__run)
        t.start()

    def stop(self):
        self.__stop = True

    def isRunning(self):
        return self.__isRunning

    def getLastInputReport(self):
        return self.__lastInputReport

    def __run(self):
        ser = None
        while True:
            if self.__stop:
                self.__isRunning = False
                return

            time.sleep(int(config.data['Inputs']['PollPeriod']))

            if self.__stop:
                self.__isRunning = False
                return

            try:
                if ser is None:
                    cmd = f"stty -F {self.__port} -hupcl"
                    os.system(cmd)
                    ser = serial.Serial(
                        port=self.__port,
                        baudrate=int(config.data['Inputs']['BaudRate']),
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        rtscts=False,
                        dsrdtr=False,
                        timeout=5,
                        write_timeout=5)

                ser.write('S'.encode())
                ser.flush()
                report = ser.readline()
                report = report.decode('utf-8')
                report = json.loads(report)
                self.__lastInputReport = report

            except Exception as e:
                ser = None
                self.__lastInputReport = None
                log.error(f"{self.__port}: port error: {e}")
                continue

import json
import os
import serial
import threading
import time

import config
import log


class Device:
	def __init__(self, port):
		self.__port = port
		self.__stop = False
		self.__is_running = False

		self.__last_input_report = None

	def start(self):
		self.__is_running = True
		t = threading.Thread(target=self.__run)
		t.start()

	def stop(self):
		self.__stop = True

	def is_running(self):
		return self.__is_running

	def get_last_input_report(self):
		return self.__last_input_report

	def __run(self):
		ser = None
		while True:
			if self.__stop:
				self.__is_running = False
				return

			time.sleep( int(config.data['Inputs']['PollPeriod']) )

			if self.__stop:
				self.__is_running = False
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
				self.__last_input_report = report
				
			except Exception as e:
				ser = None
				self.__last_input_report = None
				log.error(f"{self.__port}: port error: {e}")
				continue

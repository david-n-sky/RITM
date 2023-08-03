import datetime
import json
import os
import serial
import threading
import time
from enum import Enum

import config
import log

DEBUG = False


def debug_log(s):
	if DEBUG:
		log.debug(s)


class DeviceType(Enum):
	LOCK = 1
	INPUT = 2


class Device:
	def __init__(self, port):
		self.__port = port
		self.__type = None
		self.__stop = False
		self.__isRunning = False
		self.__ser = None
		
		self.on_card = None
		self.__last_input_report = None

	def start(self):
		self.__isRunning = True
		t = threading.Thread( target=self.__run)
		t.start()

	def stop(self):
		self.__stop = True

	def is_running(self):
		return self.__isRunning

	def get_last_input_report(self):
		if self.__type == DeviceType.INPUT:
			return self.__last_input_report
		else:
			return None

	def __run(self):
		debug_log(f"{self.__port}: scan started")

		last_get_type_time = None
		last_input_poll_time = None
		self.__waiting_for_poll_reply = False

		buffer = ""

		while True:
			if self.__stop:
				self.__isRunning = False
				return
			
			if self.__type is None or self.__type != DeviceType.INPUT:
				self.lastInputReport = None

			if self.__ser is None:
				try:
					cmd = f"stty -F {self.__port} -hupcl"
					os.system(cmd)
					self.__ser = serial.Serial(
						port=self.__port,
						baudrate=int(config.data['GenericPeripheral']['BaudRate']),
						parity=serial.PARITY_NONE,
						stopbits=serial.STOPBITS_ONE,
						bytesize=serial.EIGHTBITS,
						rtscts=False,
						dsrdtr=False,
						timeout=1,
						write_timeout=5)
					debug_log(f"{self.__port}: port opened")
				except Exception as e:
					self.__ser = None
					self.__type = None
					log.error(f"{self.__port}: port error: {e}")
					time.sleep(1)
					continue

			if self.__type is None or (last_get_type_time is not None and (datetime.datetime.now()-last_get_type_time).total_seconds() >= 60):
				try:
					debug_log(f"{self.__port}: sending T")
					self.__ser.write('T'.encode())
					self.__ser.flush()
					last_get_type_time = datetime.datetime.now()
				except Exception as e:
					log.error(f"{self.__port}: error sending T: {e}")
					self.__ser.close()
					self.__ser = None
					self.__type = None
					buffer = ""
					time.sleep(1)
					continue

			req_time_since_last_poll = 5 if self.__waiting_for_poll_reply else int(config.data['Inputs']['PollPeriod'])
			if self.__type == DeviceType.INPUT and (last_input_poll_time is None or (datetime.datetime.now()-last_input_poll_time).total_seconds() >= req_time_since_last_poll):
				try:
					debug_log(f"{self.__port}: sending S")
					self.__ser.write('S'.encode())
					self.__ser.flush()
					last_input_poll_time = datetime.datetime.now()
					self.__waiting_for_poll_reply = True
				except Exception as e:
					log.error(f"{self.__port}: error sending S: {e}")
					self.__ser.close()
					self.__ser = None
					self.__type = None
					buffer = ""
					time.sleep(1)
					continue

			try:
				received_data = self.__ser.read_until()
				if received_data is None or len(received_data) < 1:
					continue

				received_data = received_data.decode("utf-8")
				debug_log(f"{self.__port}: received: {received_data}")
				buffer = buffer + received_data

				while True:
					idx = buffer.find("\n")
					if idx < 0:
						break
					else:
						pkt = buffer[:idx]
						buffer = buffer[idx+1:]

						pkt = pkt.strip("\r\n")
						self.__process_incoming_report(pkt)

			except Exception as e:
				log.error(f"{self.__port}: error receiving data: {e}")
				# time.sleep(5) # TODO
				self.__ser.close()
				self.__ser = None
				self.__type = None
				buffer = ""
				time.sleep(1)
				continue

			if self.__type is None:
				time.sleep(1)
				continue

	def __process_incoming_report(self, report):
		report = json.loads(report)

		if 'type' in report:
			new_type = None
			if report["type"] == "lock":
				new_type = DeviceType.LOCK
			elif report["type"] == "input":
				new_type = DeviceType.INPUT
			else:
				log.error(f"{self.__port}: unknown type")
				return
			if self.__type != new_type:
				log.info(f"{self.__port}: new type is: {new_type}")
				self.__type = new_type

		elif 'card' in report:
			if self.on_card is not None:
				self.on_card(report['card'])

		elif 'placement' in report:
			self.__last_input_report = report
			self.__waiting_for_poll_reply = False

	def send_open(self):
		if self.__type != DeviceType.LOCK or self.__ser is None:
			return

		log.info(f"{self.__port}: sendOpen()")

		try:
			self.__ser.write('O'.encode())
			self.__ser.flush()
		except Exception as e:
			log.error(f"{self.__port}: error sending open cmd: {e}")

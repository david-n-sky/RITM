
import os
import log
import serial
from enum import Enum
import threading
import json
import time
import config
import datetime

DEBUG = False
def debugLog(s):
	if DEBUG:
		log.debug(s)

class DeviceType(Enum):
	LOCK = 1
	INPUT = 2

class Device:
	def __init__(self,port):
		self.__port = port
		self.__type = None
		self.__stop = False
		self.__isRunning = False
		self.__ser = None
		
		self.onCard = None
		self.__lastInputReport = None

	def start(self):
		self.__isRunning = True
		t = threading.Thread( target=self.__run )
		t.start()

	def stop(self):
		self.__stop = True

	def isRunning(self):		
		return self.__isRunning

	def getLastInputReport(self):
		if self.__type == DeviceType.INPUT:
			return self.__lastInputReport
		else:
			return None

	def __run(self):
		debugLog( f"{self.__port}: scan started" )

		lastGetTypeTime = None
		lastInputPollTime = None
		self.__waitingForPollReply = False

		buffer = ""

		while True:
			if self.__stop:
				self.__isRunning = False
				return
			
			if self.__type is None or self.__type!=DeviceType.INPUT:
				self.lastInputReport = None

			if self.__ser is None:
				try:
					cmd = f"stty -F {self.__port} -hupcl"
					os.system( cmd )
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
					debugLog( f"{self.__port}: port opened" )
				except Exception as e:
					self.__ser = None
					self.__type = None
					log.error( f"{self.__port}: port error: {e}" )
					time.sleep(1)
					continue

			if self.__type is None or (lastGetTypeTime is not None and (datetime.datetime.now()-lastGetTypeTime).total_seconds() >= 60):
				try:
					debugLog( f"{self.__port}: sending T" )
					self.__ser.write('T'.encode())
					self.__ser.flush()
					lastGetTypeTime = datetime.datetime.now()
				except Exception as e:
					log.error( f"{self.__port}: error sending T: {e}" )
					self.__ser.close()
					self.__ser = None
					self.__type = None
					buffer = ""
					time.sleep(1)
					continue

			reqTimeSinceLastPoll = 5 if self.__waitingForPollReply else int(config.data['Inputs']['PollPeriod'])
			if self.__type==DeviceType.INPUT and (lastInputPollTime is None or (datetime.datetime.now()-lastInputPollTime).total_seconds() >= reqTimeSinceLastPoll ):
				try:
					debugLog( f"{self.__port}: sending S" )
					self.__ser.write('S'.encode())
					self.__ser.flush()
					lastInputPollTime = datetime.datetime.now()
					self.__waitingForPollReply = True
				except Exception as e:
					log.error( f"{self.__port}: error sending S: {e}" )
					self.__ser.close()
					self.__ser = None
					self.__type = None
					buffer = ""
					time.sleep(1)
					continue

			try:
				receivedData = self.__ser.read_until()
				if receivedData is None or len(receivedData)<1:
					continue

				receivedData = receivedData.decode("utf-8")
				debugLog( f"{self.__port}: received: {receivedData}" )
				buffer = buffer + receivedData

				while True:
					idx = buffer.find("\n")
					if idx<0:
						break
					else:
						pkt = buffer[:idx]
						buffer = buffer[idx+1:]

						pkt = pkt.strip("\r\n")
						self.__processIncomingReport(pkt)

			except Exception as e:
				log.error( f"{self.__port}: error receiving data: {e}" )
				#time.sleep(5) # TODO
				self.__ser.close()
				self.__ser = None
				self.__type = None
				buffer = ""
				time.sleep(1)
				continue

			if self.__type is None:
				time.sleep(1)
				continue

	def __processIncomingReport(self,report):
		report = json.loads(report)

		if 'type' in report:
			newType = None
			if report["type"]=="lock":
				newType = DeviceType.LOCK
			elif report["type"]=="input":
				newType = DeviceType.INPUT
			else:
				log.error( f"{self.__port}: unknown type" )
				return
			if self.__type != newType:
				log.info( f"{self.__port}: new type is: {newType}" )
				self.__type = newType

		elif 'card' in report:
			if self.onCard is not None:
				self.onCard( report['card'] )

		elif 'placement' in report:
			self.__lastInputReport = report
			self.__waitingForPollReply = False

	def sendOpen(self):
		if self.__type != DeviceType.LOCK or self.__ser is None:
			return

		log.info( f"{self.__port}: sendOpen()" )

		try:
			self.__ser.write('O'.encode())
			self.__ser.flush()
		except Exception as e:
			log.error( f"{self.__port}: error sending open cmd: {e}" )

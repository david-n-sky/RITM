import glob
import subprocess
import threading
import time
from enum import Enum

import config
import log
import usb_generic
import usb_oldinputs
import usb_uhf

VENDOR_ID_PREFIX = "E: ID_VENDOR_ID="


class DeviceType(Enum):
	GENERIC    = 1 # контроллер замка или ложемента, поддерживает команду T для определения, что это
	OLD_INPUTS = 2 # старый контроллер ложемента, не поддерживает команду T
	UHF        = 3 # UHF считыватель


class Device:
	def __init__(self, dev_type, impl):
		self.__dev_type = dev_type
		self.__impl = impl

	def get_dev_type(self):
		return self.__dev_type

	def start(self):
		self.__impl.start()		

	def stop(self):
		self.__impl.stop()

	def is_running(self):
		return self.__impl.is_running()

	def send_open(self):
		if self.__dev_type == DeviceType.GENERIC:
			self.__impl.send_open()

	def get_input(self):
		if self.__dev_type == DeviceType.GENERIC:
			return self.__impl.get_last_input_report()
		elif self.__dev_type == DeviceType.OLD_INPUTS:
			return self.__impl.get_last_input_report()
		else:
			return None

	def start_uhf(self):
		if self.__dev_type == DeviceType.UHF:
			self.__impl.start_uhf()

	def stop_uhf(self):
		if self.__dev_type == DeviceType.UHF:
			return self.__impl.stop_uhf()
		return None


class Usb:
	def __init__(self):
		self.__vidToDeviceType = dict()
		self.__add_vids('GenericPeripheral', DeviceType.GENERIC)
		self.__add_vids('Inputs', DeviceType.OLD_INPUTS)
		self.__add_vids('Uhf', DeviceType.UHF)
		log.debug(f"USB VID to Device type: {self.__vidToDeviceType}")

		self.__port_to_device = dict()
		self.__port_to_device_mutex = threading.Lock()

		self.on_card = None

	def start(self):
		t = threading.Thread(target=self.__run_detect)
		t.start()

	def __add_vids(self, section, device_type):
		for vid in config.data[section]['UsbVids'].split(' '):
			vid = vid.strip()
			if len(vid)>0:
				self.__vidToDeviceType[vid] = device_type

	def __run_detect(self):
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
				dev_type = self.__vidToDeviceType.get(vid)
				if dev_type is None:
					continue
				
				old_dev = None
				new_dev = None
				with self.__port_to_device_mutex:
					old_dev = self.__port_to_device.get(port)
					if old_dev is None or old_dev.get_dev_type() != dev_type:
						log.info(f"{port}: device type is now {dev_type}")
						if old_dev is not None:
							log.info(f"{port}: stopping old handler")
							old_dev.stop()
						new_impl = self.__create_impl(port, dev_type)
						new_dev = Device(dev_type, new_impl)
						self.__port_to_device[port] = new_dev
				if new_dev is not None:
					if old_dev is not None:
						while old_dev.is_running():
							time.sleep(1)
						log.info(f"{port}: old handler is now stopped")
					log.info(f"{port}: starting the handler")
					new_dev.start()

			with self.__port_to_device_mutex:
				to_delete = []
				for port in self.__port_to_device:
					if port not in ports:
						log.info(f"{port}: port is not available anymore, stopping the handler")
						old_dev = self.__port_to_device[port]
						old_dev.stop()
						while old_dev.is_running():
							time.sleep(1)
						log.info(f"{port}: the handler is now stopped")
						to_delete.append(port)
				for port in to_delete:
					del self.__port_to_device[port]

			time.sleep(20)

	def __create_impl(self, port, devType):
		impl = None
		if devType == DeviceType.GENERIC:
			impl = usb_generic.Device(port)
			impl.on_card = self.__on_card
		elif devType == DeviceType.OLD_INPUTS:
			impl = usb_oldinputs.Device(port)
		elif devType == DeviceType.UHF:
			impl = usb_uhf.Device(port)
		return impl

	def __on_card(self, uid):
		if self.on_card is not None:
			self.on_card(uid)

	def send_open(self):
		with self.__port_to_device_mutex:
			for port, dev in self.__port_to_device.items():
				dev.send_open()

	def get_inputs(self):
		res = []

		with self.__port_to_device_mutex:
			for port, dev in self.__port_to_device.items():
				imp = dev.get_input()
				if imp is not None:
					res.append(imp)

		if len(res) > 0:
			return res
		else:
			return None

	def start_uhf(self):
		with self.__port_to_device_mutex:
			for port, dev in self.__port_to_device.items():
				dev.start_uhf()

	def stop_uhf(self):
		with self.__port_to_device_mutex:
			for port, dev in self.__port_to_device.items():
				r = dev.stop_uhf()
				if r is not None:
					return r
		return None

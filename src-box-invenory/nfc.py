
import log
import time
import config
import threading
import uuid

from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *
 
DOUBLE_READ_PERIOD = 1

class Reader:
	def __init__(self):
		chan = 0 if config.data['Board']['Type']=='Orange' else 1

		self.lastUid = None
		self.lastUidTime = None
		self.pn532 = Pn532_i2c( i2c_channel=chan )
		self.pn532.SAMconfigure()

		self.onRead = None

		t = threading.Thread( target=self.__run )
		t.start()

	def __waitForTag(self):

		while True:
			card_data = self.pn532.read_mifare().get_data()

			#card_data = bytearray([0x4b,0x01,0x01,0x00,0x04,0x08,0x04,0xdc,0x57,0x43,0x49])

			# 0  1  2  3  4  5  6  7  8  9  10
			# 4b 01 01 00 04 08 04 dc 57 43 49
			#    c  #  atqa? sa    uid........
	
			uid = None
			if isinstance(card_data,bytearray) and len(card_data)>=11 and card_data[0]==0x4B and card_data[1]==0x01 and card_data[6]>=4 and len(card_data)>=(7+card_data[6]):
				uid = card_data[7:7+card_data[6]]
				uid = bytes(uid).hex().upper()

			#print("DEBUG: uid:",uid)

			if uid is not None and uid==self.lastUid and (time.time()-self.lastUidTime)<DOUBLE_READ_PERIOD:
				time.sleep(1)
				self.lastUidTime = time.time()
				continue

			self.lastUid = uid
			self.lastUidTime = time.time()

			log.debug( f'nfc uid read: {uid}' )
			return uid

	def __run(self):
		while True:
			uid = self.__waitForTag()
			uuuid = str(uuid.uuid3(uuid.NAMESPACE_X500, uid.upper()))
			if self.onRead!=None:
				self.onRead(uuuid)

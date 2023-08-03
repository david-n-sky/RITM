"""pip3 install Adafruit-Blinka
pip3 install adafruit-circuitpython-pn532
sudo apt-get install libgpiod2 python3-libgpiod
pip3 install gpiod
pip3 install psutil"""
import sys

import board
import busio
from digitalio import DigitalInOut

import subprocess
import signal
import os

from adafruit_pn532.i2c import PN532_I2C

try:
    i2c = busio.I2C(board.SCL, board.SDA)

    pn532 = PN532_I2C(i2c, debug=False)

    # Проверка наличия PN532
    ic, ver, rev, support = pn532.firmware_version
    print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
    print('PN532 found on I2C bus')

except Exception as e:
    print('PN532 not found on I2C bus')
    # тут вырубаем main + запускаем запасной main
    pids = []

    for pid in os.listdir('/proc'):  # get all python processes
        try:
            pid = int(pid)
            if open(os.path.join('/proc', str(pid), 'cmdline'), 'rb').read().find(b'python') != -1:
                pids.append(pid)
        except ValueError:
            pass

    now_pid = os.getpid()

    for pid in pids:
        if pid != now_pid:
            os.kill(pid, signal.SIGINT)

    print('killed all!')
    print('starting fallback script...')
    proc = subprocess.Popen([sys.executable, 'main_broken_nfc.py'])


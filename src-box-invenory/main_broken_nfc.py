import time
import gpio

gpio = gpio.Gpio()

if not gpio.isOpen():
    gpio.open()
    time.sleep(3)
    gpio.stop()

while True:
    gpio.blink_red_green()
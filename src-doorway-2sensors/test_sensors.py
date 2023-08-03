import time
import gpio

g = gpio.Gpio()


def printState():
    entry = g.isEntryActive()
    exit = g.isExitActive()
    print(f"entry: {entry}, exit: {exit}")


print(1)
g.onSensorChanged = printState
printState()
while True:
    time.sleep(1)

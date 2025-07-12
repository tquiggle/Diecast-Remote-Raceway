#!/usr/bin/python3

import bluetooth
import time
from gpiozero import *

NANOSECONDS_TO_SECONDS = 1000000000.0

target_name = "FinishLine"
target_address = None
port = 1
sock = None

nearby_devices = bluetooth.discover_devices()

for bdaddr in nearby_devices:
    if target_name == bluetooth.lookup_name(bdaddr):
        target_address = bdaddr
        break

if target_address is None:
    print ("could not find FinishLine nearby")
else:
    print ("Found FinishLine, connecting...")
    sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    sock.connect((target_address, port))
    print ("Connected to finish line")
    sock.send("HELO", 6)

numLanes = 2		# Make configurable via UI
lane1 = DigitalInputDevice("GPIO07", True)
lane2 = DigitalInputDevice("GPIO23", True)
lane3 = DigitalInputDevice("GPIO22", True)
lane4 = DigitalInputDevice("GPIO04", True)
servo = Servo("GPIO12", 0)

def resetStartingGate():
    servo.min()

def releaseStartingGate():
    servo.max()

def allLanesReady():
    return (lane1.value + lane2.value) == 0

# TODO: Handle Bluetooth disconnect and reconnect
#       Write input parser to deal with picking up multiple messages at once
#       Clean up startup process
#         * After exchanging HELLO messages, request version from FL
#         * Do version check on SG
#         * Only if update needed, send UPFW command w/ bluetooth SSID and password
#       Send WiFI parameters to finish line

while True:
    try:
        print ("lane1 = ", lane1.value)
        print ("lane2 = ", lane2.value)

        while (not allLanesReady()):
            prinnt("Waiting for cars at the gate")
            time.sleep(1)

        print ("All Lanes Ready. Start the race");
        releaseStartingGate()
        start = time.monotonic_ns()

        lanesComplete = 0;
        while (lanesComplete < numLanes):
            data = sock.recv(1024)   # Add timeout
            if len(data) == 0: break
            str = data.decode('utf-8')
            print("received ", str)

            if (str.startswith("LANE1")):
                end = time.monotonic_ns()
                delta = float (end - start) / NANOSECONDS_TO_SECONDS
                print ("Lane 1 finished. Elapsed time: %6.3f" % delta)
                lanesComplete = lanesComplete + 1

            if (str.startswith("LANE2")):
                end = time.monotonic_ns()
                delta = float (end - start) / NANOSECONDS_TO_SECONDS
                print ("Lane 2 finished. Elapsed time: %6.3f" % delta)
                lanesComplete = lanesComplete + 1

    except IOError:
        pass

print("disconnected")
print("all done")

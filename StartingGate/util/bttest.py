#!/usr/bin/python3

"""
Small utility program to monitor Bluetooth transmissions from FinishLine.

bttest sends an initial BGIN command which should enable the FinishLine to send lane completion
messages. A car covering a finish line lanes should send a FIN# message that will be displayed.
"""

import bluetooth
import sys
import time

NANOSECONDS_TO_SECONDS = 1000000000.0

target_name = "FinishLine"
target_address = None
port = 1;

nearby_devices = bluetooth.discover_devices()

for bdaddr in nearby_devices:
    if target_name == bluetooth.lookup_name( bdaddr ):
        target_address = bdaddr
        break

if target_address is None:
    print ("could not find target bluetooth device nearby")
    sys.exit(1)

sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
sock.connect((target_address, port))
print ("Connected to finish line")

start = time.monotonic_ns()

sock.send("BGIN")
try:
    while True:
        data = sock.recv(1024)
        if len(data) == 0: break
        str = data.decode('utf-8')
        print("received ", str)
        if (str.startswith("FIN")):
                end = time.monotonic_ns()
                delta = float (end - start) / NANOSECONDS_TO_SECONDS
                print ("delta: %6.3f" % delta)

except IOError:
    pass

print("disconnected")

sock.close()
server_sock.close()
print("all done")

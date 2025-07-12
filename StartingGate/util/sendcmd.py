#!/usr/bin/python3

import bluetooth
import sys

target_name = "FinishLine"
target_address = None
port = 1;

command = sys.argv[1]

nearby_devices = bluetooth.discover_devices()

print("Connecting to ", target_name)
for bdaddr in nearby_devices:
    if target_name == bluetooth.lookup_name( bdaddr ):
        target_address = bdaddr
        break

if target_address is None:
    print ("could not find target bluetooth device nearby")
else:
    sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    sock.connect((target_address, port))
    print("Sending: ", command)
    sock.send(command)
    data = sock.recv(1024)
    str = data.decode('utf-8')
    print("received ", str)



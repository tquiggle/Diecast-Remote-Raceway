#!/usr/bin/python3

import bluetooth
import datetime

target_name = "FinishLine"
target_address = None
port = 1;

print("calling discover_devices")
start_time = datetime.datetime.now()
print("start_time=", start_time)
nearby_devices = bluetooth.discover_devices(duration=5, flush_cache=True, lookup_names=True)
print("back from discover_devices")

print("nearby_devices=", nearby_devices)

for bdaddr,bdname in nearby_devices:
    print("Found device ", bdname, bdaddr)
    end_time = datetime.datetime.now()
    if bdname == target_name:
        target_address = bdaddr
        print("back from discover_devices")
        delta = end_time - start_time
        print("delta = ", delta)
        break

if target_address is None:
    print ("could not find target bluetooth device nearby")

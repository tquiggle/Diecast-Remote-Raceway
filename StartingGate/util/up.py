#!/usr/bin/python3

"""
Raise starting gate lever
"""

from time import sleep
from gpiozero import Device, Servo
from gpiozero.pins.pigpio import PiGPIOFactory

Device.pin_factory = PiGPIOFactory()

servo = Servo("GPIO12", 0)

while True:
    print("Mid")
    servo.mid()
    sleep(10)

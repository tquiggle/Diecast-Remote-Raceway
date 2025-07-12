#!/usr/bin/python3

"""
Small test program that cycles the servo from its min, mid and max offsets.

Used to dial in the right values for the min and max pulse_width and frame_width
parameters to the Servo class initializer.
"""

from gpiozero import *;
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# Use PiGPIOFactory for hardware PWM support to prevent servo jitter
Device.pin_factory = PiGPIOFactory()

servo = Servo("GPIO12", 0.0, 0.0005, 0.0025)

print ("min_pulse_width", servo.min_pulse_width)
print ("max_pulse_width", servo.max_pulse_width)
print ("pulse_width", servo.pulse_width)
print ("frame_width", servo.frame_width)

while True:
    print("Min")
    servo.min()
    sleep(1)
    print("Mid")
    servo.mid()
    sleep(1)
    print("Max")
    servo.max()
    sleep(1)


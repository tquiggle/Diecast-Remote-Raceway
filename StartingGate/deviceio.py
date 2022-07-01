"""
Diecast Remote Raceway - DeviceIO

DeviceIO is the interface to the physical input/output devices attached to
the GPIO, excluding the LCD display which is managed separately.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

from gpiozero import Device, DigitalInputDevice, Button, Servo
from gpiozero.pins.pigpio import PiGPIOFactory

# Use PiGPIOFactory for hardware PWM support to prevent servo jitter
Device.pin_factory = PiGPIOFactory()

#
# Pin assignments were made to simplify the wiring layout of the Prototyping pHAT,
# not to make the code clearer.
#
# Also, I don't care what the Python style guide says, I find the following aligned
# layout MUCH more readable than the pythonic spacing.
#
# pylint: disable=bad-whitespace

JOYU =  Button("GPIO6",  True, None, 0.020)                    # Pin 31
JOYD =  Button("GPIO19", True, None, 0.020)                    # Pin 35
JOYL =  Button("GPIO5",  True, None, 0.020)                    # Pin 29
JOYR =  Button("GPIO26", True, None, 0.020)                    # Pin 37
JOYP =  Button("GPIO13", True, None, 0.020)                    # Pin 33

KEY_1 = Button("GPIO21", True, None, 0.100)                    # Pin 40
KEY_2 = Button("GPIO20", True, None, 0.100)                    # Pin 38
KEY_3 = Button("GPIO16", True, None, 0.100)                    # Pin 36

LANE1 = DigitalInputDevice("GPIO7",  True, None, 0.200)        # Pin 26
LANE2 = DigitalInputDevice("GPIO23", True, None, 0.200)        # Pin 16
LANE3 = DigitalInputDevice("GPIO22", True, None, 0.200)        # Pin 15
LANE4 = DigitalInputDevice("GPIO4",  True, None, 0.200)        # Pin 07

SERVO = Servo("GPIO12")                                        # Pin 32

# pylint: enable=bad-whitespace

def car_1_present():
    """
    Returns True if the LANE1 sensor detects a car in the lane 1 starting gate
    """
    return LANE1.value

def car_2_present():
    """
    Returns True if the LANE2 sensor detects a car in the lane 2 starting gate
    """
    return LANE2.value

def car_3_present():
    """
    Returns True if the LANE3 sensor detects a car in the lane 3 starting gate
    """
    return LANE3.value

def car_4_present():
    """
    Returns True if the LANE4 sensor detects a car in the lane 4 starting gate
    """
    return LANE4.value

def default_key_1_handler():
    """
    Default handler to call when key 1 is pressed and no application handler is registered
    """
    print("Default KEY_1_handler")

def default_key_2_handler():
    """
    Default handler to call when key 2 is pressed and no application handler is registered
    """
    print("Default KEY_2_handler")

def default_key_3_handler():
    """
    Default handler to call when key 3 is pressed and no application handler is registered
    """
    print("Default KEY_3_handler")

def default_joystick_handler(btn):
    """
    Default handler to call when the joystick is pressed and no application handler is registered
    """
    print("Default joystick_handler", btn)

class DeviceIO:
    """
    The DeviceIO class maintains a stack of handler functions for
    the joystick and buttons.  There is a single handler for the
    joystick that needs to consult the "btn" paramater to determine
    what motion was present.

    When entering an input mode that needs the input devices (e.g. text
    input), the caller pushes new handlers onto a stack so all user
    interaction is directed to the contextually appropriate routines.
    It is the caller's responsibility to pop the handlers it pushed
    when returning to the previous input mode.

    """

# PUBLIC:
    def push_key_handlers(self, key_1_fn, key_2_fn, key_3_fn, joystick):
        """
        Push new set of handlers for the input keys onto the handler stack
        """
        print("DeviceIO.push_key_handlers, self=", self, " instance=", DeviceIO.instance)
        DeviceIO.instance.push_key_handlers(key_1_fn, key_2_fn, key_3_fn, joystick)

    def pop_key_handlers(self):
        """
        Pop current set of handlers for the input keys from the handler stack
        """
        print("DeviceIO.pop_key_handlers, self=", self, " instance=", DeviceIO.instance)
        DeviceIO.instance.pop_key_handlers()

# PRIVATE:

    instance = None

    class __DeviceIOSingleton: #pylint: disable=invalid-name

        def push_key_handlers(self, key_1_fn, key_2_fn, key_3_fn, joystick):
            """
            Push new set of keypress callback functions onto the appropriate stacks
            """
            print("DeviceIOSingleton.push_key_handlers: key_1_fn=", key_1_fn)
            self.key_1_stack.append(key_1_fn)
            self.key_2_stack.append(key_2_fn)
            self.key_3_stack.append(key_3_fn)
            self.joystick_stack.append(joystick)

        def pop_key_handlers(self):
            """
            Pop the most recently pu7shed set of callback functions, returning control
            to the prior set.
            """
            print("DeviceIOSingleton.pop_key_handlers, self=", self)
            self.key_1_stack.pop()
            self.key_2_stack.pop()
            self.key_3_stack.pop()
            self.joystick_stack.pop()

        def __init__(self):
            print("DeviceIOSingleton.__init__: self=", self)

            # Initialize the key callback stacks with default handlers
            # that just report key presses to stdout
            self.key_1_stack = [default_key_1_handler]
            self.key_2_stack = [default_key_2_handler]
            self.key_3_stack = [default_key_3_handler]
            self.joystick_stack = [default_joystick_handler]

            # Initialize each key to call the appropriate dispatch
            # function when the key is pressed
            KEY_1.when_pressed = self.__key_1_dispatcher
            KEY_2.when_pressed = self.__key_2_dispatcher
            KEY_3.when_pressed = self.__key_3_dispatcher

            JOYU.when_pressed = self.__joystick_dispatcher
            JOYD.when_pressed = self.__joystick_dispatcher
            JOYL.when_pressed = self.__joystick_dispatcher
            JOYR.when_pressed = self.__joystick_dispatcher
            JOYP.when_pressed = self.__joystick_dispatcher

        def __key_1_dispatcher(self):
            print("__KEY_1_dispatcher, calling ", self.key_1_stack[-1])
            self.key_1_stack[-1]()

        def __key_2_dispatcher(self):
            print("__KEY_2_dispatcher, calling ", self.key_2_stack[-1])
            self.key_2_stack[-1]()

        def __key_3_dispatcher(self):
            print("__KEY_3_dispatcher, calling ", self.key_3_stack[-1])
            self.key_3_stack[-1]()

        def __joystick_dispatcher(self, btn):
            self.joystick_stack[-1](btn)

    def __init__(self):
        if not DeviceIO.instance:
            DeviceIO.instance = DeviceIO.__DeviceIOSingleton()
            print("DeviceIO.__init__: created instance", DeviceIO.instance)

    def __getattr__(self, item):
        return getattr(self.instance, item)

# vim: expandtab sw=4

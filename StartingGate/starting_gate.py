#!/usr/bin/python3

"""
Starting Gate:

    The Starting Gate is responsible for running Diecast Remote Raceway races.
    It coordinates with the Finish Line component to run races locally, and the
    Race Coordinator for multi-track races.

 TODO:
       Clean up startup process
         * After exchanging HELLO messages, request version from FL
         * Do version check on SG
         * Only if update needed, send UPFW command w/ bluetooth SSID and password
       Send encoded WiFI parameters to Finish Line if firmware update needed

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import json
import operator
import select
import time
import traceback

import bluetooth
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4

from config import Config, NOT_FINISHED
from coordinator import Coordinator
from display import Display
from finishline import FinishLine

# Globals (yea, I know)
#pylint: disable=invalid-name
race_aborted = False # Set by key_pressed callback to reset race state

NANOSECONDS_TO_SECONDS = 1000000000

def key_pressed():
    """
    Callback invoked when a key is pressed after exiting the top level menu.
    Sets global race_aborted state to exit the current race at the earliest
    convenience and return to the top level menu.
    """
    print("key_pressed(): Setting race_aborted to True")
    global race_aborted #pylint: disable=global-statement
    race_aborted = True

def reset_starting_gate(config):
    """ Set servo to midpoint position to close the starting gate """
    SERVO.value = config.servo_up_value
    time.sleep(0.1)
    SERVO.value = None  # Stop PWM signal to servo to prevent humm/jitter and reduce wear

def release_starting_gate(config):
    """ Set servo to max position to release the starting gate """
    SERVO.value = config.servo_down_value

def all_lanes_empty(config):
    """ Scan the lane sensors to see if any lanes have cars present. """
    num_lanes = config.num_lanes

    if num_lanes == 1:
        return LANE1.value == 0
    if num_lanes == 2:
        return LANE1.value + LANE2.value == 0
    if num_lanes == 3:
        return LANE1.value + LANE2.value + LANE3.value == 0
    if num_lanes == 4:
        return LANE1.value + LANE2.value + LANE3.value + LANE4.value == 0
    return 0 # Dead code, but makes pylint happy

def wait_for_car_in_lane(config):
    """ Wait for at least one car to be placed in a lane """
    global race_aborted #pylint: disable=global-statement,global-variable-not-assigned
    while all_lanes_empty(config):
        if race_aborted:
            return
        time.sleep(0.1)


def all_lanes_ready(config):
    """ Scan the lane sensors to see if all lanes have cars present. """

    num_lanes = config.num_lanes

    if num_lanes == 1:
        return LANE1.value == 1
    if num_lanes == 2:
        return LANE1.value + LANE2.value == 2
    if num_lanes == 3:
        return LANE1.value + LANE2.value + LANE3.value == 3
    if num_lanes == 4:
        return LANE1.value + LANE2.value + LANE4.value == 4
    return 0 # Dead code, but makes pylint happy

def calculate_results(config, coordinator, finish_times):
    """ Create results dictionary sorted by finish time. """
    num_lanes = config.num_lanes
    results = []

    for lane in range(num_lanes):
        result = {}
        result["trackName"] = config.track_name
        result["laneNumber"] = lane + 1
        result["laneTime"] = finish_times[lane]
        results.append(result)

    results.sort(key=operator.itemgetter('laneTime'))

    # Send local results to race coordinator and await global results
    if config.multi_track:
        results_string = coordinator.results(results)
        results = json.loads(results_string)

    return results


def run_race(config, coordinator, display, finish_line):
    """
    Run a race

    Args:
        config      Config object with current race configuration
        coordinator Coordinator object for communicating
        display     Display object to manage display of race state
        finish_line FinishLine object to communicate with the FinishLine
    """

    global race_aborted #pylint: disable=global-statement,global-variable-not-assigned
    num_lanes = config.num_lanes
    finish_times = [NOT_FINISHED, NOT_FINISHED, NOT_FINISHED, NOT_FINISHED]

    def lane_index(msg):
        """
        Convert finished message received from the Finish Line to a lane index.

        Lanes are named Lane1 through Lane4, but arrays are zero indexed.  So the "FIN1"
        message indicates that the lane with an index position of 0 is finished.
        """
        lane_number = int(msg[3])
        return lane_number - 1

    def lane_finished(lane, times):
        """
        Record the finish time for the specified lane in the times array
        """
        if times[lane] != NOT_FINISHED:
            print("lane ", lane+1, " reported redundant finish")
            return

        end = time.monotonic_ns()
        delta = float(end - start) / NANOSECONDS_TO_SECONDS
        print("Lane %d finished. Elapsed time: %6.3f" % (lane+1, delta))
        times[lane] = delta

    def all_lanes_finished():
        """
        Returns True if all configured lanes have finished.  False otherwise.
        """
        for lane in range(num_lanes):
            if finish_times[lane] == NOT_FINISHED:
                return False
        return True

    # Wait for cars on the local starting lanes
    display.wait_local_ready()
    print("Waiting for cars at the gate")
    while not all_lanes_ready(config) and not race_aborted:
        time.sleep(0.1)

    if race_aborted:
        return

    print("All Lanes Ready.")

    if config.multi_track:
        print("Waiting for remote ready")
        display.wait_remote_ready()
        coordinator.start_race()
        print("Remote track ready")

    # Send start of race message to finish line.
    # The message is sent before the countdown because it can take more than 1 second
    # for the bluetooth communication and the message to be picked up and processed by
    # the finish line. Odd, given that the lane finished messages from the finish line
    # are received nearly instantly.
    finish_line.begin_race()
    display.countdown()

    finish_line.purge_bluetooth_messages()

    print("Start the race!")
    release_starting_gate(config)

    display.race_started()

    start = time.monotonic_ns()
    timeout = start + config.race_timeout * NANOSECONDS_TO_SECONDS

    while not all_lanes_finished() and not race_aborted and time.monotonic_ns() < timeout:
        msg = finish_line.get_lane_result(100)
        print(f"received: {msg}")

        if msg.startswith("FIN"):
            lane_finished(lane_index(msg), finish_times)

    # Send end of race message to Finish Line to disable further completion messages
    finish_line.end_race()

    if race_aborted:
        return

    print("Race finished")
    results = calculate_results(config, coordinator, finish_times)

    reset_starting_gate(config)
    display.race_finished(results)

    # Placing a car on a lane terminates the results display and exits the race
    wait_for_car_in_lane(config)

def main():
    """
    Configure starting_gate and run races
    """

    #config = Config("/home/pi/config/starting_gate.json")
    config = Config("config/starting_gate.json")
    display = Display(config)
    device = DeviceIO()
    coordinator = Coordinator(config)
    finish_line = FinishLine(config)

    reset_starting_gate(config)

    # Main loop to iterate over successive race configurations
    while True:

        # Reset aborted state
        global race_aborted #pylint: disable=global-statement
        race_aborted = False

        # De-register with race coordinator.
        config.allow_multi_track = coordinator.deregister()

        # Display the main menu and wait for race selection
        display.wait_menu()

        device.push_key_handlers(key_pressed, key_pressed, key_pressed,
                                 deviceio.default_joystick_handler)

        # Establish Bluetooth connection to Finish Line
        if not finish_line.is_connected() and not race_aborted:
            display.wait_finish_line()
            finish_line.connect()

        # Register with the race coordinator if multi-track race selected in menu
        if config.multi_track:
            display.wait_remote_registration()
            coordinator.register()
            display.remote_registration_done()

        while not race_aborted:
            try:
                run_race(config, coordinator, display, finish_line)
            except bluetooth.btcommon.BluetoothError:
                print("Bluetooth exception caught.  Reconnecting...")
                finish_line.connect()
            except Exception as exc: #pylint: disable=broad-except
                print("Unexpected exception caught", exc)
                traceback.print_exc()
                break # Go back to main menu on unhandled exception within a race

        device.pop_key_handlers()


if __name__ == '__main__':
    main()

# vim: expandtab: sw=4

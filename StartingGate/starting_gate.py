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
from display import Display, NOT_FINISHED

# Globals (yea, I know)
#pylint: disable=invalid-name
race_aborted = False # Set by key_pressed callback to reset race state
finish_line_connected = False

NANOSECONDS_TO_SECONDS = 1000000000
READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR

def key_pressed():
    """
    Callback invoked when a key is pressed after exiting the top level menu.
    Sets global race_aborted state to exit the current race at the earliest
    convenience and return to the top level menu.
    """
    print("key_pressed(): Setting race_aborted to True")
    global race_aborted #pylint: disable=global-statement
    race_aborted = True

#TODO: Make this async and kick it off as early as possible.
def connect_to_finish_line(target_name):
    """ Perform a bluetooth scan for the Finish Line advertising itself as 'target_name'
        If found, establish a connection and return the connected socket

        Args:
            target_name:    The Bluetooth advertised name of the Finish Line to connect

        Returns:
            socket          The open socket to the Finish Line

    """

    port = 1
    socket = None
    target_address = None
    global finish_line_connected #pylint: disable=global-statement

    print("Attempting Bluetooth connection to ", target_name)

    while target_address is None:
        nearby_devices = bluetooth.discover_devices()

        for bdaddr in nearby_devices:
            if target_name == bluetooth.lookup_name(bdaddr):
                target_address = bdaddr
                break

        if target_address is None:
            print("could not find ", target_name, " nearby")
        else:
            print("Found ", target_name, ", connecting...")
            socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            socket.connect((target_address, port))
            finish_line_connected = True
            print("Connected to finish line")
            socket.send("HELO")
    return socket

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

def purge_bluetooth_messages(socket):
    """ Read any residual data from the Finish Line bluetooth connection.

    Before adding the BGIN/ENDR message exchange to prevent the finish line
    from sending results when something passed over a lane when no race was
    active, this purge was critical. Otherwise pending messages (for example
    from someone picking up a car from the finish line) would register before
    a car actually reached the finish line.

    Now reading data should be rare and probably indicates a problem in the
    finish line's debounce logic for the IR sensors. Nevertheless, a millisecond
    delay to read any outstanding data on the socket seems like a reasonable
    defensive act.
    """

    prior_timeout = socket.gettimeout()
    socket.settimeout(0.01)    # wait 1ms for any residual messages
    try:
        socket.recv(1024)   # Purge any messages from the Finish Line
    except bluetooth.btcommon.BluetoothError as exc:
        if exc.args[0] == 'timed out':
            print("purge_bluetooth_messages(): BluetoothError = timed out, ignoring.")
        else:
            # Re raise any other bluetooth exception so the main loop will reconnect
            print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
            raise exc
    socket.settimeout(prior_timeout)

def run_race(config, coordinator, display, socket, poller):
    """
    Run a race

    Args:
        config      Config object with current race configuration
        coordinator Coordinator object for communicating
        display     Display object to manage display of race state
        socket      Bluetooth connection to Finish Line
        poller      Polling object bound to socket to test for READ ready
    """

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
    while not all_lanes_ready(config):
        time.sleep(0.1)
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
    socket.send("BGIN")
    display.countdown()

    purge_bluetooth_messages(socket)

    print("Start the race!")
    release_starting_gate(config)

    display.race_started()

    start = time.monotonic_ns()
    timeout = start + config.race_timeout * NANOSECONDS_TO_SECONDS

    while not all_lanes_finished() and not race_aborted and time.monotonic_ns() < timeout:
        try:
            events = poller.poll(100)
            if events:
                data = socket.recv(5)

                msg = data.decode('utf-8')
                print("received ", msg)

                if msg.startswith("FIN"):
                    lane_finished(lane_index(msg), finish_times)

        except bluetooth.btcommon.BluetoothError as exc:
            if exc.args[0] == 'timed out':
                print("Timeout waiting for race results. Finishing race")
                break
            else:
                print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
                raise exc


    # Send end of race message to Finish Line to disable further completion messages
    socket.send("ENDR")

    if race_aborted:
        return

    print("Race finished")
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

    reset_starting_gate(config)
    display.race_finished(results)

    # Placing a car on a lane terminates the results display and exits the race

    while all_lanes_empty(config):
        time.sleep(0.1)

def main():
    """
    Configure starting_gate and run races
    """

    config = Config("/home/pi/config/starting_gate.json")
    display = Display(config)
    device = DeviceIO()
    coordinator = Coordinator(config)
    socket = None
    poller = None
    global finish_line_connected #pylint: disable=global-statement

    reset_starting_gate(config)

    # Main loop to iterate over successive race configurations
    while True:

        # Reset aborted state
        global race_aborted #pylint: disable=global-statement
        race_aborted = False

        # De-register with race coordinator.
        coordinator.deregister()

        # Display the main menu and wait for race selection
        display.wait_menu()

        device.push_key_handlers(key_pressed, key_pressed, key_pressed,
                                 deviceio.default_joystick_handler)

        # Establish Bluetooth connection to Finish Line
        if not finish_line_connected:
            display.wait_finish_line()
            socket = connect_to_finish_line(config.finish_line_name)
            poller = select.poll()
            poller.register(socket, READ_ONLY)

        # Register with the race coordinator if multi-track race selected in menu
        if config.multi_track:
            display.wait_remote_registration()
            coordinator.register()
            display.remote_registration_done()

        while not race_aborted:
            try:
                run_race(config, coordinator, display, socket, poller)
            except bluetooth.btcommon.BluetoothError:
                print("Bluetooth exception caught.  Reconnecting...")
                finish_line_connected = False
                socket = connect_to_finish_line("FinishLine")
            except Exception as exc: #pylint: disable=broad-except
                print("Unexpected exception caught", exc)
                traceback.print_exc()
                break # Go back to main menu on unhandled exception within a race

        device.pop_key_handlers()


if __name__ == '__main__':
    main()

# vim: expandtab: sw=4

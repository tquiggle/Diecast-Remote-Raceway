#! /usr/bin/python3

"""

Diecast Remote Raceway - config

There are two types of configiguration parameters, persisted and ephemeral.

    * Persisted: configuration parameters that are preserved from one execution to
      another. Examples are the WiFi SSID and password and number of lanes.

    * Ephemeral: configuration applies to a single race session. These are the user's
      selection of single vs multi track racing for the session, and for multi track
      races, the values retreived from the remote raceway.

A note on the REMOTE_* configs. The coordinator is designed to run circuits consisting of
an arbitrary number of tracks.  One could have a circuit with 10 tracks racing against each
other at the same time. Due to the extremely limited real estate on the starting gate
display, the on-device display is limited to two tracks.  A future update could wirelessly
transmit a race display via Miracast to a nearby TV, or maintain a central race status display
via a Web interface that could be monitored separate from the race.

Module-level constants with the config names are defined here to avoid repeated use of
string literals throughout the DRR code. When adding new configuration parameters, simpley add
a new constant with the parameter name and include it in the appropriate PERSISTED_CONFIGS
or EPHEMERAL_CONFIGS array below.  Only configuration names defined below and included in a
*_CONFIGS array will be valid class attributes that are accessable to clients.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.

"""

import json
import sys

# Sentinal value indicating that a car did not complete the race within the timeout period.
# If the finish time for a lane is NOT_FINISHED, display the failure icon for that lane.
NOT_FINISHED = sys.float_info.max

# Constants for indexing into car_icons array
CAR0 = 0
CAR1 = 1
CAR2 = 2
CAR3 = 3

# Persisted configuration variable names:
CAR_ICONS = "car_icons"                 # Car icons for each lane
CIRCUIT = "circuit"                     # Name of the circuit we are racing in, if any
COORDINATOR_HOSTNAME = "coord_host"     # Hostname of the race coordinator server
COORDINATOR_PORT = "coord_port"         # Port the race coordinator server is running on
FINISH_LINE_NAME = "finish_line_name"   # Bluetooth advertisement of our finish line
NUM_LANES = "num_lanes"                 # Number of lanes in the local track (1..4)
RACE_TIMEOUT = "race_timeout"           # Timeout, in seconds, to declare a race over
SERVO_DOWN_VALUE = "servo_down_value"   # Numeric value for Servo for gate in down position
SERVO_UP_VALUE = "servo_up_value"       # Numeric value for Servo for gate in up position
TRACK_NAME = "track_name"               # Name of the local track
WIFI_PSWD = "wifi_pswd"                 # WiFi Password
WIFI_SSID = "wifi_ssid"                 # WiFi SSID

# Ephemeral configuration variable names
IP_ADDRESS = "ip_address"               # IP Address as seen by race coordinator
MULTI_TRACK = "multi_track"             # Tracks in the current racing session, including self
REMOTE_TRACK_NAME = "remote_track_name" # Name of the remote track we are racing against
REMOTE_NUM_LANES = "remote_num_lanes"   # Number of lanes in the track we are racing against
REMOTE_CAR_ICONS = "remote_car_icons"   # Car icons to use for remote lanes

PERSISTED_CONFIGS = [CAR_ICONS,
                     CIRCUIT,
                     COORDINATOR_HOSTNAME,
                     COORDINATOR_PORT,
                     FINISH_LINE_NAME,
                     NUM_LANES,
                     RACE_TIMEOUT,
                     SERVO_DOWN_VALUE,
                     SERVO_UP_VALUE,
                     TRACK_NAME,
                     WIFI_PSWD,
                     WIFI_SSID]

EPHEMERAL_CONFIGS = [IP_ADDRESS,
                     MULTI_TRACK,
                     REMOTE_TRACK_NAME,
                     REMOTE_NUM_LANES,
                     REMOTE_CAR_ICONS]

class Config:

    """
    The Config class provides data attributes for all configuration parameters.

    Clients can simply read/write the configuration parameters directly.  E.g.:

        conf = Config()

        if conf.remote_num_lanes >= 1 and conf.remote_car_1_icon is None:
            conf.remote_car_1 = "blue"
        ...

    Only attributes defined in the above constants are valid. The __init__ function
    explicitly populates the instance's data attributes with these names.  Any inadvertant
    assignment to an unknown config parameter will fail.
    """

    # List of private attributes of the class.  These need to be included in
    # the __slots__ array or they can't be initialized in __init__()
    __PRIVATE_ATTRIBUTES = ['__filename']

    # Disallow creating unknown attributes by inadvertant assignment
    __slots__ = PERSISTED_CONFIGS + EPHEMERAL_CONFIGS + __PRIVATE_ATTRIBUTES

    #
    # Default config values, overridden by /home/pi/config/starting_gate.json
    #
    DEFAULT = {}
    DEFAULT[CAR_ICONS] = ["convertible-red", "white", "blue", "black"]
    DEFAULT[CIRCUIT] = "DRR"
    DEFAULT[COORDINATOR_HOSTNAME] = "<COORDINATOR_HOSTNAME>"
    DEFAULT[COORDINATOR_PORT] = 1968
    DEFAULT[FINISH_LINE_NAME] = "FinishLine"
    DEFAULT[IP_ADDRESS] = "127.0.0.1"
    DEFAULT[MULTI_TRACK] = False
    DEFAULT[NUM_LANES] = 2
    DEFAULT[RACE_TIMEOUT] = 5.0
    DEFAULT[REMOTE_CAR_ICONS] = ["question", "question", "question", "question"]
    DEFAULT[REMOTE_NUM_LANES] = 2
    DEFAULT[REMOTE_TRACK_NAME] = "UNKNOWN"
    DEFAULT[SERVO_DOWN_VALUE] = 1.0
    DEFAULT[SERVO_UP_VALUE] = 0.0
    DEFAULT[TRACK_NAME] = "Track-1"
    DEFAULT[WIFI_PSWD] = "<WIFI_PASSWORD>"
    DEFAULT[WIFI_SSID] = "<WIFI_SSID>"

    def __init__(self, filename):
        self.__filename = filename
        # Initialize all config attributes with their default values
        for cfg in PERSISTED_CONFIGS + EPHEMERAL_CONFIGS:
            print("setting ", cfg, " to ", Config.DEFAULT[cfg])
            object.__setattr__(self, cfg, Config.DEFAULT[cfg])

        # Perform deep copy of car icons from DEFAULT so we can detect changes
        self.car_icons = Config.DEFAULT[CAR_ICONS].copy()

        # If given a config file, load it and overwrite any defaults
        if filename is not None:
            print("Config.__init__(filename)")
            try:
                with open(filename) as config_file:
                    config_json = json.load(config_file)

                    for cfg in config_json:
                        print("  setting ", cfg, " to ", config_json[cfg])
                        if cfg in PERSISTED_CONFIGS:
                            object.__setattr__(self, cfg, config_json[cfg])
                        else:
                            print("Invalid parameter in config file: ", cfg)
            except FileNotFoundError:
                print("Could not open file ", filename)

    def save(self):
        """
        Write all non-default, persisted, config values out to the config file.
        """
        print("Config.save(", self.__filename, ")")

        local_config = {}

        for config in PERSISTED_CONFIGS:
            if config == CAR_ICONS:
                config_icons = getattr(self, CAR_ICONS)
                default_icons = Config.DEFAULT[CAR_ICONS]
                # If any car icon has been modified from the defaults, just write out the
                # entire icons array.  Don't bother joining defaults against user selections
                # when reading.
                for idx, icon in enumerate(config_icons):
                    print("comparing {} to default_icons[{}] = {}".format(icon, idx,
                                                                          default_icons[idx]))
                    if icon != default_icons[idx]:
                        print("Adding config_icons to local_icons")
                        local_config[CAR_ICONS] = config_icons
                        break

            elif getattr(self, config) != Config.DEFAULT[config]:
                print("Adding ", config, " to local_icons")
                local_config[config] = getattr(self, config)

        print("local_config=", local_config)

        if local_config:
            print("saving local_config")
            config_string = json.dumps(local_config, sort_keys=True, indent=4,
                                       separators=(',', ': '))
            filehandle = open(self.__filename, 'w')
            filehandle.write(config_string)
            filehandle.close()



if __name__ == '__main__':

    def do_main():
        #pylint: disable=attribute-defined-outside-init, no-member
        """
        At some point I should write legitimate unit tests.  But for now, I just exercise
        some basic functionality if the class is invoked as the Python main.
        """

        main_config = Config("config/starting_gate.json")

        print("main_config.num_lanes=", main_config.num_lanes)
        print("main_config.race_timeout=", main_config.race_timeout)
        main_config.race_timeout = 1.75
        main_config.track_name = "My Track"
        print("main_config.race_timeout=", main_config.race_timeout)

        main_config.remote_track_name = "other track"
        print("main_config.remote_track_name=", main_config.remote_track_name)

        main_config.save()

    do_main()

# vim: expandtab sw=4

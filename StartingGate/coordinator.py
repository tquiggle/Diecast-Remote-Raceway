#! /usr/bin/python3

"""
Diecast Remote Raceway - Coordinator

Interface to the race coordinator that manages multi-track races.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.

"""

import json
import requests

from config import Config, CAR0, CAR1, CAR2, CAR3 #pylint: disable=unused-import

class Coordinator:
    """

    Provides all communication between the Starting Gate and the Race Coordinator

    The local race controller communicates with the Race Coordinator at via 4 interactions:

    * register:   upon startup, if multi-track racing is selected, the local track registers
                  with the Race Coordinator providing the track_name, number of lanes, and
                  car icon selections.

    * deregister: at shut-down or if the user switches to single-track racing, the local track
                  removes its registration with the Race Coordinator.

    * start:      Indicates that the local track is ready to start a race.  The Race
                  Coordinator will only respond to the request once all tracks are ready

    * results:    The local track reports its results and awaits the global results.

    """

# PUBLIC:

    def __init__(self, config):
        self.config = config
        self.register_url = "http://{}:{}/register".format(config.coord_host, config.coord_port)
        self.start_url = "http://{}:{}/start".format(config.coord_host, config.coord_port)
        self.results_url = "http://{}:{}/results".format(config.coord_host, config.coord_port)
        self.deregister_url = "http://{}:{}/deregister".format(config.coord_host, config.coord_port)

    def register(self):
        """
        Register with the race coordinator.

        See Coordinator/drr_server.js for detail of the json request/response format
        """
        headers = {'Content-Type': 'application/json'}

        registration = {}
        registration['circuit'] = self.config.circuit
        registration['trackName'] = self.config.track_name
        registration['numLanes'] = self.config.num_lanes
        registration['carIcons'] = self.config.car_icons

        json_string = json.dumps(registration).encode('utf-8')

        print("register: ", json_string)
        response = requests.post(self.register_url, data=json_string, headers=headers)
        print("response=", response)

        reply = response.json()

        print("reply=", reply)

        remote = reply['remoteRegistrations'][0]

        self.config.ip_address = reply['ip']
        self.config.remote_track_name = remote['trackName']
        self.config.remote_num_lanes = remote['numLanes']
        self.config.remote_car_icons = remote['carIcons']

    def deregister(self):
        """
        Deregister from the race coordinator, thus leaving the circuit
        """
        print("deregister: ")
        response = requests.post(self.deregister_url, data="")
        print("response=", response)

    def start_race(self):
        """
        Send message to coordinator that the local track is ready for the start of the
        race.  The GET request only returns when all tracks in the circuit are ready.
        """
        print("start_race: GET ", self.start_url)
        response = requests.get(self.start_url)
        print("response=", response)

    def results(self, local_results):
        """
        Send local race results to the race coordintor and collect circuit-wide results
        in the response.
        """
        headers = {'Content-Type': 'application/json'}

        json_string = json.dumps(local_results).encode('utf-8')

        print("register: ", json_string)
        response = requests.post(self.results_url, data=json_string, headers=headers)
        print("response=", response)

        print("response.text=", response.text)
        result_string = response.text
        return result_string

# PRIVATE:


if __name__ == '__main__':

    def do_main():
        #pylint: disable=attribute-defined-outside-init, no-member
        """
        At some point I should write legitimate unit tests.  But for now, I just exercise
        some basic functionality if the class is invoked as the Python main.
        """

        main_config = Config("/home/tom/Raceway/StartingGate/config/starting_gate.json")
        main_config.car_icons[CAR1] = "white"
        main_config.car_icons[CAR2] = "police"

        main_coord = Coordinator(main_config)

        main_coord.register()
        main_coord.start_race()

    do_main()

# vim: expandtab sw=4

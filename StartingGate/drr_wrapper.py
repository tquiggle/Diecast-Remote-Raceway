#! /usr/bin/python3

"""
drr_wrapper:

This script is invoked at startup from rc.local to run the Starting Gate
software. It performs two functions:

* checks for a software update and installs if available
* executes the starting gate executable as a child and restarts on failure.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import os
import urllib.request
import requests

from config import Config

DRR_CONFIG = Config("config/starting_gate.json")

def fetch_latest_version():
    """
    Fetches version.txt containing latest release version from the DRR Coordinator
    """
    version_url = "http://{}:{}/DRR/SG/version.txt".format(DRR_CONFIG.coord_host,
                                                           DRR_CONFIG.coord_port)
    print("Fetching latest version number from ", version_url)
    response = requests.get(version_url)
    return response.text.rstrip()


def read_local_version():
    """
    Extracts the version number of the currently installed release from the local version.txt
    """
    if os.path.exists("version.txt"):
        version_file = open("version.txt")
        version = version_file.readline()
        return version.rstrip()
    else:
        print("no local version file exists!")
        return "-1"

def check_for_updates():
    """
    Check Coordinator for newer software release
    """
    current_version = read_local_version()
    latest_version = fetch_latest_version()

    if current_version < latest_version:
        release_file = "starting-gate-{}.tgz".format(latest_version)
        release_url = "http://{}:{}/DRR/SG/{}".format(DRR_CONFIG.coord_host,
                                                      DRR_CONFIG.coord_port,
                                                      release_file)
        print("fetching: ", release_url)
        urllib.request.urlretrieve(release_url, release_file)
        if not os.path.exists(release_file):
            print("Error fetching", release_url, " to ", release_file)
            return

        return_status = os.system("tar xzf {}".format(release_file))
        # needs Python 3.9:  code = os.waitstatus_to_exitcode(return_status)
        code = os.WEXITSTATUS(return_status)
        if code != 0:
            print("Error extracting", release_file)

def run_starting_gate():
    """
    Execute the Starting Gate program and wait for it to complete
    """
    pid = os.fork()
    if pid > 0:
        print("In parent, child pid = ", pid)
        pid, status = os.waitpid(pid, 0)
        print("os.waitpid returned status", status >> 8)
    else:
        print("In child pid = {} ".format(os.getpid()))
        os.execlp("/home/pi/starting_gate.py", "0", "0")

while True:
    check_for_updates()
    run_starting_gate()

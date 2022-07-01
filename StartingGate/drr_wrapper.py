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
import subprocess
import urllib.request

from config import Config

DRR_CONFIG = Config("config/starting_gate.json")

def fetch_latest_version():
    """
    Fetches version.txt containing latest release version from the DRR Coordinator
    """
    version_url = "http://{}:{}/DRR/SG/version.txt".format(DRR_CONFIG.coord_host,
                                                           DRR_CONFIG.coord_port)
    print("Fetching latest version number from ", version_url)
    try:
        with urllib.request.urlopen(version_url) as response:
            version = response.read().decode("utf-8").rstrip()
            return version
    except:
        print("Unable to fetch latest version number. Returning -1")
        return "-1"


def read_local_version():
    """
    Extracts the version number of the currently installed release from the local version.txt
    """
    print("Reading local version from version.txt")
    if os.path.exists("version.txt"):
        version_file = open("version.txt")
        version = version_file.readline()
        return version.rstrip()

    print("no local version file exists. Returning -1")
    return "-1"

def check_for_updates():
    """
    Check Coordinator for newer software release
    """
    current_version = read_local_version()
    latest_version = fetch_latest_version()

    print("current_version=", current_version)
    print("latest_version=", latest_version)

    if current_version < latest_version:
        if not os.path.isdir("releases"):
            os.mkdir("releases")

        release_file = "starting-gate-{}.tgz".format(latest_version)
        release_url = "http://{}:{}/DRR/SG/{}".format(DRR_CONFIG.coord_host,
                                                      DRR_CONFIG.coord_port,
                                                      release_file)
        release_dest = "releases/{}".format(release_file)

        print("fetching: ", release_url)
        urllib.request.urlretrieve(release_url, release_dest)
        if not os.path.exists(release_dest):
            print("Error fetching", release_url, " to ", release_dest)
            return

        print("expanding: ", release_dest)
        result = subprocess.run(["tar", "xzf", "{}".format(release_dest)])
        if result.returncode != 0:
            print("Error extracting", release_dest)

def run_starting_gate():
    """
    Execute the Starting Gate program and wait for it to complete
    """
    result = subprocess.run(["/home/pi/starting_gate.py"], check=False)
    print ("process returned = ", result.returncode)

while True:
    check_for_updates()
    run_starting_gate()

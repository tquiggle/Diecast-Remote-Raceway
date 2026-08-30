#! /usr/bin/python3

"""
drr_wrapper:

This script is invoked at startup from rc.local to run the Starting Gate
software. It performs two functions:

* performs a "git pull" to download any updates to the software
* executes the starting gate executable as a child and restarts on failure.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import os
import subprocess
import sys


command = sys.argv[0]
trailing_slash = command.rfind('/')
if trailing_slash != -1:
    curent_dir = command[:trailing_slash]
    print(f"changing current working directory to {dir}")
    os.chdir(curent_dir)


def check_for_updates():
    """
    Perform a git pull request to update the Starting Gate software
    """
    result = subprocess.run(["git", "pull"], check=False)
    print ("git pull returned = ", result.returncode)

def run_starting_gate():
    """
    Execute the Starting Gate program and wait for it to complete
    """
    result = subprocess.run(["./starting_gate.py"], check=False)
    print ("process returned = ", result.returncode)

while True:
    check_for_updates()
    run_starting_gate()

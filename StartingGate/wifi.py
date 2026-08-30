#! /usr/bin/python3

"""
Diecast Remote Raceway - WiFi

The Input class implements access to WiFi

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import configparser
import csv
import glob
import os
import subprocess

class WiFi:

    """
    WiFi():

    This class provides utility functions to read and modify the WiFi configuration

    * scan_wifi_networks:     Scans available WiFi networks and returns a list of those
                              that are broadcasting an ESSID

    * get_essid:              Returns the ESSID of the currently connected WiFi, if any

    * get_psk:                Given an ESSID, searches the system's .nmconnection files
                              and returns the psk or password string for the first match

    * set_region:             Sets the WiFi region code

    * connect:                Connect to the specified ESSID using the provided credential

    """

# PUBLIC

    def scan_wifi_networks(self):
        """
        Triggers a Wi-Fi scan and parses available access points with signal strength.
        Uses NetworkManager's nmcli output formatted as CSV for safe parsing.
        """

        # Force NetworkManager to trigger a fresh scan of available Wi-Fi networks
        # TODO: Consider adding Polkit rule to allow users of group netdev to run
        #       a wifi scan without sudo
        cmd = ["sudo", "nmcli", "device", "wifi", "rescan"]
        subprocess.run(cmd, stderr=subprocess.DEVNULL, check=False)

        # Fetch network data formatted with specific fields separated by colons
        # Fields: SSID (Name), SIGNAL (Percentage 0-100), SECURITY (Encryption)
        cmd = ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error querying NetworkManager: {e}")
            return []

        networks = []
        # Use csv reader to automatically handle escaped colons in MAC addresses or SSIDs
        reader = csv.reader(result.stdout.strip().splitlines(), delimiter=":")

        dedup = {}
        for row in reader:
            print("row: ", row, "\n")

            # Check if row has all requested fields
            if len(row) >= 3:
                # Skip WiFi sources with hidden SSID
                if row[-3]:
                    ssid = row[-3]
                    signal_pct = row[-2]
                    security = row[-1]

                    if not ssid in dedup:
                        networks.append({
                            "ssid": ssid,
                            "signal_percent": int(signal_pct) if signal_pct.isdigit() else 0,
                            "security": security
                        })
                    dedup[ssid] = True

        # Sort networks by signal strength descending
        return sorted(networks, key=lambda x: x["signal_percent"], reverse=True)

    def get_essid(self) -> str:
        """
        Returns the ESSID of the currently active wireless network or None
        if no network is active.
        """

        try:
            # Run the command and capture standard output
            output = subprocess.check_output(
                ["iwgetid", "-r"], stderr=subprocess.STDOUT, text=True
            )
            return output

        except subprocess.CalledProcessError:
            # Occurs if iwgetid exits with non-zero code (e.g., disconnected)
            return ""
        except FileNotFoundError:
            print("Error: 'iwgetid' command not found. Ensure wireless-tools is installed.")
            return ""

    def get_psk(self, essid: str) -> str | None:
        """
        Searches system .nmconnection files for one containing a given ESSID
        and extracts the psk value if present.  Falls back to pswd if no psk
        is found.

        Checks runtime path (/run) first for dynamic files (Debian 13+ / Netplan),
        then falls back to persistent path (/etc) for static files (Debian <=12).

        Returns the WiFi credential if found, or None if no match exists.
        """

        # Search order: run path first (Trixie+ netplan generated), then etc path (legacy/static)
        search_paths = [
            "/run/NetworkManager/system-connections",
            "/etc/NetworkManager/system-connections",
        ]

        for base_dir in search_paths:
            if not os.path.isdir(base_dir):
                continue

            # Find all .nmconnection files in directory
            pattern = os.path.join(base_dir, "*.nmconnection")
            for filepath in glob.glob(pattern):
                config = configparser.ConfigParser(interpolation=None)

                # NetworkManager keyfiles use case-sensitive keys
                config.optionxform = str

                try:
                    config.read(filepath, encoding="utf-8")

                    # Check connection name ([connection] -> id)
                    conn_id = config.get("connection", "id", fallback=None)

                    # Check explicit Wi-Fi SSID ([wifi] -> ssid)
                    wifi_ssid = config.get("wifi", "ssid", fallback=None)

                    if essid in (conn_id, wifi_ssid):
                        # We have a .nmconnection file that matches the essid

                        # Look for a psk config
                        psk = config.get("wifi-security", "psk", fallback=None)
                        if psk:
                            return psk

                        # If no psk value, look for a plaintext pswd
                        pswd = config.get("wifi-security", "pswd", fallback=None)
                        if pswd:
                            return pswd

                except (configparser.Error, PermissionError):
                    # Skip unreadable or malformed files
                    continue

        return None

    def set_region(self, region: str):
        """
        Sets the WiFi region code
        """
        cmd = ["sudo", "iw", "reg", "set", region]
        subprocess.run(cmd, stderr=subprocess.DEVNULL, check=False)


    def connect(self, essid: str, psk: str):
        """
        Connect to WiFi network specified by essid using supplied psk
        """

        cmd = ["sudo", "nmcli", "device", "wifi", "connect", essid, "password", psk]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error querying NetworkManager: {e}")


def main():
    """
    When run as main program, create Menu object and run main function
    """

    wifi = WiFi()

    print("Scanning for Wi-Fi networks...")
    wifi_list = wifi.scan_wifi_networks()

    print(f"\nFound {len(wifi_list)} access points:\n")
    print(f"{'SSID':<30} {'SIGNAL':<10} {'SECURITY'}")
    print("-" * 75)

    for ap in wifi_list:
        signal_bar = f"{ap['signal_percent']}%"
        print(f"{ap['ssid'][:28]:<30} {signal_bar:<10} {ap['security']}")

if __name__ == '__main__':
    main()

# vim: expandtab sw=4

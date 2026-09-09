#! /usr/bin/python3

"""
Diecast Remote Raceway - FinisLine

Interface for communication with the FinishLine over Bluetooth.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.

"""

import base64
import json
import re
import select
import subprocess
import urllib.request

from pathlib import Path

import bluetooth

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from config import Config
from wifi import WiFi

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR

class FinishLine:
    """

    Provides all communication between the Starting Gate and the FinishLine

    The Starting Gate communicates with the FinishLine as follows:

    * connect:      Connect to the FinishLine via Bluetooth

    * is_connected: Returns connected state of finish line

    * update_software:
                    Check to see if there is a newer version of the
                    FinishLine software, and if so issue update request
                    to the FinishLine

    * purge_bluetooth_messages:
                    Read any residual input from the FinishLine

    * begin_race:   Send FinishLine a message indicating a race has begun.
                    Any lane sensor triggers will send a lane completion
                    message back to the StartingGate

    * end_race:     Send  FinishLine a messge indicating race has ended.
                    Ignore any additional lane sensor triggers.

    * def get_lane_result:
                    Wait for and return the next lane finish message
    """

# PUBLIC:

    def __init__(self, config):
        self.config = config
        self.socket = None
        self.connected = False
        self.poller = select.poll()
        self.finish_line_connected = False
        self.wifi = WiFi()

    def connect(self) -> bool:
        """
        Connect to FinishLine via bluetooth

        Returns True if connection is successful, False otherwise
        """
        port = 1

        if self.socket is not None:
            self.poller.unregister(self.socket)

        target_address = None
        target_name = self.config.finish_line_name

        while target_address is None:
            nearby_devices = bluetooth.discover_devices()

            for bdaddr in nearby_devices:
                if target_name == bluetooth.lookup_name(bdaddr):
                    target_address = bdaddr
                    break

            if target_address is None:
                print("could not find ", target_name, " nearby")
                return False

        print("Found ", target_name, ", connecting...")
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.socket.connect((target_address, port))
        self.poller.register(self.socket, READ_ONLY)
        self.finish_line_connected = True
        print("Connected to finish line")
        return True

    def is_connected(self) -> bool:
        """
        Returns True if FinishLine is connected, False otherwise
        """
        return self.connected

    def purge_bluetooth_messages(self):
        """
        Read any residual data from the FinishLine bluetooth connection.

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

        prior_timeout = self.socket.gettimeout()
        self.socket.settimeout(0.01)    # wait 1ms for any residual messages
        try:
            self.socket.recv(1024)   # Purge any messages from the Finish Line
        except bluetooth.btcommon.BluetoothError as exc:
            if exc.args[0] == 'timed out':
                print("purge_bluetooth_messages(): BluetoothError = timed out, ignoring.")
            else:
                # Re raise any other bluetooth exception so the main loop will reconnect
                print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
                self.connected = False
                raise exc
        finally:
            self.socket.settimeout(prior_timeout)

    def begin_race(self):
        """
        Send begin race message to FinishLine
        """
        self.socket.send("BGIN")

    def end_race(self):
        """
        Send end race message to FinishLine
        """
        self.socket.send("ENDR")

    def get_lane_result(self, timeout_ms) -> str:
        """
        Read lane result from Bluetooth connection with specified timeout

        Returns a string of the form "FIN#" where '#" is a lane number
        Returns None if the read times out
        """

        try:
            events = self.poller.poll(timeout_ms)
            if events:
                data = self.socket.recv(5)

                msg = data.decode('utf-8')
                print("received ", msg)
                return msg

        except bluetooth.btcommon.BluetoothError as exc:
            if exc.args[0] == 'timed out':
                print("Timeout waiting for race results. Finishing race")

            print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
            raise exc

        return None

    def update_software(self):
        """
        Retrieve current software version from the FinishLine.
        Check for newer version from distribution location.
        If newer version is available, send update command to FinishLine.

        The routine determines the current WiFi connection's ESSID and PKS. The latter
        is encrypted using a public key obtaind from the FinishLine prior to sending
        as part of a JSON argument to the UPFW command
        """

        current_version = self.__get_software_version()
        release_version = self.__get_release_version()

        if current_version < "20260800":
            print(f"FinishLine version {current_version} does not support UPDATE_FIRMWARE command")
            return

        if release_version <= current_version:
            print(f"Finish Line version {current_version} is up-to-date:"
                  f"release_version={release_version}")
            return

        # There is a newer version. Construct the update request

        # Lookup what WiFi network the StartingGate is connected to
        essid = self.wifi.get_essid()
        if essid:
            print(f"Connected to: {essid}")
        else:
            print("Not connected to Wi-Fi or ESSID could not be retrieved.")
            return

        # And retrieve the PSK
        psk = self.wifi.get_psk(essid)
        if psk:
            print(f"psk found: {psk}")
        else:
            print("Unable to extract psk from nmconnection file")
            return

        # Encrypt the psk so as not to send it in plaintext over Bluetooth
        pem = self.__get_public_key_pem()
        encrypted_psk = self.__encrypt_string_with_rsa_public_key(pem, psk)
        base64_encrypted_psk_bytes = base64.b64encode(encrypted_psk)
        base64_encrypted_psk_string = base64_encrypted_psk_bytes.decode("utf-8")

        url = f"{self.config.distribution_url}/FL{release_version}.bin"

        update_argument = {
            "SSID": essid,
            "encryptedPSK": base64_encrypted_psk_string,
            "URL": url}

        update_json = json.dumps(update_argument)

        print(f"JSON command={update_json}")

        command = f"UPFW {update_json}"
        print("Sending: ", command)
        self.socket.send(command)


# PRIVATE:

    def __get_release_version(self) -> str:
        """
        Fetches version.txt containing latest release version from the distribution server
        """
        version_url = f"{self.config.distribution_url}/version.txt"
        print("Fetching latest version number from ", version_url)
        try:
            with urllib.request.urlopen(version_url) as response:
                version = response.read().decode("utf-8").rstrip()
                return version
        except (urllib.error.URLError, urllib.error.HTTPError):
            print("Unable to fetch latest version number. Return -1")

        return "-1"

    def __get_software_version(self) -> str:
        """
        Returns the version string for the FinishLine software
        """

        print("FinishLine.__get_software_version(): sending FLVS")
        self.socket.send("FLVS")

        data = self.socket.recv(9)
        version = data.decode('utf-8')

        return version

    def __get_public_key_pem(self):
        command = "GKEY"
        print("Sending: ", command)
        self.socket.send(command)


        # The first GKEY command generates a new random RSA key pair on the
        # ESP32.  This can take a while!
        original_timeout = self.socket.gettimeout()
        self.socket.settimeout(20.0)

        buffer = bytearray()
        try:
            timeout_adjusted = False
            while True:
                data = self.socket.recv(1024)
                if not data:
                    # Connection was closed by remote peer
                    print("Connection reset by peer")
                    break
                print(f"received {len(data)} bytes")
                buffer.extend(data)
                if not timeout_adjusted:
                    self.socket.settimeout(0.5)
                    timeout_adjusted = True
        except bluetooth.btcommon.BluetoothError as e:
            print(f"Caught BluetoothError: {e}")
        finally:
            # restore original timeout
            self.socket.settimeout(original_timeout)

        return bytes(buffer)

    def __encrypt_string_with_rsa_public_key(self, public_key_pem: bytes, plaintext: str) -> bytes:
        """
        Encrypts a string using an RSA public key in PEM format.

        Args:
            public_key_pem: The RSA public key in PEM format as bytes.
            plaintext: The string to be encrypted.

        Returns:
            The ciphertext as bytes.

        Raises:
            ValueError: If the public key cannot be loaded or encryption fails.
        """
        try:
            # Load the public key from PEM format
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"Failed to load public key: {e}") from e

        # Convert the plaintext string to bytes
        plaintext_bytes = plaintext.encode('utf-8')

        # Encrypt the plaintext using OAEP padding (Recommended for RSA encryption)
        # OAEP (Optimal Asymmetric Encryption Padding) is a modern padding scheme
        # that provides strong security guarantees against various attacks.
        try:
            ciphertext = public_key.encrypt(
                plaintext_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return ciphertext
        except Exception as e:
            raise ValueError(f"Failed to encrypt data: {e}") from e


def main():
    """
    When run as the main program, exercise the update logic
    """
    main_config = Config("config/starting_gate.json")

    finish_line = FinishLine(main_config)
    if not finish_line.connect():
        print("Unable to connect to FinishLine")
        return

    finish_line.update_software()


if __name__ == '__main__':
    main()

# vim: expandtab sw=4

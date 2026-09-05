#! /usr/bin/bash

#
# Script to create a service to run pigpiod on boot.
# The service can be managed using systemctl in the
# usual manner.
#

# Check if the Effective User ID (EUID) is not root (0)
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Please use"
    echo "  sudo $0"
    exit 1
fi

cat > /lib/systemd/system/pigpiod.service << __EOF__
[Unit]
Description=Daemon required to control GPIO pins via pigpio

[Service]
Type=forking
ExecStart=/usr/local/bin/pigpiod -t 0 -l
Restart=always
ExecStop=/bin/systemctl kill pigpiod

[Install]
WantedBy=multi-user.target
__EOF__

sudo systemctl daemon-reload
sudo systemctl enable --now  pigpiod


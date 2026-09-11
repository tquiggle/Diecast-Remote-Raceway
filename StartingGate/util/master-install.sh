#! /usr/bin/bash

#
# Master script to configure a DRR Starting gate from a fresh Raspberry
# PI OS install
#
# This script captures all steps required to install and configure the
# DRR Starting Gate on a freshly installed Raspberry Pi OS Lite system.
#
# Some steps involve invoking scripts located in the
#
#   ~/Diecast-Remote-Raceway/StartingGate/util/
#
# directory rather than inline in this script.  These scripts pre-date 
# this master-install and may be useful in other projects.
#
# The last step of installing the Waveshare 1.3 inch LCD HAT will
# ask if you want to reboot.  If everything was sucessful, typing
# 'y' will reboot the system into the DRR software.


####################
# First grant passwordless sudo to the 'drr' user. This will prompt the
# user for a password just once. All subsequent sudo operations will not
# require a password.

echo
echo "Granting user drr passwordless sudo"
echo

echo 'drr	ALL=(ALL) NOPASSWD: ALL' > /tmp/drr
sudo install -o root -g root /tmp/drr /etc/sudoers.d/drr

####################
# Install any pending OS updates

echo
echo "Installing OS updates"
echo

sudo apt update -y
sudo apt upgrade -y
sudo apt autopurge -y

####################
# Install all required packages

echo
echo "Installing required packages"
echo

sudo apt install -y --no-install-recommends -y cmake git python3 python3-setuptools python3-dev python3-gpiozero python3-pigpio python3-bluez python3-pip libegl1-mesa-dev libgbm-dev libgles2-mesa-dev libdrm-dev

####################
# Perform a sparse checkout of just the Starting Gate component of the DRR

echo
echo "Checking out DRR Starting Gate from github"
echo

git clone --no-checkout https://github.com/tquiggle/Diecast-Remote-Raceway.git
cd Diecast-Remote-Raceway
git sparse-checkout init --cone
git sparse-checkout set StartingGate
git checkout
cd

####################
# Build and install pigpiod

echo
echo "Building and installing pigpiod"
echo

wget https://github.com/joan2937/pigpio/archive/refs/tags/v79.tar.gz
tar zxf v79.tar.gz
cd pigpio-79
make
sudo make install

####################
# Make pigpiod start on every boot

echo
sudo ~/Diecast-Remote-Raceway/StartingGate/util/pigpiod-service.sh

####################
# Build the DRM version of Raylib

echo
echo "Building raylib and pyray"
~/Diecast-Remote-Raceway/StartingGate/util/build-raylib.sh

####################
echo
echo "Configure drr-wifi-connect"
echo

ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    armhf|armv7l)
        echo "The system environment is: armhf (32-bit)"
        DIST=https://github.com/tquiggle/DRR-wifi-connect/releases/download/1.0.1/drr-wifi-connect_1.0.1-armhf.deb
        DEB=./drr-wifi-connect_1.0.1-armhf.deb
        ;;
    arm64|aarch64)
        echo "The system environment is: arm64 (64-bit)"
        DIST=https://github.com/tquiggle/DRR-wifi-connect/releases/download/1.0.1/drr-wifi-connect_1.0.1-arm64.deb
        DEB=./drr-wifi-connect_1.0.1-arm64.deb
        ;;
    *)
        echo "Unknown or unsupported architecture: $ARCH"
        echo "Skipping installation of DRR-wifi-connect"
        ;;
esac

if [[ -v DIST ]]; then
    wget $DIST
    sudo apt install -y $DEB
    sudo systemctl enable drr-wifi-connect
fi
sudo raspi-config nonint do_wifi_country US
sudo sed -i 's/ieee80211_regdom=../ieee80211_regdom=00/g' /boot/firmware/cmdline.txt

####################
# Install RonR's image-backup utility in /bin so we can build release images

echo
echo "Installing RonR's image-backup utility"
echo

mkdir ~/bin
cd ~/bin
wget https://raw.githubusercontent.com/seamusdemora/RonR-RPi-image-utils/refs/heads/master/image-backup
chmod +x image-backup
cd

####################
# Have the starting gate start on every boot

echo
echo "Configuring /etc/rc.local to start Starting Gate at boot"
echo

sudo install -o root -g root  ~/Diecast-Remote-Raceway/StartingGate/util/rc.local /etc/rc.local

####################
# Setup the Waveshare 1.3" LCD HAT

echo
echo "Configuring Waveshare 1.3 inch LCD HAT"
echo

sudo ~/Diecast-Remote-Raceway/StartingGate/util/setup-waveshare-1.3-HAT.sh


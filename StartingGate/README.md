# Diecast Remote Raceway - Starting Gate

This directory contains the 3D models, software and instructions for the Starting Gate component of the Diecast Remote Raceway.

![Starting Gate](../images/Starting-Gate.jpg)

## 3D Printed Components

### Starting Gate

The Starting Gate is derived from the excellent design by 
[capsurfer](https://www.thingiverse.com/capsurfer/about) on 
[Thingiverse](https://www.thingiverse.com/thing:4026846) with a number of modifications to adapt it to automation.

The following components are printed exactly as-is from capsurfer's original design:

* connector_v2.stl
* lever.stl
* lid.stl
* starter.stl
* thestick[\_long4].stl

As they are capsurfer's unmodified designs, I have not included the STL files in the
repository.  You will need to download those STLs from thingiverse.

The following components have been modified to suit automation

* open-box.stl - a modified version of box.stl to insert the track with a mounted sensor from the back of the box. The sensor would collide with the starter if inserted from the front.
* open-box-servo.stl - a modified version of open-box.stl for Lane 1 with an opening and mounting holes for a MG90S servo.
* sensor-track.stl - a modified version of track.stl designed to mount a [TCRT5000 Infrared Reflective Sensor Module](https://www.amazon.com/gp/product/B081RPJ44L) to detect the presence of a car.

* sensor-track-flush.stl - a modified version of sensor-track.stl that moves the sensor forward about 10mm.  Requires reworking the TCRT5000 sensors. See note below.
* servo-knob.stl - Modified version of knob.stl to make the arm much narrower and add holes for the servo control.
* lane-#.stl - modified versions of sensor-track-flush.stl with embossed lane numbers

I also moved the location of the track extrusions that accept the threaded heat set screw inserts further away from the track surface to
eliminate bulging of the track surface. This required changes to both the open-box\* and
sensor-track\* relative to the original they are derived from.

New components added to the design:

* back-lid.stl - a removable lid on the back of the box that secures the track.
* mount.stl - a mount that attaches to the bottom of a box allowing the box to be mounted on a [Hot Wheels Clamp 3-way](https://www.thingiverse.com/thing:4037458) or a [Hot Wheels Track Tripod Connector ](https://www.thingiverse.com/thing:4376073).


#### Note on Track Sensors
With an unmodified IR sensor, the sensor needs to be mounted entirely aft of the starter which leaves very little room for the wiring and puts the sensor at the back bumper of shorter cars.

By reworking the TCRT5000 IR Sensor to mount the LED/Photosensor pair flush with the PCB, the sensor module can be moved forward about 10mm
giving more room for wiring and a better sensing location.  This requires desoldering the LED/Photosensor, clipping the plastic stand-offs
and resoldering the LED and Photosensor after repositioning.  If you aren't comfortable desoldering the LED/Photosensor components, just print the
sensor-track.stl. I felt the relocation was worth the effort of reworking the sensor modules.  I found this inexpensive
[Vacuum Desoldering Iron](https://www.jameco.com/z/VTDESOL3U-Velleman-10-5-Long-Vacuum-Desoldering-Pump-with-30W-Heater-Yellow-_2131021.html)
made the job easy.

![IR Sensors](../images/sensors.jpg)

An unmodified sensor is shown on the left and a reworked sensor on the right.

#### License

To conform to capsurfer's licensing for the Starter Box from which these components are
derived, the Starting Gate components are released under the [Creative Commons
Attribution - NonCommercial - ShareAlike](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.

### Controller

The control hardware is housed in a three piece case that is based on [JdaieLin](https://github.com/JdaieLin)'s [PiSugar Case](https://github.com/PiSugar/PiSugar).  The controller consists of four 3D printed components:

* bottom-cover.stl - this is an optional bottom cap for use on a completed controller case 
while testing, before mounting to a set of starting gate lanes.  It is based on the PiSugar [pisugar_case_common_cap.STL](https://github.com/PiSugar/PiSugar/blob/master/model/pisugar_case_common_cap.STL) but has been modified to slightly beef up the clips that hold the cap onto the bottom of the pi-zero-case.
* pi-zero-case.stl - a modified version of PiSugar's
[pisugar_nobatt_shell.STL](https://github.com/PiSugar/PiSugar/blob/master/model/pisugar_nobatt_shell.STL) with embossed labels for the exposed ports. The Raspberry Pi Zero W board mounts to this case.
* connector-case.stl - case for the Prototyping pHAT with JST connectors. Snaps onto the
pi-zero-case.
* lcd-cap.stl - a slightly modified version of the PiSugar 
[1.3inch_lcd_cap](https://github.com/PiSugar/pisugar-case-pihat-cap/blob/master/1.3inch_lcd_cap/pisugar_case_lcd_cap.STL)
with fillets to beef up the clips.  You will need to print the buttons and joystick cap from
the original design. The file is
[pisugar_case_lcd_button_comp.STL](https://github.com/PiSugar/pisugar-case-pihat-cap/blob/master/1.3inch_lcd_cap/pisugar_case_lcd_button_comp.STL).

* mount.stl

#### License

To conform to [JdaieLin](https://github.com/JdaieLin)'s 
licensing for the PiSugar from which these components are
derived, the Controller case components are released under the 
[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

## Hardware

The Starting Gate is controlled by a Raspberry Pi Zero W.  These are available for about $10 without the GPIO header or about $15 for the Pi Zero WH model with preinstalled GPIO headers.

![IR Sensors](../images/GPIO-zero.jpg)

### GPIO Usage

| SYMBOL | BROADCOM GPIO (BCM) | RASPBERRY PI PIN | DESCRIPTION |
|:------:|:-------------------:|:----------------:|:-----------:|
| KEY1 | GPIO21 | 40 | Button 1/GPIO |
| KEY2 | GPIO20 | 38 | Button 2/GPIO |
| KEY3 | GPIO16 | 36 | Button 3/GPIO |
| Joystick Up | GPIO6 | 31 | Joystick Up |
| Joystick Down | GPIO19 | 35 | Joystick Down |
| Joystick Left | GPIO5 | 29 | Joystick Left |
| Joystick Right | GPIO26 | 37 | Joystick Right |
| Joystick Press | GPIO13 | 33 | Joystick Press |
| SCLK | GPIO11/SCLK | 23 | SPI clock input |
| MOSI | GPIO10/MOSI | 19 | SPI data input |
| DC | GPIO25 | 22 | Data/Command selection (high for data, low for command) |
| CS | GPIO8/CE0 | 24 | Chip selection, low active |
| RST | GPIO27 | 13 | Reset, low active |
| BL | GPIO24 | 18 | Backlight |
| Servo | GPIO12 (PWM0) | 32 | Servo |
| LANE1 | GPIO7 | 26 | Lane 1 Sensor |
| LANE2 | GPIO23 | 16 | Lane 2 Sensor |
| LANE3 | GPIO22 | 15 | Lane 3 Sensor |
| LANE4 | GPIO4 | 7 | Lane 4 Sensor |


### Prototyping pHAT Schematic

Connections to the car release servo and lane car sensors
are made via JST connectors soldered to a [ModMyPi Zero Prototyping
pHAT.](https://www.pishop.us/product/zero-prototyping-phat-zero/). The
schematic is shown below.

![GPIO Usage](../images/Schematics-3.3V.png)

### Waveshare 1.3" LED HAT

![LCD HAT](../images/waveshare-lcd.png)

## Raspberry Pi Setup

### Install Raspbian


Detailed notes on initial setup:

1. Install the last version of Raspbian, which is based on the 4.19 kernel.  Raspberry Pi OS is
based on kernel version 5.4 kernel which has dropped support for the fb1 framebuffer as 
fbtft_device.  The Wavefront 1.3" LCD HAT does not have Raspberry Pi Device Tree support to
work with the 5.4 kernel.  Get the download image from:

	https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2020-02-14/

    I chose Raspberry Pi OS Lite, as I didn't need a GUI.  Follow the instructions at:

	https://www.raspberrypi.org/documentation/installation/installing-images/README.md

    Follow the instructions to create a wpa_supplicant.conf file in the boot partition:

	https://www.raspberrypi.org/documentation/configuration/wireless/headless.md

    If you want ssh access, also create an empty file named 'ssh' in the boot partition.

1.  Run configure 

      ```
      % sudo raspi-config
      ```

    And perform the following:

    1. Change User Password

       Change the default password from raspberry to something else

    1. Network Options

       If you didn't set up wireless config via wpa_supplicant.conf on the sd card,
       navigate to "Network Options" -> "N2 Wireless LAN" and setup your SSID and
       passphrase.

    1. Localisation Options

       Set your timezone (and Keyboard, Locale or any other options you like)

    1. Interfacing Options

       Enable "P4 SPI"

    1. Advanced Options

       A1 Expand Filesystem

    Note: I also enabled SSH via "5 Interfacing Options" -> "P2 SSH"

    When asked to reboot, select Yes

1.  Update the OS to the latest 4.19.118 packages.  DO NOT ALLOW IT TO UPDATE TO 5.x, the display HAT won't work!

      ```
      % sudo apt-get update
      % sudo apt-get upgrade
      ```

1.  Install Python 3 and the necessary libraries

      ```
      % sudo apt-get install python3 python3-gpiozero python3-pigpio python3-bluez python3-pip wiringpi
      % sudo apt autoremove
      ```

1.  Have pigpiod start on every boot

      ```
      % sudo systemctl enable pigpiod
      ```

1. Update default config.txt

      ```
      % sudo nano /boot/config.txt
      ```
    
    Disable audio since we aren't going to be using it and we want the PCM driver for the
    servo

      ```
      #dtparam=audio=on
      dtparam=spi=on
      ```

    TODO: Verify this is needed - Setup framebuffer device

      ```
      [ALL]
      hdmi_force_hotplug = 1
      hdmi_cvt = 240 240 60 1 0 0 0
      hdmi_group = 2
      hdmi_mode = 1
      hdmi_mode = 87
      display_rotate = 1
      ```

1.  Enable framebuffer modules

      ```
    % sudo nano /etc/modules
      ```
    
      ```
    spi-bcm2835
    flexfb
    fbtft_device
      ```

1. Create fbtft.conf

      ```
   % sudo nano /etc/modprobe.d/fbtft.conf
      ```

   Add the lines:

      ```
   options fbtft_device name=flexfb gpios=reset:27,dc:25,cs:8,led:24 speed=40000000 bgr=1 fps=60 custom=1 height=240 width=240
   options flexfb gsetaddrwin=0 width=240 height=240 init=-1,0x11,-2,120,-1,0x36,0x70,-1,0x3A,0x05,-1,0xB2,0x0C,0x0C,0x00,0x33,0x33,-1,0xB7,0x35,-1,0xBB,0x1A,-1,0xC0,0x2C,-1,0xC2,0x01,-1,0xC3,0x0B,-1,0xC4,0x20,-1,0xC6,0x0F,-1,0xD0,0xA4,0xA1,-1,0x21,-1,0xE0,0x00,0x19,0x1E,0x0A,0x09,0x15,0x3D,0x44,0x51,0x12,0x03,0x00,0x3F,0x3F,-1,0xE1,0x00,0x18,0x1E,0x0A,0x09,0x25,0x3F,0x43,0x52,0x33,0x03,0x00,0x3F,0x3F,-1,0x29,-3 
      ```

1. Build and install rpi-fbcp

      ```
    % cd
    % sudo apt-get install -y git build-essential cmake
    % git clone https://github.com/tasanakorn/rpi-fbcp
    % mkdir -p rpi-fbcp/build
    % cd rpi-fbcp/build
    % cmake ..
    % make
    % sudo install fbcp /usr/local/bin/fbcp
    % cd
      ```

1. Install raylib

   * Build raylib from source https://github.com/raysan5/raylib/wiki/Working-on-Raspberry-Pi

      ```
   % wget https://github.com/raysan5/raylib/archive/2.6.0.tar.gz
   % tar xzf 2.6.0.tar.gz
   % cd 
      ```

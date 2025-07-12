#! /usr/bin/bash

cd /tmp

cat > waveshare-1_3-LCD-HAT.txt << __EOF__
# This was taken from notro's response in the Raspberry Pi forum:
#
#    https://forums.raspberrypi.com/viewtopic.php?t=337019
#
# for configuring a Waveshare 2.0 inch display. The original Waveshare
# Wiki instructions for the 1.3" display HAT had a slightly different 
# initialization sequence. I merged the differences to preserve the
# values from the 1.3" HAT Wiki where they differed.
# 
# Compile and install via:
#
#  ./mipi-dbi-cmd.txt waveshare-1_3-LCD-HAT.bin waveshare-1_3-LCD-HAT.txt 
#  sudo cp waveshare-1_3-LCD-HAT.bin /lib/firmware/

command 0x11				# 0x1000011
delay 255				# 0x20000ff

# the fbtft driver overwrites this in set_var(), need to pick the value from the driver
# 0x1000036 0xA0

# dts has rotate=90 + bgr: driver converts to:  MADCTL_BGR | MADCTL_MV | MADCTL_MY
#tjq command 0x36 0xA8			# MADCTL MY | MV | RGB
command 0x36 0x78			# MADCTL MX | MV | ML | RGB

command 0x3a 0x05			# 0x100003a 0x05
command 0x21 				# 0x1000021 
command 0x2a 0x00 0x01 0x00 0x3f	# 0x100002a 0x00 0x01 0x00 0x3f
command 0x2b 0x00 0x00 0x00 0xef	# 0x100002b 0x00 0x00 0x00 0xef
command 0xb2 0x0c 0x0c 0x00 0x33 0x33	# 0x10000b2 0x0c 0x0c 0x00 0x33 0x33
command 0xb7 0x35			# 0x10000b7 0x35
#tjq command 0xbb 0x1f			# 0x10000bb 0x1f # Set VCOM to 0.875V
command 0xbb 0x1a			# 0x10000bb 0x1a # Set VCOM to 0.75V
command 0xc0 0x0c			# 0x10000c0 0x0c
command 0xc2 0x01			# 0x10000c2 0x01
#tjq command 0xc3 0x12			# 0x10000c3 0x12 # VRHS 4.45V + ...
command 0xc3 0x0b			# 0x10000c3 0x0b # VRHS 4.1V + ...
command 0xc4 0x20			# 0x10000c4 0x20
command 0xc6 0x0f			# 0x10000c6 0x0f
command 0xd0 0xa4 0xa1			# 0x10000d0 0xa4 0xa1
#tjq command 0xe0 0xd0 0x08 0x11 0x08 0x0C 0x15 0x39 0x33 0x50 0x36 0x13 0x14 0x29 0x2d	# 0x10000e0 [...]
#tjq command 0xe1 0xd0 0x08 0x10 0x08 0x06 0x06 0x39 0x44 0x51 0x0b 0x16 0x14 0x2f 0x31	# 0x10000e1 [...]
command 0xE0 0x00 0x19 0x1E 0x0A 0x09 0x15 0x3D 0x44 0x51 0x12 0x03 0x00 0x3F 0x3F # Set Positive Voltage Gamma Control
command 0xE1 0x00 0x18 0x1E 0x0A 0x09 0x25 0x3F 0x43 0x52 0x33 0x03 0x00 0x3F 0x3F # Set Negative Voltage Gamma Control
command 0x29				# 0x1000029
__EOF__

#
# notro maintains a github repository (https://github.com/notro/panel-mipi-dbi) containing a Python program 
# originally written by Noralf Trønnes to convert the above text representation of an initialization sequence
# into a binary file suitable for loading by the kernel. Since Noralf Trønnes explicitly released the program
# to the public domain, I simply include a copy here rather than require separate download.
#

cat > mipi-dbi-cmd << __EOF__
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: CC0-1.0
#
# Written in 2022 by Noralf Trønnes <noralf@tronnes.org>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from __future__ import print_function
import argparse
import sys


def hexstr(buf):
    return ' '.join('{:02x}'.format(x) for x in buf)


def parse_binary(buf):
    if len(buf) < 18:
        raise ValueError('file too short, len=%d' % len(buf))
    if buf[:15] != b'MIPI DBI\x00\x00\x00\x00\x00\x00\x00':
        raise ValueError('wrong magic: %s' % hexstr(buf[:15]))
    if buf[15] != 1:
        raise ValueError('wrong version: %d' % (buf[15]))

    result = ''
    cmds = buf[16:]
    i = 0
    while i < len(cmds):
        try:
            pos = i
            cmd = cmds[i]
            i += 1
            num_params = cmds[i]
            i += 1
            params = cmds[i:i+num_params]
            if len(params) != num_params:
                raise IndexError()

            if cmd == 0x00 and num_params == 1:
                s = 'delay %d\n' % params[0]
            else:
                s = 'command 0x%02x' % cmd
                if params:
                    s += ' '
                    s += ' '.join('0x{:02x}'.format(x) for x in params)
                s += '\n'
        except IndexError:
            raise ValueError('malformed file at offset %d: %s' % (pos + 16, hexstr(cmds[pos:])))
        i += num_params
        result += s

    return result


def print_file(fn):
    with open(args.fw_file, mode='rb') as f:
        fw = f.read()
    s = parse_binary(bytearray(fw))
    print(s)


def parse_values(parts):
    vals = []
    for x in parts:
        try:
            val = int(x, 0)
        except ValueError:
            raise ValueError('not a number: %s' % x)
        if val < 0 or val > 255:
            raise ValueError('value out of bounds: %s (%d)' % (hex(val), val))
        vals.append(val)
    return vals


def make_file(fw_file, input_file):
    with open(input_file, mode='r') as f:
        lines = f.readlines()

    buf = bytearray()
    buf.extend(b'MIPI DBI\x00\x00\x00\x00\x00\x00\x00') # magic
    buf.append(1) # version

    for idx, line in enumerate(lines):
        # strip off comments and skip empty lines
        comment_idx = line.find('#')
        if comment_idx >= 0:
            line = line[:comment_idx]
        line = line.strip()
        if not line:
            continue

        try:
            parts = line.split()
            if parts[0] == 'command':
                vals = parse_values(parts[1:])
                buf.append(vals[0])
                num_params = len(vals) - 1
                buf.append(num_params)
                if num_params:
                    buf.extend(vals[1:])
            elif parts[0] == 'delay':
                vals = parse_values(parts[1:])
                if len(vals) != 1:
                    raise ValueError('delay takes exactly one argument')
                buf.append(0x00)
                buf.append(1)
                buf.append(vals[0])
            else:
                raise ValueError('unknown keyword: %s' % parts[0])
        except ValueError as e:
            raise ValueError('error: %s\nline %d: %s' % (e, idx + 1, line))

    with open(fw_file, mode='wb') as f:
        f.write(buf)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MIPI DBI Linux driver firmware tool')
    parser.add_argument('fw_file', help='firmware binary file')
    parser.add_argument('input', nargs='?', help='Input commands file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-d', '--debug', action='store_true', help='Print exception callstack')
    args = parser.parse_args()

    try:
        if args.input:
                make_file(args.fw_file, args.input)
                if args.verbose:
                    print_file(args.fw_file)
        else:
            print_file(args.fw_file)
    except Exception as e:
        if args.debug:
            raise
        print(e, file=sys.stderr)
        sys.exit(1)
__EOF__

chmod +x ./mipi-dbi-cmd
./mipi-dbi-cmd waveshare-1_3-LCD-HAT.bin waveshare-1_3-LCD-HAT.txt 
cp waveshare-1_3-LCD-HAT.bin /lib/firmware/

if ! grep -q 'fbcon=map:10 fbcon=font:VGA8x8' /boot/firmware/cmdline.txt; then
   echo "Setting up console output on boot"
   sed -i 's!rootwait!rootwait fbcon=map:10 fbcon=font:VGA8x8!g' /boot/firmware/cmdline.txt
fi

echo "Configuring /boot/firmware/config.txt"

raspi-config nonint do_spi 0
sed -i s/^dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/g /boot/firmware/config.txt
sed -i s/^max_framebuffers=2/#max_framebuffers=2/g /boot/firmware/config.txt

if ! grep -q '# Configure Waveshare 1.3" LCD HAT display' /boot/firmware/config.txt; then

  cat >> /boot/firmware/config.txt << __EOF__
[all]
# Configure Waveshare 1.3" LCD HAT display
dtoverlay=mipi-dbi-spi,spi0-0,speed=80000000
dtparam=compatible=waveshare-1_3-LCD-HAT\0panel-mipi-dbi-spi
dtparam=width=240,height=240,width-mm=23,height-mm=23
dtparam=reset-gpio=27,dc-gpio=25,backlight-gpio=24
dtparam=write-only,cpha,cpol
__EOF__
fi

echo 'Installation complete. Reboot Now? (y/n)'
read x
if [[ "$x" == "y" ]]; then
   /sbin/reboot now
fi

#! /usr/bin/python3

"""
Diecast Remote Raceway - Input

The Input class implements text input using the Waveshare 1.3" LCD HAT joystick and keys.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import time

import pyray
from pyray import BLACK, WHITE, GRAY, LIGHTGRAY, RAYWHITE

from deviceio import DeviceIO, JOYU, JOYD, JOYL, JOYR, JOYP

#
# Input via selection from a 6x6 grid.  Grid positions are numbered:
#
# [ text input box     ]
#  0,  1,  2,  3,  4,  5
#  6,  7,  8,  9, 10, 11
# 12, 13, 14, 15, 16, 17
# 18, 19, 20, 21, 22, 23
# 24, 25, 26, 27, 28, 29
#

# Given the current cursor position, the cell to move to when the
# joystick key is pressed in each direction.

UP = [  24, 25, 26, 27, 28, 29,
         0,  1,  2,  3,  4,  5,
         6,  7,  8,  9, 10, 11,
        12, 13, 14, 15, 16, 17,
        18, 19, 20, 21, 22, 23]

DOWN = [ 6,  7,  8,  9, 10, 11,
        12, 13, 14, 15, 16, 17,
        18, 19, 20, 21, 22, 23,
        24, 25, 26, 27, 28, 29,
         0,  1,  2,  3,  4,  5]

LEFT = [ 5,  0,  1,  2,  3,  4,
        11,  6,  7,  8,  9, 10,
        17, 12, 13, 14, 15, 16,
        23, 18, 19, 20, 21, 22,
        29, 24, 25, 26, 27, 28]

RIGHT = [1,  2,  3,  4,  5,  0,
         7,  8,  9, 10, 11,  6,
        13, 14, 15, 16, 17, 12,
        19, 20, 21, 22, 23, 18,
        25, 26, 27, 28, 29, 24]

# Character maps for each input mode
UPPER =   ["A", "B", "C", "D", "E", "F",
           "G", "H", "I", "J", "K", "L",
           "M", "N", "O", "P", "Q", "R",
           "S", "T", "U", "V", "W", "X",
           "Y", "Z", " ", " ", " ", " "]

LOWER =   ["a", "b", "c", "d", "e", "f",
           "g", "h", "i", "j", "k", "l",
           "m", "n", "o", "p", "q", "r",
           "s", "t", "u", "v", "w", "x",
           "y", "z", " ", " ", " ", " "]

SPECIAL = ["0", "1", "2", "3", "4", "5",
           "6", "7", "8", "9", ",", ".",
           ":", ";", "'", '"', "+", "=",
           "!", "@", "#", "$", "%", "?",
           "&", "*", "(", ")", "-", "_"]

# Names of character maps
MODE_UPPER = 1
MODE_LOWER = 2
MODE_SPECIAL = 3

class Input:

    """
    Input():

    This class provides text input via the joystick and keys on the
    Waveshare 1.3" LCD HAT.

    get_string() displays a grid of characters.  The joystick is used
    to move around the grid.  Pressing the joystick adds the current
    character to the text input string.

    * Key 1: toggles between upper case, lower case and numbers/punctuation/symbols
    * Key 2: removes the last letter from the input string
    * Key 3: accepts the current string

    """

# PUBLIC

    def get_string(self, mode=MODE_UPPER):
        """
        Display text input menu and collect an input string.

        Return: the string input by the user
        """

        def font_size(input_string):
            """
            Determine font size to fit input string into display area in the top box
            """
            length = len(input_string)
            if length <= 12:
                return 28
            if length <= 15:
                return 20
            if length <= 18:
                return 16
            return 12

        self.cursor_pos = 0
        self.input_complete = False
        self.mode = mode
        self.string = ""

        self.device.push_key_handlers(self.__key1, self.__key2, self.__key3, self.__joystick)

        while not self.input_complete:
            display_string = ""

            pyray.begin_drawing()
            pyray.clear_background(RAYWHITE)

            #blink = int(time.monotonic_ns()/400000000) % 2
            blink = int(time.monotonic()*4) % 2

            if blink == 0:
                display_string = self.string + "_"
            else:
                display_string = self.string

            self.__text_box(display_string, 0, 0, 240, 40, font_size(self.string), True)

            if self.mode == MODE_UPPER:
                for pos, char in enumerate(UPPER):
                    self.__character_position(char, pos)
                self.__character_box("SPACE", 80, 200, 160, 40, 28, self.cursor_pos > 25)
            elif self.mode == MODE_LOWER:
                for pos, char in enumerate(LOWER):
                    self.__character_position(char, pos)
                self.__character_box("space", 80, 200, 160, 40, 28, self.cursor_pos > 25)
            elif self.mode == MODE_SPECIAL:
                for pos,char in enumerate(SPECIAL):
                    self.__character_position(char, pos)
            else:
                print("INVALID MODE!")

            pyray.end_drawing()

        self.device.pop_key_handlers()
        return self.string

# PRIVATE

    def __init__(self, font):

        self.font = font

        self.device = DeviceIO()

        self.cursor_pos = 0
        self.input_complete = False
        self.mode = MODE_UPPER
        self.string = ""

    def __key1(self):
        """
        Select the input mode: Upper case letters, lower case letters or numeric/punctuation
        """
        print("input: __key1")
        self.mode += 1
        if self.mode > 3:
            self.mode = 1

    def __key2(self):
        """
        Remove the last letter from the input string
        """
        print("input: __key2")
        self.string = self.string[:-1]

    def __key3(self):
        """
        Select the current input string and return to the caller
        """
        print("input: __key3")
        self.input_complete = True

    def __joystick(self, btn):
        print("input: btn.pin: ", btn.pin, "cursor_pos: ", self.cursor_pos)
        if btn.pin == JOYU.pin:
            self.cursor_pos = UP[self.cursor_pos]
            print("  new cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYD.pin:
            self.cursor_pos = DOWN[self.cursor_pos]
            print("  new cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYL.pin:
            self.cursor_pos = LEFT[self.cursor_pos]
            print("  new cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYR.pin:
            self.cursor_pos = RIGHT[self.cursor_pos]
            print("  new cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYP.pin:
            if self.mode == MODE_UPPER:
                self.string = self.string + UPPER[self.cursor_pos]
            elif self.mode == MODE_LOWER:
                self.string = self.string + LOWER[self.cursor_pos]
            elif self.mode == MODE_SPECIAL:
                self.string = self.string + SPECIAL[self.cursor_pos]

    def __text_box(self, text, x, y, width, height, size, gray=False): # pylint: disable=invalid-name
        """
        Draw a box at position (x,y) with a width w and height h.
        Display text b with point size s within the box.
        If gray=True, set the box fill color to gray and the text color to white
        """
        if gray:
            pyray.draw_rectangle_rec([x, y, width, height], LIGHTGRAY)
        else:
            pyray.draw_rectangle_rec([x, y, width, height], WHITE)

        pyray.draw_rectangle_lines(x, y, width, height, BLACK)
        pyray.draw_text_ex(self.font, text, [x+10, y+5], size, 1.0, BLACK)

    def __character_box(self, text, x, y, width, height, size, inverted=False): # pylint: disable=invalid-name
        """
        Draw a box at position (x,y) with a width w and height h.
        Display text b with point size s within th box.
        If gray=True, set the box fill color to gray and the text color to white

        This differs from __text_box() in that it the font size and padding are
        match that of __character_position()
        """
        if inverted:
            pyray.draw_rectangle_rec([x, y, width, height], GRAY)
            pyray.draw_text_ex(self.font, text, [x+10, y+10], size, 1.0, WHITE)
        else:
            pyray.draw_rectangle_rec([x, y, width, height], WHITE)
            pyray.draw_text_ex(self.font, text, [x+10, y+10], size, 1.0, BLACK)
        pyray.draw_rectangle_lines(x, y, width, height, BLACK)

    def __character_position(self, byte_array, grid_pos, width=40):
        """
        Draw a single box arround a single character at the specified grid position
        """

        # pylint: disable=invalid-name
        # x and y are perfectly acceptable names for cartesian coordinates!
        x = 40 * (grid_pos % 6)
        y = 40 + (40 * int(grid_pos/6))
        # pylint: enable=invalid-name

        height = 40

        if grid_pos == self.cursor_pos:
            pyray.draw_rectangle_rec([x, y, width, height], GRAY)
            pyray.draw_text_ex(self.font, byte_array, [x+10, y+10], 28, 1.0, WHITE)
        else:
            pyray.draw_rectangle_rec([x, y, width, height], WHITE)
            pyray.draw_text_ex(self.font, byte_array, [x+10, y+10], 28, 1.0, BLACK)
        pyray.draw_rectangle_lines(x, y, width, height, BLACK)

def main():
    """
    When run as main program, create Menu object and run main function
    """
    pyray.init_window(240, 240, "Menu Test")
    pyray.set_target_fps(30)
    pyray.hide_cursor()

    font = pyray.load_font("fonts/Roboto-Black.ttf")
    inp = Input(font)

    while True:
        string = inp.get_string()
        print("User input '", string, "'")
        if string == "done":
            break

if __name__ == '__main__':
    main()

# vim: expandtab sw=4

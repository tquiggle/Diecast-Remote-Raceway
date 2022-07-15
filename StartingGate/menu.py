#! /usr/bin/python3

"""
Diecast Remote Raceway - Menu

The menu hierarchy and associated enum values are described below.

My original thought was that I could intelligently use the enum values
in computing transitions while walking the hierarchy.  One digit values
representing top level menu items, two digit values representing second
level menu items, three digit values third level, etc.  This didn't
prove very useful.

The top level menu is treated special. Input is via one of the three
buttons on the right of the display.  The user can select from "Single
Track," "Multi Track" or "Configure" by just pressing the adjacent button
and the action is immediate.  If the user selects "Configure" they are
dumped into the various configuration options where navigation is done
using the joystick. Menu items are selected by pushing the joystick
button.  See the Input class for details on how text input is handled.

TODO:

   * Add menu item to select the name of the finish line to connect to
   * Implement RESET logic to delete saved config and reload from defaults

Logical Menu Layout:

    # __top_menu()
    * SINGLE_TRACK = 1
    * MULTI_TRACK = 2
    * CONFIGURE = 3
        # config_menu()
        * TRACK_NAME = 31
            * ENTER_TRACK_NAME = 311
        * NUM_LANES = 32
            * ENTER_NUM_LANES = 321
        * CAR_ICONS = 33
            # __car_menu()
            * CAR_1_ICON = 331
                * SELECT_CAR_1_ICON = 3311
            * CAR_2_ICON = 332
                * SELECT_CAR_2_ICON = 3321
            * CAR_3_ICON = 333
                * SELECT_CAR_3_ICON = 3331
            * CAR_4_ICON = 334
                * SELECT_CAR_4_ICON = 3341
        * CIRCUIT_NAME = 34
            * ENTER_CIRCUIT_NAME = 341
        * RACE_TIMEOUT = 35
            * ENTER_RACE_TIMEOUT = 351
        * WIFI_SETUP = 36
            # __wifi_menu()
            * WIFI_SSID = 361
                * ENTER_WIFI_SSID = 3611
            * WIFI_PSWD = 362
                * ENTER_WIFI_PSWD = 3621
        * COORDINATOR_SETUP = 37
            # __controller_menu()
            * COORD_HOSTNAME = 371
                * ENTER_COORD_HOSTNAME =3711
            * COORD_PORT = 372
                * ENTER_COORD_PORT =3721
        * SERVO_LIMITS = 38
            # __servo_menu
            * SERVO_DOWN_VALUE = 381
                * ENTER_SERVO_DOWN_VALUE = 3811
            * SERVO_UP_VALUE = 382
                * ENTER_SERVO_UP_VALUE = 3821
        * RESET = 39
            * PERFORM_RESET = 391

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.
"""

import enum
import glob
import time

from deviceio import DeviceIO, JOYU, JOYD, JOYL, JOYR, JOYP, SERVO
from input import Input, MODE_SPECIAL
from config import Config

from raylib.pyray import PyRay
from raylib.colors import BLACK, LIGHTGRAY, ORANGE, RAYWHITE, WHITE

@enum.unique
class MenuState(enum.Enum):
    """
    Enumerate all of the possible menu selection postions
    """
    # __top_menu()
    SINGLE_TRACK = 1
    MULTI_TRACK = 2
    CONFIGURE = 3
    # config_menu()
    TRACK_NAME = 31
    NUM_LANES = 32
    CAR_ICONS = 33
    CIRCUIT_NAME = 34
    RACE_TIMEOUT = 35
    WIFI_SETUP = 36
    COORDINATOR_SETUP = 37
    SERVO_LIMITS = 38
    RESET = 39
    # __car_menu()
    CAR_1_ICON = 331
    CAR_2_ICON = 332
    CAR_3_ICON = 333
    CAR_4_ICON = 334
    # __wifi_menu()
    WIFI_SSID = 361
    WIFI_PSWD = 362
    # __controller_menu()
    COORD_HOSTNAME = 371
    COORD_PORT = 372
    # __servo_menu
    SERVO_DOWN_VALUE = 381
    SERVO_UP_VALUE = 382
    # __perform_reset()
    PERFORM_RESET = 391
    # Terminal entries in menu where we accept user input
    ENTER_TRACK_NAME = 311
    ENTER_NUM_LANES = 321
    SELECT_CAR_1_ICON = 3311
    SELECT_CAR_2_ICON = 3321
    SELECT_CAR_3_ICON = 3331
    SELECT_CAR_4_ICON = 3341
    ENTER_CIRCUIT_NAME = 341
    ENTER_RACE_TIMEOUT = 351
    ENTER_WIFI_SSID = 3611
    ENTER_WIFI_PSWD = 3621
    ENTER_COORD_HOSTNAME = 3711
    ENTER_COORD_PORT = 3721
    ENTER_SERVO_DOWN_VALUE = 3811
    ENTER_SERVO_UP_VALUE = 3821

    def next(self):
        """
        Returns next menu item in enum
        """
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        if index >= len(members):
            index = 0
        return members[index]

    def prev(self):
        """
        Returns previous menu item in enum
        """
        cls = self.__class__
        members = list(cls)
        index = members.index(self) - 1
        if index < 0:
            index = 0
        return members[index]

# Menu transitions when the joystick is pushed UP
UP = {}
UP[MenuState.SINGLE_TRACK] = MenuState.CONFIGURE
UP[MenuState.MULTI_TRACK] = MenuState.SINGLE_TRACK
UP[MenuState.CONFIGURE] = MenuState.MULTI_TRACK
UP[MenuState.TRACK_NAME] = MenuState.RESET
UP[MenuState.NUM_LANES] = MenuState.TRACK_NAME
UP[MenuState.CAR_ICONS] = MenuState.NUM_LANES
UP[MenuState.CAR_1_ICON] = MenuState.CAR_4_ICON
UP[MenuState.CAR_2_ICON] = MenuState.CAR_1_ICON
UP[MenuState.CAR_3_ICON] = MenuState.CAR_2_ICON
UP[MenuState.CAR_4_ICON] = MenuState.CAR_3_ICON
UP[MenuState.CIRCUIT_NAME] = MenuState.CAR_ICONS
UP[MenuState.RACE_TIMEOUT] = MenuState.CIRCUIT_NAME
UP[MenuState.WIFI_SETUP] = MenuState.RACE_TIMEOUT
UP[MenuState.WIFI_SSID] = MenuState.WIFI_PSWD
UP[MenuState.WIFI_PSWD] = MenuState.WIFI_SSID
UP[MenuState.COORDINATOR_SETUP] = MenuState.WIFI_SETUP
UP[MenuState.COORD_HOSTNAME] = MenuState.COORD_PORT
UP[MenuState.COORD_PORT] = MenuState.COORD_HOSTNAME
UP[MenuState.SERVO_LIMITS] = MenuState.COORDINATOR_SETUP
UP[MenuState.RESET] = MenuState.SERVO_LIMITS
UP[MenuState.SERVO_DOWN_VALUE] = MenuState.SERVO_UP_VALUE
UP[MenuState.SERVO_UP_VALUE] = MenuState.SERVO_DOWN_VALUE
UP[MenuState.ENTER_TRACK_NAME] = MenuState.ENTER_TRACK_NAME
UP[MenuState.ENTER_NUM_LANES] = MenuState.ENTER_NUM_LANES
UP[MenuState.ENTER_CIRCUIT_NAME] = MenuState.ENTER_CIRCUIT_NAME
UP[MenuState.ENTER_RACE_TIMEOUT] = MenuState.ENTER_RACE_TIMEOUT
UP[MenuState.ENTER_WIFI_SSID] = MenuState.ENTER_WIFI_SSID
UP[MenuState.ENTER_WIFI_PSWD] = MenuState.ENTER_WIFI_PSWD
UP[MenuState.ENTER_COORD_HOSTNAME] = MenuState.ENTER_COORD_HOSTNAME
UP[MenuState.ENTER_COORD_PORT] = MenuState.ENTER_COORD_PORT
UP[MenuState.ENTER_SERVO_UP_VALUE] = MenuState.ENTER_SERVO_UP_VALUE
UP[MenuState.ENTER_SERVO_DOWN_VALUE] = MenuState.ENTER_SERVO_DOWN_VALUE
UP[MenuState.SELECT_CAR_1_ICON] = MenuState.SELECT_CAR_1_ICON
UP[MenuState.SELECT_CAR_2_ICON] = MenuState.SELECT_CAR_2_ICON
UP[MenuState.SELECT_CAR_3_ICON] = MenuState.SELECT_CAR_3_ICON
UP[MenuState.SELECT_CAR_4_ICON] = MenuState.SELECT_CAR_4_ICON

# Menu transitions when the joystick is pushed DOWN
DOWN = {}
DOWN[MenuState.SINGLE_TRACK] = MenuState.MULTI_TRACK
DOWN[MenuState.MULTI_TRACK] = MenuState.CONFIGURE
DOWN[MenuState.CONFIGURE] = MenuState.SINGLE_TRACK

DOWN[MenuState.TRACK_NAME] = MenuState.NUM_LANES
DOWN[MenuState.NUM_LANES] = MenuState.CAR_ICONS
DOWN[MenuState.CAR_ICONS] = MenuState.CIRCUIT_NAME
DOWN[MenuState.CAR_1_ICON] = MenuState.CAR_2_ICON
DOWN[MenuState.CAR_2_ICON] = MenuState.CAR_3_ICON
DOWN[MenuState.CAR_3_ICON] = MenuState.CAR_4_ICON
DOWN[MenuState.CAR_4_ICON] = MenuState.CAR_1_ICON
DOWN[MenuState.CIRCUIT_NAME] = MenuState.RACE_TIMEOUT
DOWN[MenuState.RACE_TIMEOUT] = MenuState.WIFI_SETUP
DOWN[MenuState.WIFI_SETUP] = MenuState.COORDINATOR_SETUP
DOWN[MenuState.WIFI_SSID] = MenuState.WIFI_PSWD
DOWN[MenuState.WIFI_PSWD] = MenuState.WIFI_SSID
DOWN[MenuState.COORDINATOR_SETUP] = MenuState.SERVO_LIMITS
DOWN[MenuState.COORD_HOSTNAME] = MenuState.COORD_PORT
DOWN[MenuState.COORD_PORT] = MenuState.COORD_HOSTNAME
DOWN[MenuState.SERVO_LIMITS] = MenuState.RESET
DOWN[MenuState.SERVO_DOWN_VALUE] = MenuState.SERVO_UP_VALUE
DOWN[MenuState.SERVO_UP_VALUE] = MenuState.SERVO_DOWN_VALUE
DOWN[MenuState.RESET] = MenuState.TRACK_NAME
DOWN[MenuState.ENTER_TRACK_NAME] = MenuState.ENTER_TRACK_NAME
DOWN[MenuState.ENTER_NUM_LANES] = MenuState.ENTER_NUM_LANES
DOWN[MenuState.ENTER_CIRCUIT_NAME] = MenuState.ENTER_CIRCUIT_NAME
DOWN[MenuState.ENTER_RACE_TIMEOUT] = MenuState.ENTER_RACE_TIMEOUT
DOWN[MenuState.ENTER_WIFI_SSID] = MenuState.ENTER_WIFI_SSID
DOWN[MenuState.ENTER_WIFI_PSWD] = MenuState.ENTER_WIFI_PSWD
DOWN[MenuState.ENTER_COORD_HOSTNAME] = MenuState.ENTER_COORD_HOSTNAME
DOWN[MenuState.ENTER_SERVO_UP_VALUE] = MenuState.ENTER_SERVO_DOWN_VALUE
DOWN[MenuState.ENTER_SERVO_DOWN_VALUE] = MenuState.ENTER_SERVO_UP_VALUE
DOWN[MenuState.ENTER_COORD_PORT] = MenuState.ENTER_COORD_PORT
DOWN[MenuState.SELECT_CAR_1_ICON] = MenuState.SELECT_CAR_1_ICON
DOWN[MenuState.SELECT_CAR_2_ICON] = MenuState.SELECT_CAR_2_ICON
DOWN[MenuState.SELECT_CAR_3_ICON] = MenuState.SELECT_CAR_3_ICON
DOWN[MenuState.SELECT_CAR_4_ICON] = MenuState.SELECT_CAR_4_ICON

# Menu transitions when the joystick is pushed LEFT
LEFT = {}
LEFT[MenuState.SINGLE_TRACK] = MenuState.SINGLE_TRACK
LEFT[MenuState.MULTI_TRACK] = MenuState.MULTI_TRACK
LEFT[MenuState.CONFIGURE] = MenuState.CONFIGURE
LEFT[MenuState.TRACK_NAME] = MenuState.CONFIGURE
LEFT[MenuState.NUM_LANES] = MenuState.CONFIGURE
LEFT[MenuState.CAR_ICONS] = MenuState.CONFIGURE
LEFT[MenuState.CAR_1_ICON] = MenuState.CAR_ICONS
LEFT[MenuState.CAR_2_ICON] = MenuState.CAR_ICONS
LEFT[MenuState.CAR_3_ICON] = MenuState.CAR_ICONS
LEFT[MenuState.CAR_4_ICON] = MenuState.CAR_ICONS
LEFT[MenuState.CIRCUIT_NAME] = MenuState.CONFIGURE
LEFT[MenuState.RACE_TIMEOUT] = MenuState.CONFIGURE
LEFT[MenuState.WIFI_SETUP] = MenuState.CONFIGURE
LEFT[MenuState.WIFI_SSID] = MenuState.WIFI_SETUP
LEFT[MenuState.WIFI_PSWD] = MenuState.WIFI_SETUP
LEFT[MenuState.COORDINATOR_SETUP] = MenuState.CONFIGURE
LEFT[MenuState.COORD_HOSTNAME] = MenuState.COORDINATOR_SETUP
LEFT[MenuState.COORD_PORT] = MenuState.COORDINATOR_SETUP
LEFT[MenuState.SERVO_LIMITS] = MenuState.CONFIGURE
LEFT[MenuState.SERVO_DOWN_VALUE] = MenuState.SERVO_LIMITS
LEFT[MenuState.SERVO_UP_VALUE] = MenuState.SERVO_LIMITS
LEFT[MenuState.RESET] = MenuState.CONFIGURE
LEFT[MenuState.ENTER_TRACK_NAME] = MenuState.TRACK_NAME
LEFT[MenuState.ENTER_NUM_LANES] = MenuState.NUM_LANES
LEFT[MenuState.ENTER_CIRCUIT_NAME] = MenuState.CIRCUIT_NAME
LEFT[MenuState.ENTER_RACE_TIMEOUT] = MenuState.RACE_TIMEOUT
LEFT[MenuState.ENTER_WIFI_SSID] = MenuState.WIFI_SSID
LEFT[MenuState.ENTER_WIFI_PSWD] = MenuState.WIFI_PSWD
LEFT[MenuState.ENTER_COORD_HOSTNAME] = MenuState.COORD_HOSTNAME
LEFT[MenuState.ENTER_COORD_PORT] = MenuState.COORD_PORT
LEFT[MenuState.ENTER_SERVO_UP_VALUE] = MenuState.SERVO_LIMITS
LEFT[MenuState.ENTER_SERVO_DOWN_VALUE] = MenuState.SERVO_LIMITS
LEFT[MenuState.SELECT_CAR_1_ICON] = MenuState.CAR_1_ICON
LEFT[MenuState.SELECT_CAR_2_ICON] = MenuState.CAR_2_ICON
LEFT[MenuState.SELECT_CAR_3_ICON] = MenuState.CAR_3_ICON
LEFT[MenuState.SELECT_CAR_4_ICON] = MenuState.CAR_4_ICON

# Menu transitions when the joystick button is pressed
SELECT = {}
SELECT[MenuState.SINGLE_TRACK] = MenuState.SINGLE_TRACK
SELECT[MenuState.MULTI_TRACK] = MenuState.MULTI_TRACK
SELECT[MenuState.CONFIGURE] = MenuState.TRACK_NAME
SELECT[MenuState.TRACK_NAME] = MenuState.ENTER_TRACK_NAME
SELECT[MenuState.NUM_LANES] = MenuState.ENTER_NUM_LANES
SELECT[MenuState.CAR_ICONS] = MenuState.CAR_1_ICON
SELECT[MenuState.CAR_1_ICON] = MenuState.SELECT_CAR_1_ICON
SELECT[MenuState.CAR_2_ICON] = MenuState.SELECT_CAR_2_ICON
SELECT[MenuState.CAR_3_ICON] = MenuState.SELECT_CAR_3_ICON
SELECT[MenuState.CAR_4_ICON] = MenuState.SELECT_CAR_4_ICON
SELECT[MenuState.CIRCUIT_NAME] = MenuState.ENTER_CIRCUIT_NAME
SELECT[MenuState.RACE_TIMEOUT] = MenuState.ENTER_RACE_TIMEOUT
SELECT[MenuState.WIFI_SETUP] = MenuState.WIFI_SSID
SELECT[MenuState.WIFI_SSID] = MenuState.ENTER_WIFI_SSID
SELECT[MenuState.WIFI_PSWD] = MenuState.ENTER_WIFI_PSWD
SELECT[MenuState.COORDINATOR_SETUP] = MenuState.COORD_HOSTNAME
SELECT[MenuState.COORD_HOSTNAME] = MenuState.ENTER_COORD_HOSTNAME
SELECT[MenuState.COORD_PORT] = MenuState.ENTER_COORD_PORT
SELECT[MenuState.SERVO_LIMITS] = MenuState.SERVO_DOWN_VALUE
SELECT[MenuState.RESET] = MenuState.RESET
SELECT[MenuState.ENTER_TRACK_NAME] = MenuState.ENTER_TRACK_NAME
SELECT[MenuState.ENTER_NUM_LANES] = MenuState.ENTER_NUM_LANES
SELECT[MenuState.ENTER_CIRCUIT_NAME] = MenuState.ENTER_CIRCUIT_NAME
SELECT[MenuState.ENTER_RACE_TIMEOUT] = MenuState.ENTER_RACE_TIMEOUT
SELECT[MenuState.ENTER_WIFI_SSID] = MenuState.ENTER_WIFI_SSID
SELECT[MenuState.ENTER_WIFI_PSWD] = MenuState.ENTER_WIFI_PSWD
SELECT[MenuState.ENTER_COORD_HOSTNAME] = MenuState.ENTER_COORD_HOSTNAME
SELECT[MenuState.ENTER_COORD_PORT] = MenuState.ENTER_COORD_PORT
SELECT[MenuState.SERVO_DOWN_VALUE] = MenuState.ENTER_SERVO_DOWN_VALUE
SELECT[MenuState.SERVO_UP_VALUE] = MenuState.ENTER_SERVO_UP_VALUE
SELECT[MenuState.SELECT_CAR_1_ICON] = MenuState.SELECT_CAR_1_ICON
SELECT[MenuState.SELECT_CAR_2_ICON] = MenuState.SELECT_CAR_2_ICON
SELECT[MenuState.SELECT_CAR_3_ICON] = MenuState.SELECT_CAR_3_ICON
SELECT[MenuState.SELECT_CAR_4_ICON] = MenuState.SELECT_CAR_4_ICON

# Text string displayed for each menu position
TEXT = {}
TEXT[MenuState.SINGLE_TRACK] = "Single Track"
TEXT[MenuState.MULTI_TRACK] = "Multi Track"
TEXT[MenuState.CONFIGURE] = "Configure"
TEXT[MenuState.TRACK_NAME] = "Track Name"
TEXT[MenuState.NUM_LANES] = "# of Lanes"
TEXT[MenuState.CAR_ICONS] = "Car Icons"
TEXT[MenuState.CAR_1_ICON] = "Car 1 Icon"
TEXT[MenuState.CAR_2_ICON] = "Car 2 Icon"
TEXT[MenuState.CAR_3_ICON] = "Car 3 Icon"
TEXT[MenuState.CAR_4_ICON] = "Car 4 Icon"
TEXT[MenuState.CIRCUIT_NAME] = "Circuit"
TEXT[MenuState.RACE_TIMEOUT] = "Race Timeout"
TEXT[MenuState.WIFI_SETUP] = "WiFi Setup"
TEXT[MenuState.WIFI_SSID] = "WiFi SSID"
TEXT[MenuState.WIFI_PSWD] = "WiFi Password"
TEXT[MenuState.COORDINATOR_SETUP] = "Coordinator"
TEXT[MenuState.COORD_HOSTNAME] = "Coordinator Hostname"
TEXT[MenuState.COORD_PORT] = "Coordinator Port"
TEXT[MenuState.SERVO_LIMITS] = "Servo Limits"
TEXT[MenuState.SERVO_DOWN_VALUE] = "Servo Down Value"
TEXT[MenuState.SERVO_UP_VALUE] = "Servo Up Value"
TEXT[MenuState.RESET] = "Factory Reset"

# Display function to call based on current menu position
FUNCTION = {}

class Menu:
    """
    This class implements the menu displayed at startup.  There is a single public
    method, process_menus(), to perform all menu operations.

    process_menus() updates the global config settings

    """

# PUBLIC

    def process_menus(self):
        """
        The main method that displays and walks the menu tree. The choice of
        SINGLE_TRACK vs MULTI_TRACK is set in the config.num_tracks

        The config is written back to disk if it was modified
        """

        print("process_menus: self=", self)
        self.race_type = None;
        self.device.push_key_handlers(self.__key1, self.__key2, self.__key3, self.__joystick)
        while (not self.pyray.window_should_close()) and (self.race_type is None):
            if self.cursor_pos != self.last_cursor_pos:
                print("self.cursor_pos=", self.cursor_pos,
                      ", self.config_window_top=", self.config_window_top,
                      ", self.config_window_bottom=", self.config_window_bottom)
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.last_cursor_pos = self.cursor_pos
            FUNCTION[self.cursor_pos]()
            self.pyray.end_drawing()
        self.device.pop_key_handlers()
        if self.config_updated:
            self.config.save()

# PRIVATE

    def __init__(self, pyray, font, config):
        self.pyray = pyray
        self.font = font
        self.config = config

        self.input = Input(self.pyray, self.font)
        self.device = DeviceIO()
        self.race_type = None

        # The config object passed in was modified by the user within the configuration menu
        self.config_updated = False
        self.race_timeout_updated = False

        # Initialize attributes used to select the number of lanes
        self.num_lanes_selected = False
        self.num_lanes_pos = False

        # Initialize attributes used to set servo limits
        self.servo_down_value_updated = False
        self.servo_up_value_updated = False

        self.cursor_pos = MenuState.SINGLE_TRACK         # Start at the top of the main menu
        self.current_func = self.__top_menu              # Dispaly loop calls __top_menu function
        self.config_window_top = MenuState.TRACK_NAME    # Initial config menu window top
        self.config_window_bottom = MenuState.TRACK_NAME # Initial config menu window bottom
        self.config_menu_pos = self.config_window_top    # Initial window position for config menu
        self.config_menu_first = MenuState.TRACK_NAME    # Top of config menu, up wraps
        self.config_menu_last = MenuState.RESET          # Bottom of config menu, down wraps
        self.last_cursor_pos = MenuState.RESET
        self.__init_function_pointers()

        # Initialize attributes used for selecting car images
        self.car_icons_loaded = False
        self.car_icon_index = 0
        self.car_textures = []
        self.car_icon_selected = None

        background_image = self.pyray.load_image("images/background.png")

        self.background_texture = self.pyray.load_texture_from_image(background_image)
        self.pyray.unload_image(background_image)

        single_track_image = self.pyray.load_image("images/Single-Track.png")
        self.single_track_texture = self.pyray.load_texture_from_image(single_track_image)
        self.pyray.unload_image(single_track_image)

        multi_track_image = self.pyray.load_image("images/Multi-Track.png")
        self.multi_track_texture = self.pyray.load_texture_from_image(multi_track_image)
        self.pyray.unload_image(multi_track_image)

        configure_image = self.pyray.load_image("images/Configure.png")
        self.configure_texture = self.pyray.load_texture_from_image(configure_image)
        self.pyray.unload_image(configure_image)

    def __init_function_pointers(self):
        """
        The main loop in process_menus() dispatches to the appropriate menu function based on
        the current menu state.  These are instance-level functions, as they require access to
        object state (self.*).  We need to initialize the FUNCTION dict from within the
        __init__ call.  This initialization is factored out into a separate init function for
        readability.
        """

        FUNCTION[MenuState.SINGLE_TRACK] = self.__top_menu
        FUNCTION[MenuState.MULTI_TRACK] = self.__top_menu
        FUNCTION[MenuState.CONFIGURE] = self.__top_menu
        FUNCTION[MenuState.TRACK_NAME] = self.__config_menu
        FUNCTION[MenuState.NUM_LANES] = self.__config_menu
        FUNCTION[MenuState.CAR_ICONS] = self.__config_menu
        FUNCTION[MenuState.CAR_1_ICON] = self.__car_menu
        FUNCTION[MenuState.CAR_2_ICON] = self.__car_menu
        FUNCTION[MenuState.CAR_3_ICON] = self.__car_menu
        FUNCTION[MenuState.CAR_4_ICON] = self.__car_menu
        FUNCTION[MenuState.CIRCUIT_NAME] = self.__config_menu
        FUNCTION[MenuState.RACE_TIMEOUT] = self.__config_menu
        FUNCTION[MenuState.WIFI_SETUP] = self.__config_menu
        FUNCTION[MenuState.WIFI_SSID] = self.__wifi_menu
        FUNCTION[MenuState.WIFI_PSWD] = self.__wifi_menu
        FUNCTION[MenuState.COORDINATOR_SETUP] = self.__config_menu
        FUNCTION[MenuState.COORD_HOSTNAME] = self.__controller_menu
        FUNCTION[MenuState.COORD_PORT] = self.__controller_menu
        FUNCTION[MenuState.SERVO_LIMITS] = self.__config_menu
        FUNCTION[MenuState.SERVO_DOWN_VALUE] = self.__servo_menu
        FUNCTION[MenuState.SERVO_UP_VALUE] = self.__servo_menu
        FUNCTION[MenuState.RESET] = self.__config_menu
        FUNCTION[MenuState.ENTER_TRACK_NAME] = self.__enter_track_name
        FUNCTION[MenuState.ENTER_NUM_LANES] = self.__enter_num_lanes
        FUNCTION[MenuState.ENTER_CIRCUIT_NAME] = self.__enter_circuit_name
        FUNCTION[MenuState.ENTER_RACE_TIMEOUT] = self.__enter_race_timeout
        FUNCTION[MenuState.ENTER_WIFI_SSID] = self.__enter_wifi_ssid
        FUNCTION[MenuState.ENTER_WIFI_PSWD] = self.__enter_wifi_pswd
        FUNCTION[MenuState.ENTER_COORD_HOSTNAME] = self.__enter_coord_host
        FUNCTION[MenuState.ENTER_COORD_PORT] = self.__enter_coord_port
        FUNCTION[MenuState.ENTER_SERVO_DOWN_VALUE] = self.__enter_servo_down
        FUNCTION[MenuState.ENTER_SERVO_UP_VALUE] = self.__enter_servo_up
        FUNCTION[MenuState.SELECT_CAR_1_ICON] = self.__select_car_1_icon
        FUNCTION[MenuState.SELECT_CAR_2_ICON] = self.__select_car_2_icon
        FUNCTION[MenuState.SELECT_CAR_3_ICON] = self.__select_car_3_icon
        FUNCTION[MenuState.SELECT_CAR_4_ICON] = self.__select_car_4_icon

    def __top_menu(self):
        """
        Display the top level menu with three choices
        """
        #pylint: disable=bad-whitespace
        self.pyray.draw_texture(self.single_track_texture, 10,  45, WHITE)
        if self.config.allow_multi_track:
            self.pyray.draw_texture(self.multi_track_texture,  10, 100, WHITE)
        else:
            self.pyray.draw_texture(self.multi_track_texture,  10, 100, LIGHTGRAY)
        self.pyray.draw_texture(self.configure_texture,    10, 155, WHITE)

    def __config_menu(self):
        """
        Display the 2nd level configure menu.

        There are more options than can fit on the tiny 240x240 screen so the display
        scrolls through a 4 line window.  Scrolling off the bottom menu item shifts the
        window down one.  Similarly, scrolling off the top menu item shifts the window
        up one.  The scrolling wraps such that scrolling down from the last menu option
        starts again at the topmost option.
        """

        self.config_menu_pos = self.config_window_top   # start at top of current window
        for idx in range(4):
            self.__menu_line(self.config_menu_pos, 10, idx*56+16, 210, 40, 26)
            if self.config_window_top == MenuState.RESET:
                break
            self.config_menu_pos = self.config_menu_pos.next()
        self.config_window_bottom = self.config_menu_pos

    def __car_menu(self):
        """
        Display menu to select car icons
        """

        #pylint: disable=bad-whitespace
        self.__menu_line(MenuState.CAR_1_ICON, 10,  16, 210, 40, 28)
        if self.config.num_lanes > 1:
            self.__menu_line(MenuState.CAR_2_ICON, 10,  72, 210, 40, 28)
        if self.config.num_lanes > 2:
            self.__menu_line(MenuState.CAR_3_ICON, 10, 128, 210, 40, 28)
        if self.config.num_lanes > 3:
            self.__menu_line(MenuState.CAR_4_ICON, 10, 184, 210, 40, 28)

    def __wifi_menu(self):
        """
        Display menu to set WiFi SSID and Password
        """

        #pylint: disable=bad-whitespace
        self.__text_box("WiFi:",    00,   0, 210, 40, 28)
        self.__text_box("SSID",     10,  53, 210, 40, 28, self.cursor_pos == MenuState.WIFI_SSID)
        self.__text_box("Password", 10, 146, 210, 40, 28, self.cursor_pos == MenuState.WIFI_PSWD)

    def __controller_menu(self):
        """
        Display menu to configure controler hostname and port
        """

        #pylint: disable=bad-whitespace
        self.__text_box("Coordinator:",  0,   0, 210, 40, 28)
        self.__text_box("Hostname",     10,  53, 210, 40, 28,
                        self.cursor_pos == MenuState.COORD_HOSTNAME)
        self.__text_box("Port",         10, 146, 210, 40, 28,
                        self.cursor_pos == MenuState.COORD_PORT)

    def __load_car_textures(self):
        car_icon_filenames = glob.glob('cars/*-48.png')
        car_icon_filenames.sort()
        for car_filename in car_icon_filenames:
            print("Load car image", car_filename)
            icon_name = car_filename[5:-7]
            if icon_name == "question":
                continue
            car_image = self.pyray.load_image(car_filename)
            car_texture = self.pyray.load_texture_from_image(car_image)
            self.car_textures.append((icon_name, car_texture))
            self.pyray.unload_image(car_image)
        self.car_icons_loaded = True

    def __enter_car_icon(self, car):
        """
        Perform action to enter a car icon
        """
        self.car_icon_selected = False

        if not self.car_icons_loaded:
            self.__load_car_textures()

        self.device.push_key_handlers(self.__key_noop, self.__key_noop, self.__key_noop,
                                      self.__joystick_enter_car_icon)

        while not self.car_icon_selected:
            car_icon, car_texture = self.car_textures[self.car_icon_index]
            self.pyray.begin_drawing()
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.pyray.draw_line_ex([120, 10], [120, 230], 64.0, ORANGE)
            self.__text_box(car_icon, 10, 16, 210, 40, 24)
            self.pyray.draw_texture(car_texture, 96, 90, WHITE)
            self.pyray.end_drawing()

        if self.config.car_icons[car] != car_icon:
            self.config.car_icons[car] = car_icon
            self.config_updated = True

        self.device.pop_key_handlers()
        self.cursor_pos = MenuState.CAR_ICONS

    def __select_car_1_icon(self):
        self.__enter_car_icon(0)
        self.cursor_pos = MenuState.CAR_1_ICON

    def __select_car_2_icon(self):
        self.__enter_car_icon(1)
        self.cursor_pos = MenuState.CAR_2_ICON

    def __select_car_3_icon(self):
        self.__enter_car_icon(2)
        self.cursor_pos = MenuState.CAR_3_ICON

    def __select_car_4_icon(self):
        self.__enter_car_icon(3)
        self.cursor_pos = MenuState.CAR_4_ICON

    def __enter_circuit_name(self):
        """
        Perform action to enter circuit name
        """
        circuit_name = self.input.get_string()
        if circuit_name and (circuit_name != self.config.circuit):
            self.config.circuit = circuit_name
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.CIRCUIT_NAME], self.config.circuit_name)
        self.cursor_pos = MenuState.CIRCUIT_NAME

    def __enter_coord_host(self):
        """
        Perform action to enter coordinator hostname
        """
        coord_host = self.input.get_string()
        if coord_host and (coord_host != self.config.coord_host):
            self.config.coord_host = coord_host
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.COORD_HOSTNAME], self.config.coord_host)
        self.cursor_pos = MenuState.COORD_HOSTNAME

    def __enter_coord_port(self):
        """
        Perform action to enter controller port
        """
        coord_port = self.input.get_string(MODE_SPECIAL)
        if coord_port and (coord_port != self.config.coord_port):
            self.config.coord_port = coord_port
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.COORD_HOSTNAME], self.config.coord_port)
        self.cursor_pos = MenuState.COORD_PORT

    def __enter_num_lanes(self):
        """
        Perform action to enter number of lanes
        """
        print("__enter_num_lanes:")
        num_lanes = self.config.num_lanes
        self.num_lanes_pos = num_lanes
        self.num_lanes_selected = False
        self.device.push_key_handlers(self.__key_noop, self.__key_noop, self.__key_noop,
                                      self.__joystick_enter_num_lanes)
        while not self.num_lanes_selected:
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.__text_box(TEXT[MenuState.RACE_TIMEOUT], 0, 0, 240, 40, 28)
            #pylint: disable=bad-whitespace
            self.__text_box("1",  16, 80, 40, 40, 30, self.num_lanes_pos == 1)
            self.__text_box("2",  72, 80, 40, 40, 30, self.num_lanes_pos == 2)
            self.__text_box("3", 128, 80, 40, 40, 30, self.num_lanes_pos == 3)
            self.__text_box("4", 184, 80, 40, 40, 30, self.num_lanes_pos == 4)
            self.pyray.end_drawing()

        self.device.pop_key_handlers()
        self.cursor_pos = MenuState.NUM_LANES
        if self.num_lanes_pos != num_lanes:
            self.config.num_lanes = self.num_lanes_pos
            self.config_updated = True

    def __enter_race_timeout(self):
        """
        Perform action to enter race timeout
        """
        print("__enter_race_timeout:")
        self.device.push_key_handlers(self.__key_noop, self.__key_noop, self.__key_noop,
                                      self.__joystick_enter_race_timeout)
        self.race_timeout_updated = False
        original_timeout = self.config.race_timeout
        self.pyray.end_drawing()
        while not self.race_timeout_updated:
            value = "%4.2f" % self.config.race_timeout
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.__text_box(TEXT[MenuState.RACE_TIMEOUT], 00, 0, 240, 40, 28)
            self.__text_box(value, 10, 53, 210, 40, 28, False)
            self.pyray.end_drawing()

        self.device.pop_key_handlers()
        self.cursor_pos = MenuState.RACE_TIMEOUT
        self.config_updated = self.config.race_timeout != original_timeout

    def __enter_wifi_pswd(self):
        """
        Perform action to enter WiFi password
        """
        wifi_pswd = self.input.get_string()
        if wifi_pswd and (wifi_pswd != self.config.wifi_pswd):
            self.config.wifi_pswd = wifi_pswd
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.COORD_HOSTNAME], self.config.wifi_pswd)
        self.cursor_pos = MenuState.WIFI_PSWD

    def __enter_wifi_ssid(self):
        """
        Perform action to enter WiFi SSID

        TODO: Get list of broadcast SSIDs along with their signal strength and security status
              and implement chooser rather than having to enter the SSID.
        """
        wifi_ssid = self.input.get_string()
        if wifi_ssid and (wifi_ssid != self.config.wifi_ssid):
            self.config.wifi_ssid = wifi_ssid
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.COORD_HOSTNAME], self.config.wifi_ssid)
        self.cursor_pos = MenuState.WIFI_SSID

    def __servo_menu(self):
        """
        Display menu to set servo limits
        """

        self.__text_box("Servo Limits:", 00, 0, 210, 40, 28)
        self.__text_box("Down", 10, 53, 210, 40, 28, self.cursor_pos == MenuState.SERVO_DOWN_VALUE)
        self.__text_box("Up", 10, 146, 210, 40, 28, self.cursor_pos == MenuState.SERVO_UP_VALUE)

    def __enter_servo_down(self):
        """
        Perform action to enter servo down limit value
        """
        print("__enter_servo_down:")
        self.device.push_key_handlers(self.__key_noop, self.__key_noop, self.__key_noop,
                                      self.__joystick_enter_servo_down)
        self.servo_down_value_updated = False
        original_down_value = self.config.servo_down_value
        self.pyray.end_drawing()
        while not self.servo_down_value_updated:
            SERVO.value = self.config.servo_down_value
            value = "%4.2f" % self.config.servo_down_value
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.__text_box(TEXT[MenuState.SERVO_DOWN_VALUE], 00, 0, 240, 40, 28)
            self.__text_box(value, 10, 53, 210, 40, 28, False)
            self.pyray.end_drawing()

        self.device.pop_key_handlers()
        self.cursor_pos = MenuState.SERVO_DOWN_VALUE
        self.config_updated = self.config.servo_down_value != original_down_value
        SERVO.value = None

    def __enter_servo_up(self):
        """
        Perform action to enter servo up limit value
        """
        print("__enter_servo_up:")
        self.device.push_key_handlers(self.__key_noop, self.__key_noop, self.__key_noop,
                                      self.__joystick_enter_servo_up)
        self.servo_up_value_updated = False
        original_up_value = self.config.servo_up_value
        self.pyray.end_drawing()
        while not self.servo_up_value_updated:
            SERVO.value = self.config.servo_up_value
            value = "%4.2f" % self.config.servo_up_value
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            self.__text_box(TEXT[MenuState.SERVO_UP_VALUE], 00, 0, 240, 40, 28)
            self.__text_box(value, 10, 53, 210, 40, 28, False)
            self.pyray.end_drawing()

        self.device.pop_key_handlers()
        self.cursor_pos = MenuState.SERVO_UP_VALUE
        self.config_updated = self.config.servo_up_value != original_up_value
        SERVO.value = None

    def __enter_track_name(self):
        """
        Perform action to enter track name
        """
        track_name = self.input.get_string()
        if track_name and (track_name != self.config.track_name):
            self.config.track_name = track_name
            self.config_updated = True
        self.__display_setting(TEXT[MenuState.TRACK_NAME], self.config.track_name)
        self.cursor_pos = MenuState.TRACK_NAME

    def __joystick(self, btn):
        """
        Process joystick action.
        """
        print("menu: btn.pin: ", btn.pin, "self.cursor_pos: ", self.cursor_pos)
        if btn.pin == JOYU.pin:
            if self.config_window_top == self.cursor_pos:
                for index in range(4): #pylint: disable=unused-variable
                    self.config_window_top = UP[self.config_window_top]
                print("  new self.config_window_top: ", self.config_window_top)
            self.cursor_pos = UP[self.cursor_pos]
            print("  new self.cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYD.pin:
            if self.cursor_pos == self.config_menu_last:
                self.cursor_pos = self.config_menu_first
                self.config_window_top = self.config_menu_first
                self.config_window_bottom = self.config_menu_first
            else:
                self.cursor_pos = DOWN[self.cursor_pos]
                if self.cursor_pos == self.config_window_bottom:
                    self.config_window_top = DOWN[self.config_window_top]
            print("  new self.cursor_pos: ", self.cursor_pos)
        elif btn.pin == JOYL.pin:
            self.cursor_pos = LEFT[self.cursor_pos]
        elif btn.pin == JOYP.pin:
            print("  Joystick Pressed")
            self.cursor_pos = SELECT[self.cursor_pos]

    def __key1(self):
        """
        User pressed key1 selecting single track race
        """
        print("menu: key1 pressed")
        self.race_type = MenuState.SINGLE_TRACK
        self.config.multi_track = False

    def __key2(self):
        """
        User pressed key2 selecting multi track race
        """
        print("menu: key2 pressed, allow_multi_track=", self.config.allow_multi_track)
        if self.config.allow_multi_track:
            self.race_type = MenuState.MULTI_TRACK
            self.config.multi_track = True

    def __key3(self):
        """
        User pressed key3 to enter configuration menu.
        """
        print("menu: key3 pressed, self=", self)
        self.cursor_pos = MenuState.TRACK_NAME


    def __key_noop(self):
        """
        Callback function for key press that performs no operation
        """
        pass

    def __joystick_enter_race_timeout(self, btn):
        """
        Joystick callback function for use in the ENTER_RACE_TIMEOUT
        """
        if btn.pin == JOYU.pin:
            self.config.race_timeout += 0.1
        elif btn.pin == JOYD.pin:
            self.config.race_timeout -= 0.1
        elif btn.pin == JOYL.pin:
            self.config.race_timeout -= 1.0
        elif btn.pin == JOYR.pin:
            self.config.race_timeout += 1.0
        elif btn.pin == JOYP.pin:
            self.race_timeout_updated = True

    def __joystick_enter_car_icon(self, btn):
        """
        Joystick callback function for use in the ENTER_RACE_TIMEOUT
        """
        if btn.pin == JOYU.pin:
            pass
        elif btn.pin == JOYD.pin:
            pass
        elif btn.pin == JOYL.pin:
            if self.car_icon_index == 0:
                self.car_icon_index = len(self.car_textures)-1
            else:
                self.car_icon_index -= 1
        elif btn.pin == JOYR.pin:
            if self.car_icon_index + 1 == len(self.car_textures):
                self.car_icon_index = 0
            else:
                self.car_icon_index += 1
        elif btn.pin == JOYP.pin:
            self.car_icon_selected = True

    def __joystick_enter_num_lanes(self, btn):
        """
        Joystick callback function for use in the ENTER_NUM_LANES state
        """
        if btn.pin == JOYU.pin:
            pass
        elif btn.pin == JOYD.pin:
            pass
        elif btn.pin == JOYL.pin:
            if self.num_lanes_pos == 1:
                self.num_lanes_pos = 4
            else:
                self.num_lanes_pos -= 1
        elif btn.pin == JOYR.pin:
            if self.num_lanes_pos == 4:
                self.num_lanes_pos = 1
            else:
                self.num_lanes_pos += 1
        elif btn.pin == JOYP.pin:
            self.num_lanes_selected = True

    def __joystick_enter_servo_down(self, btn):
        """
        Joystick callback function for use when adjusting the servo down value
        """
        if btn.pin == JOYU.pin:
            self.config.servo_down_value += 0.01
        elif btn.pin == JOYD.pin:
            self.config.servo_down_value -= 0.01
        elif btn.pin == JOYL.pin:
            self.config.servo_down_value -= 0.1
        elif btn.pin == JOYR.pin:
            self.config.servo_down_value += 0.1
        elif btn.pin == JOYP.pin:
            self.servo_down_value_updated = True

        # Restrict value to -1.0 .. 1.0 otherwise the gpiozero.Servo class will throw an exception
        self.config.servo_down_value = max(self.config.servo_down_value, -1.0)
        self.config.servo_down_value = min(self.config.servo_down_value, 1.0)


    def __joystick_enter_servo_up(self, btn):
        """
        Joystick callback function for use when adjusting the servo up value
        """
        if btn.pin == JOYU.pin:
            self.config.servo_up_value += 0.01
        elif btn.pin == JOYD.pin:
            self.config.servo_up_value -= 0.01
        elif btn.pin == JOYL.pin:
            self.config.servo_up_value -= 0.1
        elif btn.pin == JOYR.pin:
            self.config.servo_up_value += 0.1
        elif btn.pin == JOYP.pin:
            self.servo_up_value_updated = True

        # Restrict value to -1.0 .. 1.0 otherwise the gpiozero.Servo class will throw an exception
        self.config.servo_up_value = max(self.config.servo_up_value, -1.0)
        self.config.servo_up_value = min(self.config.servo_up_value, 1.0)


    def __text_box(self, text, x, y, width, height, size, gray=False):
        """
        Draw a box at position (x,y) with specified width and height.
        Display text with point size size within the box.
        If gray=True, set the box fill color to gray and the text color to white
        """
        if gray:
            self.pyray.draw_rectangle_rec([x, y, width, height], LIGHTGRAY)
        else:
            self.pyray.draw_rectangle_rec([x, y, width, height], WHITE)
        self.pyray.draw_rectangle_lines(x, y, width, height, BLACK)
        self.pyray.draw_text_rec(self.font, text, [x+10, y+5, width-10, height-5],
                                 size, 5.0, True, BLACK)

    def __menu_line(self, state, x, y, width, height, size):
        """
        Display line of menu text corresponding to specified MenuState location
        """
        self.__text_box(TEXT[state], x, y, width, height, size, self.cursor_pos == state)

    def __display_setting(self, config, value):
        display_start = time.monotonic()
        while time.monotonic() - display_start < 1.0:
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)
            self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
            #pylint: disable=bad-whitespace
            self.__text_box(config, 00,   0, 240, 40, 28)
            self.__text_box(value,  10,  53, 210, 40, 28)
            self.pyray.end_drawing()

def main():
    """
    When run as main program, create Menu object and run main function
    """
    main_pyray = PyRay()
    main_config = Config("./config/starting_gate.json")

    main_pyray.init_window(240, 240, "Menu Test")
    main_pyray.set_target_fps(30)
    main_pyray.hide_cursor()

    main_font = main_pyray.load_font("fonts/Roboto-Black.ttf")
    menu = Menu(main_pyray, main_font, main_config)
    menu.process_menus()

if __name__ == '__main__':
    main()

# vim: expandtab sw=4

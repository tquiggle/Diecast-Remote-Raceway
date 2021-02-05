#! /usr/bin/python3

"""
Diecast Remote Raceway - Display

The Display module implements the race UI on the Waveshare 1.3 inch LCD HAT.

At present, the code only supports 2-lane tracks.  The logic needs to be generalized to
support 1 to 4 lanes per track for both tracks. Rendering 8 lanes in an intelligible manner
will be a challenge.

The code currently contains numerous hard-coded numeric values to represent screen x,y
coordinates.  A future rewrite will move all screen coordinates into lookup tables
indexed by number of tracks and number of lanes per track.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.

"""

import enum
import random
import threading
import time

from raylib.pyray import PyRay
from raylib.colors import WHITE, RAYWHITE, GRAY, BLACK, ORANGE

from config import CAR0, CAR1, CAR2, CAR3, Config, NOT_FINISHED #pylint: disable=unused-import
from deviceio import car_1_present, car_2_present
from menu import Menu


@enum.unique
class RaceState(enum.Enum):
    """
    Enumerate the states a race goes through. Used to determine what to display.
    """
    WAIT_MENU = 0                # Waiting for top menu input: 1 track, 2 tracks or configure
    MENU_DONE = 1                # Menu selection made, waiting for next state
    WAIT_FINISH_LINE = 2         # Waiting for Bluetooth connection to the Finish Line
    WAIT_REMOTE_REGISTRATION = 3 #   " for remote track to register in our circuit
    REMOTE_REGISTRATION_DONE = 4 # Remote registration is complete. Load remote icons.
    WAIT_LOCAL_READY = 5         # Waiting for local track to have cars in each position
    WAIT_REMOTE_READY = 6        #   " for remote track to have cars in its starting gate
    COUNTDOWN = 7                # All tracks ready, perform 3 second countdown
    RACE_STARTED = 8             # Race is being run
    RACE_FINISHED = 9            # Race successfully completed, show results
    RACE_TIMEOUT = 10            # Race did not complete w/in configured time, show partial results

class Display(threading.Thread):
    """
    Implements the race display and user interaction on the Waveshare 1.3" LCD HAT

    starting_gate.py creates a single instance of Display to provide the UI. The Display
    object starts a separate thread that continuously updates the display. starting_gate.py
    is responsible for manging the actual race, including (almost) all interactions with the
    sensors, servo, controller and finish line.  As the race proceedes, starting_gate.py
    calls methods of this class to update the display.

    The public methods in this class just update the current display state. The display thread
    uses the current state to dispatch to the appropriate rendering logic.

    Several of the states block the caller until some action completes. E.g. menu input has
    completed or the appropriate textures for the remote car icons have been loaded.
    """

# PUBLIC

    def wait_menu(self):
        """
        Display configuration menu and operate submenus
        """
        self.menu_event.clear()
        self.state = RaceState.WAIT_MENU
        self.menu_event.wait()

    def wait_finish_line(self):
        """
        Display notice that the starting gate is establishing a Bluetooth connection to
        the finish line.
        """
        self.state = RaceState.WAIT_FINISH_LINE

    def wait_remote_registration(self):
        """
        The local racetrack is ready, configured for a multi-track race, and waiting
        for the race coordinator to inidicate that a remote track has joined the circuit.
        """
        self.state = RaceState.WAIT_REMOTE_REGISTRATION

    def remote_registration_done(self):
        """
        The coordinator completed the registration call and returned the remote car icons.
        Load the appropriate textures for the race display.
        """
        self.registration_event.clear()
        self.remote_icons_loaded = False
        self.state = RaceState.REMOTE_REGISTRATION_DONE
        self.registration_event.wait()

    def wait_local_ready(self):
        """
        In this state, the display places an overlay on the track saying "Waiting for Cars"

        The car_#_present() functions from the DeviceIO module read the
        appropriate IR sensor to determine if a car is present in the
        indicated lane. In the WAIT_LOCAL_READY state, the Display loop
        checks for cars via these callbacks and updates the display to
        show car icons at the start of lanes that have cars present.
        """
        self.__reset_car_positions()
        self.state = RaceState.WAIT_LOCAL_READY

    def wait_remote_ready(self):
        """
        In this state, the display places an overlay on the track saying

           "Waiting for <other track name>"

        """
        self.state = RaceState.WAIT_REMOTE_READY

    def countdown(self):
        """
        All conditions to start the race have been met:
           * single track race: all tracks have cars present
           * multi track race:  local track has all cars and the
             controller has signalled that remote tracks are ready

        Display a 3, 2, 1 countdown sequence before returning to the caller.
        """
        self.countdown_event.clear()
        self.countdown_start = time.monotonic()
        self.state = RaceState.COUNTDOWN
        self.countdown_event.wait()

    def race_started(self):
        """
        The race is running. Display cars moving randomly down the tracks.
        """
        self.start = time.monotonic()
        self.state = RaceState.RACE_STARTED

    def race_finished(self, results):
        """
        The race is complete. Display race results
        """
        self.results = results
        self.state = RaceState.RACE_FINISHED
        self.first_results_display = True

    def exit(self):
        """
        Exit the display thread.
        """
        self.running = False

# PRIVATE

    # Maximum distance a car can travel in the race display
    MAX_Y = 150

    __instance = None

    def __load_textures(self):
        """
        Load appropriate sized textures based on the number of tracks (and lanes)
        """

        multi_track = self.config.multi_track

        if multi_track:
            banner_size = 48
            car_icon_size = 24
            checkerboard_size = 34
            y_starting_offset = 40
        else:
            banner_size = 96
            car_icon_size = 48
            checkerboard_size = 64
            y_starting_offset = 10

        # Load the background image
        background_image = self.pyray.load_image("images/raceoff-2.png")
        self.background_texture = self.pyray.load_texture_from_image(background_image)
        self.pyray.unload_image(background_image)
        self.y_starting_offset = y_starting_offset

        checkerboard_image = self.pyray.load_image(
            "images/checkerboard-{}.png".format(checkerboard_size))
        question_image = self.pyray.load_image("cars/question-{}.png".format(car_icon_size))

        first_image = self.pyray.load_image("images/1st-{}.png".format(banner_size))
        second_image = self.pyray.load_image("images/2nd-{}.png".format(banner_size))
        third_image = self.pyray.load_image("images/3rd-{}.png".format(banner_size))
        fail_image = self.pyray.load_image("images/fail-{}.png".format(banner_size))

        # Load textures into VRAM
        self.checkerboard_texture = self.pyray.load_texture_from_image(checkerboard_image)
        self.question_texture = self.pyray.load_texture_from_image(question_image)

        first_texture = self.pyray.load_texture_from_image(first_image)
        second_texture = self.pyray.load_texture_from_image(second_image)
        third_texture = self.pyray.load_texture_from_image(third_image)
        self.fail_texture = self.pyray.load_texture_from_image(fail_image)

        self.place_textures = [first_texture, second_texture, third_texture]

        # Load car textures for local track
        for car in range(self.config.num_lanes):
            icon = self.config.car_icons[car]
            image = self.pyray.load_image("cars/{}-{}.png".format(icon, car_icon_size))
            self.local_textures[car] = self.pyray.load_texture_from_image(image)
            self.pyray.unload_image(image)

        if multi_track:
            # Load car textures for remote track
            for car in range(self.config.remote_num_lanes):
                icon = self.config.remote_car_icons[car]
                # TODO: Handle error condition where remote image isn't found locally
                image = self.pyray.load_image("cars/{}-{}.png".format(icon, car_icon_size))
                self.remote_textures[car] = self.pyray.load_texture_from_image(image)
                self.pyray.unload_image(image)

        # Unload image data from CPU memory
        self.pyray.unload_image(checkerboard_image)
        self.pyray.unload_image(question_image)
        self.pyray.unload_image(first_image)
        self.pyray.unload_image(second_image)
        self.pyray.unload_image(third_image)
        self.pyray.unload_image(fail_image)

    def __new__(cls, val):
        """
        Override the new operator to enforce that all allocations share a singleton object
        """
        if Display.__instance is None:
            Display.__instance = object.__new__(cls)
        Display.__instance.val = val
        return Display.__instance

    def __init__(self, config):
        threading.Thread.__init__(self, daemon=True)

        self.config = config
        self.pyray = PyRay()

        # Value between 0.0 and 1.0 used to determine how far each car moves down
        # the screen on each iteration of the display loop. See __race_started() below.
        self.progress_threshold = 0.4

        # Initialize the dispatch table
        self.dispatch = {
            RaceState.WAIT_MENU: self.__wait_menu,
            RaceState.MENU_DONE: self.__menu_done,
            RaceState.WAIT_FINISH_LINE: self.__wait_finish_line,
            RaceState.WAIT_REMOTE_REGISTRATION: self.__wait_remote_registration,
            RaceState.REMOTE_REGISTRATION_DONE: self.__remote_registration_done,
            RaceState.WAIT_LOCAL_READY: self.__wait_local_ready,
            RaceState.WAIT_REMOTE_READY: self.__wait_remote_ready,
            RaceState.COUNTDOWN: self.__countdown,
            RaceState.RACE_STARTED: self.__race_started,
            RaceState.RACE_FINISHED: self.__race_finished,
            RaceState.RACE_TIMEOUT: self.__race_timeout
        }

        # Declare initial Y offset for car images at the start of a race
        self.y_starting_offset = 0
        self.local_y = [0, 0, 0, 0]
        self.remote_y = [0, 0, 0, 0]

        # Declare local texture variables. __load_textures() will load the appropriate
        # textures based on whether a single or multi track race is selected.
        self.background_texture = None

        self.local_textures = [None, None, None, None]
        self.remote_textures = [None, None, None, None]

        self.checkerboard_texture = None
        self.question_texture = None
        self.place_textures = []
        self.fail_texture = None

        self.countdown_start = None
        self.font = None
        self.menu = None
        self.results = None
        self.first_results_display = None

        self.menu_event = threading.Event()
        self.menu_event.clear()

        self.countdown_event = threading.Event()
        self.countdown_event.clear()

        self.remote_icons_loaded = False
        self.registration_event = threading.Event()
        self.registration_event.clear()

        self.state = RaceState.WAIT_MENU
        self.running = True
        self.start()

    def run(self):
        """
        Thread used for actual display updates

        Note, all pyray interactions must be done in this thread as it creates the GL context!
        """
        self.pyray.init_window(240, 240, b"Diecast Remote Raceway")
        self.pyray.set_target_fps(30)
        self.pyray.hide_cursor()

        self.font = self.pyray.load_font(b"fonts/Roboto-Black.ttf")
        self.menu = Menu(self.pyray, self.font, self.config)

        while self.running and not self.pyray.window_should_close():
            # Draw common background used for all displays
            self.pyray.begin_drawing()
            self.pyray.clear_background(RAYWHITE)

            if self.state != RaceState.WAIT_MENU:
                # A common background is displayed for all race states after leaving the
                # main menu.
                self.pyray.draw_texture(self.background_texture, 0, 0, WHITE)
                self.__draw_lanes()

            # Dispatch to appropriate drawing routine based on current race state
            self.dispatch[self.state]()
            self.pyray.end_drawing()

    def __reset_car_positions(self):
        for car in range(self.config.num_lanes):
            self.local_y[car] = self.y_starting_offset
        if self.config.multi_track:
            for car in range(self.config.remote_num_lanes):
                self.remote_y[car] = self.y_starting_offset

    def __text_box_dense(self, text, x, y, width, height, size):
        self.pyray.draw_rectangle_rec([x, y, width, height], WHITE)
        self.pyray.draw_text_rec(self.font, text, [x+2, y+2, width-2, height-2], size, 2,
                                 True, BLACK)

    def __text_box(self, text, x, y, width, height, size, inverted=False):
        """
        Draws a box at location (x,y) with width and height. Prints text with specified font size
        """
        self.pyray.draw_rectangle_lines(x, y, width, height, BLACK)
        if inverted:
            self.pyray.draw_rectangle_rec([x, y, width, height], GRAY)
            self.pyray.draw_text_rec(self.font, text,
                                     [x+10, y+2, width-10, height-2], size, 3.5, True, WHITE)
        else:
            self.pyray.draw_rectangle_rec([x, y, width, height], WHITE)
            self.pyray.draw_text_rec(self.font, text,
                                     [x+10, y+2, width-10, height-2], size, 3.5, True, BLACK)

    @staticmethod
    def __font_size(text):
        """
        Compute font size that will fit within text box based on length of text string
        """
        length = len(text)
        if length <= 14:
            return 34
        elif length < 30:
            return 26
        else:
            return 24

    def __text_message(self, text, inverted=False):
        if len(text) >= 16:
            # Two line text box
            self.__text_box(text, 10, 90, 215, 68, self.__font_size(text), inverted)
        else:
            # One line textbox
            self.__text_box(text, 10, 90, 215, 40, self.__font_size(text), inverted)


    def __draw_lanes(self):
        if self.config.multi_track:
            self.pyray.draw_text(self.config.track_name, 10, 10, 24, ORANGE)
            self.pyray.draw_text(self.config.remote_track_name, 130, 10, 24, BLACK)
            self.pyray.draw_line_ex([120, 5], [120, 235], 4.0, BLACK)

            self.pyray.draw_line_ex([35, 40], [35, 230], 34.0, ORANGE)
            self.pyray.draw_line_ex([80, 40], [80, 230], 34.0, ORANGE)

            self.pyray.draw_texture(self.checkerboard_texture, 18, 196, WHITE)
            self.pyray.draw_texture(self.checkerboard_texture, 63, 196, WHITE)

            self.pyray.draw_line_ex([155, 40], [155, 230], 34.0, ORANGE)
            self.pyray.draw_line_ex([200, 40], [200, 230], 34.0, ORANGE)

            self.pyray.draw_texture(self.checkerboard_texture, 138, 196, WHITE)
            self.pyray.draw_texture(self.checkerboard_texture, 183, 196, WHITE)
        else:
            self.pyray.draw_line_ex([64, 10], [64, 230], 64.0, ORANGE)
            self.pyray.draw_line_ex([164, 10], [164, 230], 64.0, ORANGE)

            self.pyray.draw_texture(self.checkerboard_texture, 32, 166, WHITE)
            self.pyray.draw_texture(self.checkerboard_texture, 132, 166, WHITE)

    def __draw_cars(self, texture1, texture2, texture3, texture4):
        #pylint: disable=bad-whitespace
        if self.config.multi_track:
            self.pyray.draw_texture(texture1,  22, self.local_y[CAR0],  WHITE)
            self.pyray.draw_texture(texture2,  68, self.local_y[CAR1],  WHITE)
            self.pyray.draw_texture(texture3, 142, self.remote_y[CAR0], WHITE)
            self.pyray.draw_texture(texture4, 188, self.remote_y[CAR1], WHITE)
        else:
            self.pyray.draw_texture(texture1,  40, self.local_y[CAR0],  WHITE)
            self.pyray.draw_texture(texture2, 140, self.local_y[CAR1],  WHITE)


    def __draw_result(self, track_count, track_number, lane_number, lane_time, place):
        """
        Draw result icon superimposed of appripriate track.

            track_count     1 if single track race, 2 if multi track race
            track_number    1 if local track, 2 if remote track
            lane_number     which lane in the track specified by track_number
            lane_time       elapsed time for the specified lane, or NOT_FINISHED
            place           1, 2, or 3 for First, Second or Third place
        """
        if self.first_results_display:
            print("__draw_result(", track_count, track_number, lane_number, lane_time, place, ")")

        if track_count == 1:
            x_offset = 15 + (lane_number - 1)*100
            y_offset = 20 + (place)*40
            time_y_offset = 180
            time_width = 96
        else:
            x_offset = 10 + (lane_number - 1)*48 + (track_number - 1)*120
            y_offset = 40 + (place)*50
            time_y_offset = 204
            time_width = 46

        texture = self.fail_texture if lane_time == NOT_FINISHED else self.place_textures[place]
        self.pyray.draw_texture(texture, x_offset, y_offset, WHITE)

        if lane_time == NOT_FINISHED:
            display_time = "FAIL"
        else:
            display_time = "{:.3f}".format(lane_time)
        if track_count == 1:
            self.__text_box(display_time, x_offset, time_y_offset, time_width, 30, 28)
        else:
            self.__text_box_dense(display_time, x_offset, time_y_offset, time_width, 20, 16)

    def __wait_menu(self):
        self.menu.process_menus()
        self.state = RaceState.MENU_DONE
        self.__load_textures()
        self.menu_event.set()

    def __menu_done(self):
        pass

    def __wait_finish_line(self):
        finish_line_name = self.config.finish_line_name
        self.__text_message("Connecting to " + finish_line_name)

    def __wait_remote_registration(self):
        self.__text_message("Waiting for: remote track")

    def __remote_registration_done(self):
        # Load car textures for remote track
        if self.remote_icons_loaded:
            return

        print("__remote_registration_done: remote_num_lanes=", self.config.remote_num_lanes)
        print("  remote_car_icons=", self.config.remote_car_icons)
        for car in range(self.config.remote_num_lanes):
            icon = self.config.remote_car_icons[car]
            self.local_y[car] = 40
            image = self.pyray.load_image("cars/{}-{}.png".format(icon, 24))
            self.remote_textures[car] = self.pyray.load_texture_from_image(image)
            self.pyray.unload_image(image)
        self.remote_icons_loaded = True
        self.registration_event.set()

    def __wait_local_ready(self):
        texture1 = self.local_textures[0] if car_1_present() else self.question_texture
        texture2 = self.local_textures[1] if car_2_present() else self.question_texture
        if self.config.multi_track:
            self.__draw_cars(texture1, texture2, self.question_texture, self.question_texture)
        else:
            self.__draw_cars(texture1, texture2, self.question_texture, self.question_texture)
        self.__text_message("Waiting for: Cars")

    def __wait_remote_ready(self):
        wait_msg = "Waiting for: " + self.config.remote_track_name
        self.__draw_cars(self.local_textures[CAR0], self.local_textures[CAR1],
                         self.question_texture, self.question_texture)
        self.__text_message(wait_msg)

    def __countdown(self):
        self.__draw_cars(self.local_textures[CAR0], self.local_textures[CAR1],
                         self.remote_textures[CAR0], self.remote_textures[CAR1])
        now = time.monotonic()
        if now - self.countdown_start > 3.0:
            self.countdown_event.set()
        elif now - self.countdown_start > 2.0:
            self.__text_message("Starting in 1")
        elif now - self.countdown_start > 1.0:
            self.__text_message("Starting in 2")
        else:
            self.__text_message("Starting in 3")

    def __race_started(self):
        delta = time.monotonic() - self.start
        delta_bytes = bytes('{:06.3f}'.format(delta), 'ascii')

        self.__draw_cars(self.local_textures[0],
                         self.local_textures[1],
                         self.remote_textures[0],
                         self.remote_textures[1])
        self.__text_box(delta_bytes, 26, 95, 180, 55, 50)
        for car in range(self.config.num_lanes):
            if random.random() < self.progress_threshold and self.local_y[car] < Display.MAX_Y:
                self.local_y[car] += 1
        for car in range(self.config.remote_num_lanes):
            if random.random() < self.progress_threshold and self.remote_y[car] < Display.MAX_Y:
                self.remote_y[car] += 1

    def __race_finished(self):
        # TODO: use IP address in results payload to determine own track vs other track to
        #       disambiguate in the event both tracks are set to the same name.
        if self.first_results_display:
            print("__race_finished(): results =", self.results)

        track_count = 2 if self.config.multi_track else 1
        place = 0
        for result in self.results:
            track_number = 1 if result["trackName"] == self.config.track_name else 2
            lane_number = result["laneNumber"]
            lane_time = result["laneTime"]
            self.__draw_result(track_count, track_number, lane_number, lane_time, place)
            place += 1
            if place > 2:
                break
        self.first_results_display = False

    def __race_timeout(self):
        self.__text_message("Race Timed Out")



def run_sample_race():
    """
    Run through the display operations for a sample race
    """

    main_config = Config("config/starting_gate.json")

    display = Display(main_config)
    print("main: calling wait_menu")
    display.wait_menu()
    time.sleep(1.0)
    print("main: calling wait_finish_line")
    display.wait_finish_line()
    time.sleep(1.0)

    if main_config.multi_track:
        print("main: calling wait_remote_registration")
        display.wait_remote_registration()
        time.sleep(2.0)
        main_config.remote_track_name = "Charlie"
        main_config.remote_num_lanes = 2
        main_config.remote_car_icons = ["white-sl", "mclaren-f1"]
        print("main: calling remote_registration_done")
        display.remote_registration_done()
        time.sleep(2)

    print("main: calling wait_local_ready")
    display.wait_local_ready()
    time.sleep(2.0)

    if main_config.multi_track:
        print("main: calling wait_remote_ready")
        display.wait_remote_ready()
        time.sleep(2.0)

    print("main: calling countdown")
    display.countdown()
    print("main: calling race started")
    display.race_started()
    time.sleep(2.0)

    if main_config.multi_track:
        test_results = [{"trackName":main_config.track_name, "laneNumber":2, "laneTime":1.234},
                        {"trackName":main_config.remote_track_name, "laneNumber":1,
                         "laneTime":1.541},
                        {"trackName":main_config.track_name, "laneNumber":1, "laneTime":2.130},
                        {"trackName":main_config.remote_track_name, "laneNumber":2,
                         "laneTime":NOT_FINISHED}]
        display.race_finished(test_results)
    else:
        test_results = [{"trackName":main_config.track_name, "laneNumber":2, "laneTime":1.234},
                        {"trackName":main_config.track_name, "laneNumber":1, "laneTime":2.087}]
        display.race_finished(test_results)

    display.join()

if __name__ == '__main__':
    run_sample_race()

# vim: expandtab: sw=4

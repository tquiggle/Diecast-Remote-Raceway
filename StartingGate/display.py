#! /usr/bin/python3

"""
Diecast Remote Raceway - Display

The Display module implements the race UI on the Waveshare 1.3 inch LCD HAT.

The race logic can manage one or two tracks, each with one to four lanes.  Given
the limited display space on the 1.3" display, at most 5 lanes are rendered.

For a single track race, all lanes are rendered.

For a two track race, all local lanes are always rendered. If the total number of
lanes across both tracks exceedes 5, the remote lanes beyond 5 will be "superimposed"
on the final lane.

Author: Tom Quiggle
tquiggle@gmail.com
https://github.com/tquiggle/Die-Cast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for full license information.

"""

import enum
import math
import random
import sys
import threading
import time

from pathlib import Path

import pyray
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE
from config import CAR1, CAR2, CAR3, CAR4, Config, NOT_FINISHED #pylint: disable=unused-import
from deviceio import car_present
from menu import Menu

@enum.unique
class RaceState(enum.IntEnum):
    """
    Enumerate the states a race goes through. Used to determine what to display.
    """

    WAIT_MENU = 0                # Waiting for top menu input: 1 track, 2 tracks or configure
    MENU_DONE = 1                # Menu selection made, waiting for next state
    WAIT_FINISH_LINE = 2         # Waiting for Bluetooth connection to the Finish Line
    WAIT_REMOTE_REGISTRATION = 3 #   " for remote track to register in our circuit
    RACE_CONFIGURATION_DONE  = 4 # Local and remote configuratin is complete. Finish initialization
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

    def race_configuration_done(self):
        """
        The coordinator completed the registration call and returned the remote car icons.
        Load the appropriate textures for the race display.
        """
        self.configuration_event.clear()
        self.configuration_loaded = False
        self.state = RaceState.RACE_CONFIGURATION_DONE
        self.configuration_event.wait()

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

    _MAX_Y = 150             # Maximum distance a car can travel in the race display
    _MAX_DISPLAY_LANES = 5   # Maximum number of lanes to display
    _MAX_LANES_PER_TRACK = 4 # Maximum possible number of lanes in a track

    __instance = None

    def __load_textures(self):
        """
        Load appropriate sized textures based on the number of tracks (and lanes)
        """

        print("__load_textures():")

        multi_track = self.config.multi_track

        self.y_starting_offset = 40 if multi_track else 10

        if self.display_lane_count > 3:
            banner_size = 48
            car_icon_size = 24
            checkerboard_size = 34
        else:
            banner_size = 96
            car_icon_size = 48
            checkerboard_size = 64

        self.checkerboard_size = checkerboard_size
        checkerboard_image = pyray.load_image(f"images/checkerboard-{checkerboard_size}.png")
        question_image = pyray.load_image(f"cars/question-{car_icon_size}.png")

        first_image = pyray.load_image(f"images/1st-{banner_size}.png")
        second_image = pyray.load_image(f"images/2nd-{banner_size}.png")
        third_image = pyray.load_image(f"images/3rd-{banner_size}.png")
        fail_image = pyray.load_image(f"images/fail-{banner_size}.png")

        self.banner_size = banner_size

        # Load textures into VRAM
        self.checkerboard_texture = pyray.load_texture_from_image(checkerboard_image)
        self.question_texture = pyray.load_texture_from_image(question_image)

        first_texture = pyray.load_texture_from_image(first_image)
        second_texture = pyray.load_texture_from_image(second_image)
        third_texture = pyray.load_texture_from_image(third_image)
        self.fail_texture = pyray.load_texture_from_image(fail_image)

        self.place_textures = [first_texture, second_texture, third_texture]

        car_index = 0
        # Load car textures for local track
        print(f"__load_textures(): num_lanes={self.config.num_lanes}")
        for car in range(self.config.num_lanes):
            icon = self.config.car_icons[car]
            print(f"loading image[{car_index}]: cars/{icon}-{car_icon_size}.png")
            image = pyray.load_image(f"cars/{icon}-{car_icon_size}.png")
            self.car_textures[car_index] = pyray.load_texture_from_image(image)
            pyray.unload_image(image)
            car_index += 1

        if multi_track:
            # Load car textures for remote track
            print(f"__load_textures(): remote_num_lanes={self.config.remote_num_lanes}")
            for car in range(self.config.remote_num_lanes):
                icon = self.config.remote_car_icons[car]
                filename = f"cars/{icon}-{car_icon_size}.png"
                if not Path(filename).is_file():
                    # Remote track has icons we dont.  Substitute a random car image
                    # that exists locally
                    print(f"Car icon file {filename} not found locally. Substituting")
                    filename = self.__get_random_car_image(car_icon_size)

                print(f"loading image[{car}]: {filename}")
                image = pyray.load_image(filename)
                self.car_textures[car_index] = pyray.load_texture_from_image(image)
                pyray.unload_image(image)
                car_index += 1

        # Unload image data from CPU memory
        pyray.unload_image(checkerboard_image)
        pyray.unload_image(question_image)
        pyray.unload_image(first_image)
        pyray.unload_image(second_image)
        pyray.unload_image(third_image)
        pyray.unload_image(fail_image)

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

        # Value between 0.0 and 1.0 used to determine how far each car moves down
        # the screen on each iteration of the display loop. See __race_started() below.
        self.progress_threshold = 0.4

        # Initialize the dispatch table
        self.dispatch = {
            RaceState.WAIT_MENU: self.__wait_menu,
            RaceState.MENU_DONE: self.__menu_done,
            RaceState.WAIT_FINISH_LINE: self.__wait_finish_line,
            RaceState.WAIT_REMOTE_REGISTRATION: self.__wait_remote_registration,
            RaceState.RACE_CONFIGURATION_DONE: self.__race_configuration_done,
            RaceState.WAIT_LOCAL_READY: self.__wait_local_ready,
            RaceState.WAIT_REMOTE_READY: self.__wait_remote_ready,
            RaceState.COUNTDOWN: self.__countdown,
            RaceState.RACE_STARTED: self.__race_started,
            RaceState.RACE_FINISHED: self.__race_finished,
            RaceState.RACE_TIMEOUT: self.__race_timeout
        }

        # Intialize lane counts
        self.local_lane_count = self.config.num_lanes
        self.remote_lane_count = self.config.remote_num_lanes
        self.total_lane_count = self.local_lane_count + self.remote_lane_count
        self.display_lane_count = min(self.total_lane_count, Display._MAX_DISPLAY_LANES)

        # Declare initial Y offset for car images at the start of a race
        self.y_starting_offset = 0
        self.car_y_position = [0] * (Display._MAX_LANES_PER_TRACK * 2)
        self.car_x_position = [0] * (Display._MAX_LANES_PER_TRACK * 2)
        self.track_separator_x_offset = 0
        self.remote_name_width = 0

        # Initialize textures
        self.background_texture = None
        self.car_textures = [None] * (Display._MAX_LANES_PER_TRACK * 2)
        self.checkerboard_texture = None
        self.question_texture = None
        self.place_textures = []
        self.fail_texture = None

        self.lane_dimensions = []
        self.lane_width = 0
        self.banner_size = 0
        self.checkerboard_size = 0

        self.countdown_start = None
        self.last_debug_print = 0.0
        self.font = None
        self.menu = None
        self.results = None
        self.first_results_display = None

        self.menu_event = threading.Event()
        self.menu_event.clear()

        self.countdown_event = threading.Event()
        self.countdown_event.clear()

        self.configuration_loaded = False
        self.configuration_event = threading.Event()
        self.configuration_event.clear()

        self.state = RaceState.WAIT_MENU
        self.running = True
        self.start()

    def run(self):
        """
        Thread used for actual display updates

        Note, all pyray interactions must be done in this thread as it creates the GL context!
        """
        pyray.init_window(240, 240, "Diecast Remote Raceway")
        pyray.set_target_fps(30)
        pyray.hide_cursor()

        self.font = pyray.load_font("fonts/Roboto-Black.ttf")
        self.menu = Menu(self.font, self.config)

        # Load the background image
        background_image = pyray.load_image("images/raceoff-2.png")
        self.background_texture = pyray.load_texture_from_image(background_image)
        pyray.unload_image(background_image)

        while self.running and not pyray.window_should_close():
            # Draw common background used for all displays
            pyray.begin_drawing()
            pyray.clear_background(RAYWHITE)
            pyray.draw_texture(self.background_texture, 0, 0, WHITE)

            if self.state > RaceState.RACE_CONFIGURATION_DONE:
                # A common background is displayed for all race states after leaving the
                # main menu.
                self.__draw_lanes()

            # Dispatch to appropriate drawing routine based on current race state
            self.dispatch[self.state]()
            pyray.end_drawing()

    def __reset_car_positions(self):
        for car in range(self.total_lane_count):
            self.car_y_position[car] = self.y_starting_offset

    def __text_box_dense(self, text, x, y, width, height, size):
        pyray.draw_rectangle_rec([x, y, width, height], WHITE)
        pyray.draw_text_ex(self.font, text, [x+2, y+2], size, 1.0, BLACK)

    def __text_box(self, text, x, y, width, height, size, inverted=False):
        """
        Draws a box at location (x,y) with width and height. Prints text with specified font size
        """
        pyray.draw_rectangle_lines(x, y, width, height, BLACK)
        if inverted:
            pyray.draw_rectangle_rec([x, y, width, height], GRAY)
            pyray.draw_text_ex(self.font, text, [x+10, y+2], size, 1.0, WHITE)
        else:
            pyray.draw_rectangle_rec([x, y, width, height], WHITE)
            pyray.draw_text_ex(self.font, text, [x+10, y+2], size, 1.0, BLACK)


    @staticmethod
    def __font_size(text):
        """
        Compute font size that will fit within text box based on length of text string
        """
        length = len(text)
        if length <= 14:
            return 34
        if length < 30:
            return 26
        return 24

    def draw_dashed_line(self, start_pos, end_pos, dash_size, space_size, color):
        """
        Draw dashed line from start_pos to end_pos

        When upgrading to raylib 6, this will no longer be needed. Replace with
        a call to pyray.draw_line_dashed(...)
        """
        x1, y1 = start_pos
        x2, y2 = end_pos
        dx = x2 - x1
        dy = y2 - y1
        line_length = math.hypot(dx, dy)

        if line_length < (dash_size + space_size) or dash_size <= 0:
            pyray.draw_line(int(x1), int(y1), int(x2), int(y2), color)
            return

        dir_x = dx / line_length
        dir_y = dy / line_length
        distance_traveled = 0.0
        drawing_dash = True

        current_x, current_y = x1, y1
        while distance_traveled < line_length:
            segment_len = dash_size if drawing_dash else space_size
            remaining = line_length - distance_traveled
            segment_len = min(segment_len, remaining)

            next_x = current_x + dir_x * segment_len
            next_y = current_y + dir_y * segment_len

            if drawing_dash:
                pyray.draw_line(int(current_x), int(current_y), int(next_x), int(next_y), color)

            distance_traveled += segment_len
            current_x, current_y = next_x, next_y
            drawing_dash = not drawing_dash

    def __text_message(self, text, inverted=False):
        lines = self.menu.break_string(text, 18)
        num_lines = len(lines)
        wrapped_text = "\n".join(lines)
        self.__text_box(wrapped_text, 10, 90, 215, 40*num_lines,
                        self.__font_size(text), inverted)

    def __draw_lane(self, start, end, texture):
        pyray.draw_line_ex(start, end, self.lane_width, ORANGE)
        pyray.draw_texture_v(self.checkerboard_texture, texture, WHITE)

    def __draw_lanes(self):
        if self.config.multi_track:
            pyray.draw_text(self.config.track_name, 10, 10, 24, ORANGE)
            pyray.draw_text(self.config.remote_track_name,
                            230 - self.remote_name_width, 10, 24, BLACK)

        for lane in range(self.display_lane_count):
            triple = self.lane_dimensions[lane]
            self.__draw_lane(triple[0], triple[1], triple[2])
            if self.config.multi_track and lane == self.local_lane_count:
                pyray.draw_line_ex([self.track_separator_x_offset, 35],
                                   [self.track_separator_x_offset, 235], 4.0, BLACK)

        # If the total number of lanes exceeds the number that can be displayed,
        # the last displayed lane represental all remaining lanes.  Draw a dashed
        # line down the middle of the lane to indicate it represents multiple lanes
        if self.total_lane_count > self.display_lane_count:
            triple = self.lane_dimensions[self.display_lane_count-1]
            end_pos = [triple[1][0], triple[1][1]]
            end_pos[1] -= self.checkerboard_size
            self.draw_dashed_line(triple[0], end_pos, 8, 2, BLACK)

    def __draw_cars(self, missing=None):
        for lane in range(self.display_lane_count):
            texture = (self.question_texture if (missing and missing[lane])
                       else self.car_textures[lane])

            if missing and missing[lane]:
                texture = self.question_texture
            else:
                texture = self.car_textures[lane]

            pyray.draw_texture(texture,
                               self.car_x_position[lane],
                               self.car_y_position[lane],
                               WHITE)

    def __draw_result(self, lane_number, lane_time, place):
        """
        Draw result icon superimposed of appripriate track.
            lane_number     number of winning lane (0 based)
            lane_time       elapsed time for the specified lane, or NOT_FINISHED
            place           1, 2, or 3 for First, Second or Third place
        """

        if self.first_results_display:
            print(f"__draw_result({lane_number}, {lane_time}, {place})")

        lane_index = min(lane_number, self.display_lane_count)

        if self.display_lane_count > 3:
            time_y_offset = 204
            time_width = 40
            banner_y_offset = 42
        else:
            time_y_offset = 190
            time_width = 74
            banner_y_offset = 60

        y_offset = self.y_starting_offset + (place * banner_y_offset)

        triple = self.lane_dimensions[lane_index]
        x_offset = triple[0][0] - int(self.banner_size/2)
        texture = self.fail_texture if lane_time == NOT_FINISHED else self.place_textures[place]
        pyray.draw_texture(texture, x_offset, y_offset, WHITE)

        display_time = "FAIL" if lane_time == NOT_FINISHED else "{:.3f}".format(lane_time)

        x_offset = triple[0][0] - int(time_width/2)
        if self.display_lane_count > 3:
            self.__text_box_dense(display_time, x_offset, time_y_offset, time_width, 20, 16)
        else:
            self.__text_box(display_time, x_offset, time_y_offset, time_width, 30, 24)

    def __wait_menu(self):
        self.menu.process_menus()
        self.state = RaceState.MENU_DONE
        #self.__load_textures()
        self.menu_event.set()

    def __menu_done(self):
        pass

    def __wait_finish_line(self):
        finish_line_name = self.config.finish_line_name
        self.__text_message("Connecting to " + finish_line_name)

    def __wait_remote_registration(self):
        self.__text_message("Waiting for: remote track")

    def __race_configuration_done(self):
        if self.configuration_loaded:
            return
        print("__race_configuration_done: remote_num_lanes=", self.config.remote_num_lanes)
        print("  car_icons=", self.config.car_icons)
        print("  remote_car_icons=", self.config.remote_car_icons)

        self.remote_lane_count = self.config.remote_num_lanes
        self.total_lane_count = self.local_lane_count + self.remote_lane_count
        self.display_lane_count = min(self.total_lane_count, Display._MAX_DISPLAY_LANES)
        self.remote_name_width = pyray.measure_text(self.config.remote_track_name, 24)

        self.lane_dimensions = self.__gen_lane_dimensions(self.local_lane_count,
                                                          self.remote_lane_count)
        self.__load_textures()

        self.configuration_event.set()
        self.configuration_loaded = True

    def __wait_local_ready(self):
        missing = [True] * self.total_lane_count
        for index in range(self.local_lane_count):
            missing[index] = not car_present(index)

        self.__draw_cars(missing)
        self.__text_message("Waiting for: Cars")

    def __wait_remote_ready(self):
        missing = [False] * self.total_lane_count
        for index in range(self.local_lane_count, self.total_lane_count):
            missing[index] = True

        self.__draw_cars(missing)
        self.__text_message(f"Waiting for: {self.config.remote_track_name}")

    def __countdown(self):
        self.__draw_cars()
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

        self.__draw_cars()
        self.__text_box(delta_bytes, 26, 95, 180, 55, 50)
        car_index = 0

        for __ in range(self.config.num_lanes):
            if (random.random() < self.progress_threshold and \
                self.car_y_position[car_index] < Display._MAX_Y):
                self.car_y_position[car_index] += 1
            car_index += 1

        for __ in range(self.config.remote_num_lanes):
            if (random.random() < self.progress_threshold and \
                self.car_y_position[car_index] < Display._MAX_Y):
                self.car_y_position[car_index] += 1
            car_index += 1

    def __race_finished(self):
        # TODO: use IP address in results payload to determine own track vs other track to
        #       disambiguate in the event both tracks are set to the same name.
        if self.first_results_display:
            print(f"__race_finished(): results = {self.results}")

        place = 0
        for result in self.results:
            if result["trackName"] == self.config.track_name:
                track_offset = 0
            else:
                track_offset = self.local_lane_count
            lane_number = result["laneNumber"] + track_offset
            lane_time = result["laneTime"]
            self.__draw_result(lane_number, lane_time, place)
            place += 1
            if place > 2:
                break

        self.first_results_display = False

    def __race_timeout(self):
        self.__text_message("Race Timed Out")

    def __get_random_car_image(self, icon_size):
        dir_path = Path("cars")
        matching_files = [ p.name for p in dir_path.glob(f"*-{icon_size}.png") ]
        while len(matching_files):
            random_car = random.choice(matching_files)
            if not "question" in random_car:
                break
        return f"cars/{random_car}"

    def __gen_lane_dimensions(self, local_lane_count, remote_lane_count):
        """
        Generate the array of

           [ [start_x, end_x], [start_y, end_y], [checkerboard_x, checkerboard_y] ]

        boundaries for each lane to be displayed.

        Lanes are evenly spaced across the display. For Multi-Track races,
        the spacing between the last lane of the local track and the first
        lane of the remote track is doubled to draw a line separator.

        To avoid lanes too small to draw/see, the display is limited to
        at most _MAX_DISPLAY_LANES lanes.  If the total number of lanes)
        across both tracks exceedes this limit, remote lanes are combined
        into a single "highway" lane for display purposes.
        """

        print(f"__gen_lane_dimensions({local_lane_count}, {remote_lane_count})")

        result = []

        total_lane_count = local_lane_count + remote_lane_count
        draw_lane_count  = min(total_lane_count, Display._MAX_DISPLAY_LANES)

        lane_width = 64 if draw_lane_count <= 3 else 32
        car_x_offset = 24 if draw_lane_count <= 3 else 12
        end_y = 230

        self.lane_width = lane_width
        self.display_lane_count = draw_lane_count

        if remote_lane_count == 0:
            spacing = int((240-lane_width*draw_lane_count)/(draw_lane_count+1))
            start_y = 10
        else:
            spacing = int((240-lane_width*draw_lane_count)/(draw_lane_count+2))
            start_y = 35

        print(f"__gen_lane_dimensions(): lane_width:{lane_width} "
              f"draw_lane_count:{draw_lane_count} spacing:{spacing}")

        start_x = end_x = spacing + int(lane_width/2)
        for lane in range(local_lane_count):
            print(f"__gen_lane_dimensions():local lane={lane}")
            checkerboard_x = end_x - int(lane_width/2)
            checkerboard_y = end_y - lane_width
            tup = [[start_x, start_y], [end_x, end_y], [checkerboard_x, checkerboard_y]]
            result.append(tup)
            self.car_x_position[lane] = start_x - car_x_offset
            start_x = end_x = start_x + lane_width + spacing

        if remote_lane_count > 0:
            self.track_separator_x_offset = start_x - lane_width/2
            start_x = end_x = start_x + spacing

        for lane in range (local_lane_count, draw_lane_count):
            print(f"__gen_lane_dimensions():remote lane={lane}")
            checkerboard_x = end_x - int(lane_width/2)
            checkerboard_y = end_y - lane_width
            tup = [[start_x, start_y], [end_x, end_y], [checkerboard_x, checkerboard_y]]
            result.append(tup)
            self.car_x_position[lane] = start_x - car_x_offset
            start_x = end_x = start_x + lane_width + spacing

        print(f"__gen_lane_dimensions: {result}")
        return result


def run_sample_race(local_lane_count, remote_lane_count):
    """
    Run through the display operations for a sample race with the specified
    number of local and remote lanes
    """

    main_config = Config("config/starting_gate.json")
    main_config.allow_multi_track = remote_lane_count > 0
    main_config.num_lanes = local_lane_count
    main_config.track_name = "Gramps"

    if remote_lane_count:
        main_config.multi_track = True
        main_config.remote_num_lanes = remote_lane_count
        main_config.remote_track_name = "Charlie"
        main_config.remote_car_icons = ["NOT_THERE", "mclaren-f1", "minivan", "jeep"]

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
    else:
        # override command line remote count if single lane race was selected
        main_config.remote_num_lanes = 0

    print("main: calling configuration_done")
    display.race_configuration_done()

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

    # Generate random race results
    results = []
    lanes = []  # list of lanes that have not been selected as finishing in top n
    for lane in range(display.total_lane_count):
        lanes.append(lane)

    print(f"lanes={lanes}")

    last_lane_time = 0.0
    for __ in range (min(display.total_lane_count, 3)):
        lane_time = random.uniform(last_lane_time, last_lane_time + 2.0)
        lane = random.choice(lanes)
        lanes.remove(lane)

        if lane < display.local_lane_count:
            track_name = main_config.track_name
        else:
            track_name = main_config.remote_track_name
            lane = lane - display.local_lane_count

        result = {"trackName":track_name, "laneNumber":lane, "laneTime":lane_time}
        results.append(result)
        last_lane_time = lane_time

    display.race_finished(results)

    display.join()

if __name__ == '__main__':
    local = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    remote = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    run_sample_race(local, remote)

# vim: expandtab: sw=4

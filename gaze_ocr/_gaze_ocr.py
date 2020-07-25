"""Library for manipulating on-screen text using gaze tracking and OCR."""

import os.path
import time
from concurrent import futures

import dragonfly

from . import _dragonfly_wrappers as dragonfly_wrappers


class Controller(object):
    """Mediates interaction with gaze tracking and OCR."""

    def __init__(self,
                 ocr_reader,
                 eye_tracker,
                 save_data_directory=None,
                 mouse=dragonfly_wrappers.Mouse()):
        self.ocr_reader = ocr_reader
        self.eye_tracker = eye_tracker
        self.save_data_directory = save_data_directory
        self.mouse = mouse
        self._executor = futures.ThreadPoolExecutor(max_workers=1)
        self._future = None

    def start_reading_nearby(self):
        """Start OCR nearby the gaze point in a background thread."""
        gaze_point = self.eye_tracker.get_gaze_point_or_default()
        # Don't enqueue multiple requests.
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self._executor.submit(lambda: self.ocr_reader.read_nearby(gaze_point))

    def latest_screen_contents(self):
        """Return the ScreenContents of the latest call to start_reading_nearby().

        Blocks until available.
        """
        if not self._future:
            raise RuntimeError("Call start_reading_nearby() before latest_screen_contents()")
        return self._future.result()

    def move_cursor_to_word(self, word, cursor_position="middle"):
        """Move the mouse cursor nearby the specified word.

        Arguments:
        word: The word to search for.
        cursor_position: "before", "middle", or "after" (relative to the matching word)
        """
        screen_contents = self.latest_screen_contents()
        coordinates = screen_contents.find_nearest_word_coordinates(word, cursor_position)
        self._write_data(screen_contents, word, coordinates)
        if coordinates:
            self.mouse.move(coordinates)
            return True
        else:
            return False

    def select_text(self, start_word, end_word=None):
        """Select a range of onscreen text.

        If only start_word is provided, it can be a word or phrase to select. If
        end_word is provided, a range from the start word to end word will be
        selected.
        """
        # Automatically split up start word if multiple words are provided.
        if " " in start_word and not end_word:
            words = start_word.split()
            start_word = words[0]
            end_word = words[-1]
        if not self.move_cursor_to_word(start_word, "before"):
            return False
        if end_word:
            # If gaze has significantly moved, look for the end word at the final gaze coordinates.
            current_gaze_point = self.eye_tracker.get_gaze_point_or_default()
            previous_gaze_point = self.latest_screen_contents().screen_coordinates
            if (_distance_squared(current_gaze_point, previous_gaze_point)
                > _squared(self.ocr_reader.radius / 2.0)):
                self.start_reading_nearby()
        else:
            end_word = start_word
        screen_contents = self.latest_screen_contents()
        end_coordinates = screen_contents.find_nearest_word_coordinates(end_word, "after")
        self._write_data(screen_contents, end_word, end_coordinates)
        if not end_coordinates:
            return False
        self.mouse.click_down()
        self.mouse.move(end_coordinates)
        time.sleep(0.1)
        self.mouse.click_up()
        return True

    def move_cursor_to_word_action(self, word, cursor_position="middle"):
        """Return a Dragonfly action for moving the cursor nearby a word."""
        outer = self
        class MoveCursorToWordAction(dragonfly.ActionBase):
            def _execute(self, data=None):
                dynamic_word = word
                if data:
                    dynamic_word = word % data
                return outer.move_cursor_to_word(dynamic_word, cursor_position)
        return MoveCursorToWordAction()

    def select_text_action(self, start_word, end_word=None):
        """Return a Dragonfly action for selecting text."""
        outer = self
        class SelectTextAction(dragonfly.ActionBase):
            def _execute(self, data=None):
                dynamic_start_word = start_word
                dynamic_end_word = end_word
                if data:
                    dynamic_start_word = start_word % data
                    if end_word:
                        try:
                            dynamic_end_word = end_word % data
                        except KeyError:
                            dynamic_end_word = None
                return outer.select_text(dynamic_start_word, dynamic_end_word)
        return SelectTextAction()

    def _write_data(self, screen_contents, word, coordinates):
        if not self.save_data_directory:
            return
        file_name_prefix = "{}_{:.2f}".format("success" if coordinates else "failure", time.time())
        file_path_prefix = os.path.join(self.save_data_directory, file_name_prefix)
        screen_contents.screenshot.save(file_path_prefix + ".png")
        with open(file_path_prefix + ".txt", "w") as file:
            file.write(word)


def _squared(x):
    return x * x


def _distance_squared(coordinate1, coordinate2):
    return (_squared(coordinate1[0] - coordinate2[0])
            + _squared(coordinate1[1] - coordinate2[1]))

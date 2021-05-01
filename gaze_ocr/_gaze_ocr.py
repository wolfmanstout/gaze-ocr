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
                 mouse=dragonfly_wrappers.Mouse(),
                 keyboard=dragonfly_wrappers.Keyboard()):
        self.ocr_reader = ocr_reader
        self.eye_tracker = eye_tracker
        self.save_data_directory = save_data_directory
        self.mouse = mouse
        self.keyboard = keyboard
        self._executor = futures.ThreadPoolExecutor(max_workers=1)
        self._future = None

    def shutdown(self, wait=True):
        self._executor.shutdown(wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        return False

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

        If successful, returns the new cursor coordinates.

        Arguments:
        word: The word to search for.
        cursor_position: "before", "middle", or "after" (relative to the matching word)
        """
        screen_contents = self.latest_screen_contents()
        coordinates = screen_contents.find_nearest_word_coordinates(word, cursor_position)
        self._write_data(screen_contents, word, coordinates)
        if coordinates:
            self.mouse.move(coordinates)
            return coordinates
        else:
            return False

    def move_text_cursor_to_word(self, word, cursor_position="middle", use_nearest=True,
                                 validate_location_function=None, include_whitespace=False):
        """Move the text cursor nearby the specified word or phrase.

        If successful, returns the screen_ocr.WordLocation of the matching word.

        Arguments:
        word: The word or phrase to search for.
        cursor_position: "before", "middle", or "after" (relative to the matching word).
        use_nearest: Minimizes cursor movement for subword placement, instead of always
                     clicking based on cursor_position.
        validate_location_function: Given a word location, return whether to proceed with
                                    cursor movement.
        """
        if " " in word:
            split = word.split()
            if cursor_position == "before":
                word = split[0]
            elif cursor_position == "after":
                word = split[-1]
            elif cursor_position == "middle":
                raise ValueError("Unable to place the cursor in the middle of multiple words")
        screen_contents = self.latest_screen_contents()
        word_location = screen_contents.find_nearest_word(word)
        self._write_data(screen_contents, word, word_location)
        if (not word_location or
            (validate_location_function and not validate_location_function(word_location))):
            return False
        if cursor_position == "before":
            if (not use_nearest
                or word_location.left_char_offset
                <= word_location.right_char_offset + len(word_location.text)):
                self.mouse.move(word_location.start_coordinates)
                self.mouse.click()
                if word_location.left_char_offset:
                    self.keyboard.right(word_location.left_char_offset)
            else:
                self.mouse.move(word_location.end_coordinates)
                self.mouse.click()
                offset = word_location.right_char_offset + len(word_location.text)
                if offset:
                    self.keyboard.left(offset)
            if not word_location.left_char_offset and include_whitespace:
                # Assume that there is whitespace adjacent to the word. This
                # will gracefully fail if the word is the first in the
                # editable text area.
                self.keyboard.left(1)
        elif cursor_position == "middle":
            # Note: if it's helpful, we could change this to position the cursor
            # in the middle of the word.
            self.mouse.move(word_location.middle_coordinates)
            self.mouse.click()
        if cursor_position == "after":
            if (not use_nearest
                or word_location.right_char_offset
                <= word_location.left_char_offset + len(word_location.text)):
                self.mouse.move(word_location.end_coordinates)
                self.mouse.click()
                if word_location.right_char_offset:
                    self.keyboard.left(word_location.right_char_offset)
            else:
                self.mouse.move(word_location.start_coordinates)
                self.mouse.click()
                offset = word_location.left_char_offset + len(word_location.text)
                if offset:
                    self.keyboard.right(offset)
            if not word_location.right_char_offset and include_whitespace:
                # Assume that there is whitespace adjacent to the word. This
                # will gracefully fail if the word is the last in the
                # editable text area.
                self.keyboard.right(1)
        return word_location

    def select_text(self, start_word, end_word=None, for_deletion=False):
        """Select a range of onscreen text.

        If only start_word is provided, it can be a word or phrase to select. If
        end_word is provided, a range from the start word to end word will be
        selected.

        Arguments:
        for_deletion: If True, select adjacent whitespace for clean deletion of
                      the selected text.
        """
        # Automatically split up start word if multiple words are provided.
        if " " in start_word and not end_word:
            words = start_word.split()
            start_word = words[0]
            end_word = words[-1]
        # Always click before the word to avoid subword selection issues on Windows.
        start_location = self.move_text_cursor_to_word(start_word,
                                                       "before",
                                                       use_nearest=False,
                                                       include_whitespace=for_deletion)
        if not start_location:
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
        self.keyboard.shift_down()
        validate_function = lambda location: self._is_valid_selection(start_location.start_coordinates,
                                                                      location.end_coordinates)
        include_whitespace = for_deletion and start_location.left_char_offset
        # Always click after the word to avoid subword selection issues on Windows.
        end_location = self.move_text_cursor_to_word(
            end_word, "after", use_nearest=False,
            validate_location_function=validate_function,
            include_whitespace=include_whitespace)
        self.keyboard.shift_up()
        return end_location

    def move_cursor_to_word_action(self, word, cursor_position="middle"):
        """Return a Dragonfly action for moving the mouse cursor nearby a word."""
        outer = self
        class MoveCursorToWordAction(dragonfly.ActionBase):
            def _execute(self, data=None):
                dynamic_word = word
                if data:
                    dynamic_word = word % data
                return outer.move_cursor_to_word(dynamic_word, cursor_position)
        return MoveCursorToWordAction()

    def move_text_cursor_action(self, word, cursor_position="middle"):
        """Return a dragonfly action for moving the text cursor nearby a word."""
        outer = self
        class MoveTextCursorAction(dragonfly.ActionBase):
            def _execute(self, data=None):
                dynamic_word = word
                if data:
                    dynamic_word = word % data
                return outer.move_text_cursor_to_word(dynamic_word, cursor_position)
        return MoveTextCursorAction()

    def select_text_action(self, start_word, end_word=None, for_deletion=False):
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
                return outer.select_text(dynamic_start_word, dynamic_end_word, for_deletion=for_deletion)
        return SelectTextAction()

    def _write_data(self, screen_contents, word, word_location):
        if not self.save_data_directory:
            return
        file_name_prefix = "{}_{:.2f}".format("success" if word_location else "failure", time.time())
        file_path_prefix = os.path.join(self.save_data_directory, file_name_prefix)
        screen_contents.screenshot.save(file_path_prefix + ".png")
        with open(file_path_prefix + ".txt", "w") as file:
            file.write(word)

    def _is_valid_selection(self, start_coordinates, end_coordinates):
        epsilon = 5  # pixels
        (start_x, start_y) = start_coordinates
        (end_x, end_y) = end_coordinates
        # Selection goes to previous line.
        if end_y - start_y < -epsilon:
            return False
        # Selection stays on same line.
        elif end_y - start_y < epsilon:
            return end_x > start_x
        # Selection moves to following line.
        else:
            return True


def _squared(x):
    return x * x


def _distance_squared(coordinate1, coordinate2):
    return (_squared(coordinate1[0] - coordinate2[0])
            + _squared(coordinate1[1] - coordinate2[1]))

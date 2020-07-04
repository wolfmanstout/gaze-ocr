import time
from concurrent import futures

import dragonfly
import screen_ocr

from . import _dragonfly_wrappers as dragonfly_wrappers


class Controller(object):
    def __init__(self,
                 ocr_reader,
                 eye_tracker,
                 mouse=dragonfly_wrappers.Mouse()):
        self._ocr_reader = ocr_reader
        self._eye_tracker = eye_tracker
        self._mouse = mouse
        self._executor = futures.ThreadPoolExecutor(max_workers=1)
        self._future = None

    def start_reading_nearby(self):
        gaze_point = self._eye_tracker.get_gaze_point_or_default()
        # Don't enqueue multiple requests.
        if self._future and not self._future.done():
            self._future.cancel()
        self._future = self._executor.submit(lambda: self._ocr_reader.read_nearby(gaze_point))

    def find_nearest_word_coordinates(self, word, cursor_position=screen_ocr.CursorPosition.MIDDLE):
        if not self._future:
            raise RuntimeError("Call start_reading_nearby() before find_nearest_word_coordinates()")
        screen_contents = self._future.result()
        return screen_contents.find_nearest_word_coordinates(word, cursor_position)

    def move_cursor_to_word(self, word, cursor_position=screen_ocr.CursorPosition.MIDDLE):
        coordinates = self.find_nearest_word_coordinates(word, cursor_position)
        if coordinates:
            self._mouse.move(coordinates)
            # TODO Save data for OCR
            return True
        else:
            return False

    def select_text(self, start_word, end_word=None):
        if not self.move_cursor_to_word(start_word, screen_ocr.CursorPosition.BEFORE):
            return False
        self._mouse.click_down()
        if not end_word:
            end_word = start_word
        if not self.move_cursor_to_word(end_word, screen_ocr.CursorPosition.AFTER):
            return False
        time.sleep(0.05)
        self._mouse.click_up()
        return True

    def move_cursor_to_word_action(self, word, cursor_position=screen_ocr.CursorPosition.MIDDLE):
        outer = self
        class MoveCursorToWordAction(dragonfly.ActionBase):
            def _execute(self, data=None):
                dynamic_word = word
                if data:
                    dynamic_word = word % data
                return outer.move_cursor_to_word(dynamic_word, cursor_position)
        return MoveCursorToWordAction()

    def select_text_action(self, start_word, end_word=None):
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

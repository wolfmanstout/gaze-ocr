"""Tests for move_text_cursor_to_difference_generator."""

from typing import cast

import screen_ocr
from screen_ocr import _base

from gaze_ocr._gaze_ocr import Controller


class FakeMouse:
    def move(self, coordinates):
        pass

    def click(self):
        pass


class FakeKeyboard:
    def shift_down(self):
        pass

    def shift_up(self):
        pass

    def is_shift_down(self):
        return False

    def left(self, n=1):
        pass

    def right(self, n=1):
        pass


class FakeReader:
    """Reader that returns a fixed line of words."""

    def __init__(self, words: list[str]):
        self._words = words

    def read_screen(self, bounding_box=None):
        ocr_words = []
        left = 100
        for text in self._words:
            ocr_words.append(
                _base.OcrWord(text, left=left, top=10, width=50, height=10)
            )
            left += 60
        return screen_ocr.ScreenContents(
            screen_coordinates=(0, 0),
            bounding_box=(0, 0, 500, 100),
            screenshot=None,
            result=_base.OcrResult(lines=[_base.OcrLine(ocr_words)]),
            confidence_threshold=0.75,
            homophones={},
            search_radius=None,
        )


def _make_controller(onscreen_words: list[str]) -> Controller:
    controller = Controller(
        ocr_reader=cast(screen_ocr.Reader, FakeReader(onscreen_words)),
        eye_tracker=None,
        mouse=FakeMouse(),
        keyboard=FakeKeyboard(),
    )
    controller.start_reading_nearby()
    return controller


def _run_to_completion(generator):
    try:
        next(generator)
    except StopIteration as e:
        return e.value
    raise AssertionError("Generator unexpectedly yielded for disambiguation")


def test_difference_inserts_between_adjacent_prefix_and_suffix():
    controller = _make_controller(["alpha", "gamma"])
    generator = controller.move_text_cursor_to_difference_generator(
        "alpha beta gamma", disambiguate=False
    )
    # The difference is the middle text, with its leading space dropped because
    # whitespace already separates the onscreen matches.
    assert _run_to_completion(generator) == (5, 10)


def test_difference_with_overlapping_prefix_and_suffix_does_not_crash():
    # The whole utterance matches onscreen as both prefix and suffix, and the two
    # occurrences are adjacent. There is no middle text to insert, so the adjacent
    # pair must be ignored (previously raised IndexError).
    controller = _make_controller(["hello", "hello"])
    generator = controller.move_text_cursor_to_difference_generator(
        "hello", disambiguate=False
    )
    assert _run_to_completion(generator) == (0, 0)

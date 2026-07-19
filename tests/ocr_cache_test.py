"""Tests for OCR cache behavior."""

import logging
from typing import cast

import screen_ocr
from screen_ocr import _base

from gaze_ocr import _gaze_ocr
from gaze_ocr._gaze_ocr import Controller, EyeTrackerFallback, OcrCache


def _contents(
    bounding_box: tuple[int, int, int, int], words: list[_base.OcrWord] | None = None
) -> screen_ocr.ScreenContents:
    return screen_ocr.ScreenContents(
        screen_coordinates=None,
        bounding_box=bounding_box,
        screenshot=None,
        result=_base.OcrResult(lines=[_base.OcrLine(words or [])]),
        confidence_threshold=1,
        homophones={},
        search_radius=None,
    )


class FakeReader:
    SCREEN = (0, 0, 100, 100)

    def __init__(self):
        self.read_screen_calls: list[tuple[int, int, int, int] | None] = []
        self.read_current_window_calls = 0

    def read_screen(self, bounding_box: tuple[int, int, int, int] | None = None):
        self.read_screen_calls.append(bounding_box)
        return _contents(bounding_box or self.SCREEN)

    def read_current_window(self):
        self.read_current_window_calls += 1
        return _contents((20, 30, 120, 150))


def _cache(reader: FakeReader) -> OcrCache:
    return OcrCache(cast(screen_ocr.Reader, reader))


def test_subset_time_range_reuses_cache():
    reader = FakeReader()
    cache = _cache(reader)

    first = cache.read((1, 4), None)
    second = cache.read((2, 3), None)

    assert second is first
    assert reader.read_screen_calls == [None]


def test_non_subset_time_range_misses_cache():
    reader = FakeReader()
    cache = _cache(reader)

    cache.read((1, 2), None)
    cache.read((3, 4), None)

    assert reader.read_screen_calls == [None, None]


def test_active_window_fallback():
    reader = FakeReader()
    cache = OcrCache(
        cast(screen_ocr.Reader, reader),
        fallback_when_no_eye_tracker=EyeTrackerFallback.ACTIVE_WINDOW,
    )

    cache.read((1, 2), None)

    assert reader.read_current_window_calls == 1
    assert reader.read_screen_calls == []


def test_empty_cache_miss_does_not_warn(caplog):
    reader = FakeReader()
    cache = _cache(reader)

    with caplog.at_level(logging.WARNING):
        cache.read((1, 2), None)

    assert not caplog.records


def test_cache_hit_does_not_warn(caplog):
    reader = FakeReader()
    cache = _cache(reader)
    cache.read((1, 4), None)

    with caplog.at_level(logging.WARNING):
        cache.read((2, 3), None)

    assert not caplog.records


def test_populated_cache_miss_warns_with_process_lifetime_rate(caplog, monkeypatch):
    monkeypatch.setattr(_gaze_ocr, "_populated_cache_call_count", 0)
    monkeypatch.setattr(_gaze_ocr, "_populated_cache_miss_count", 0)

    first_reader = FakeReader()
    first_cache = _cache(first_reader)
    first_cache.read((1, 4), None)
    first_cache.read((2, 3), None)

    second_reader = FakeReader()
    second_cache = _cache(second_reader)
    second_cache.read((10, 11), None)

    with caplog.at_level(logging.WARNING):
        first_cache.read((5, 6), None)
        second_cache.read((12, 13), (0, 0, 10, 10))

    assert len(caplog.records) == 2
    assert caplog.records[0].message == (
        "OCR cache miss with populated cache: requested_time_range=(5, 6), "
        "cached_time_range=(1, 4), requested_bounds=None; "
        "misses=50.0% of 2 calls"
    )
    assert caplog.records[1].message == (
        "OCR cache miss with populated cache: requested_time_range=(12, 13), "
        "cached_time_range=(10, 11), requested_bounds=(0, 0, 10, 10); "
        "misses=66.7% of 3 calls"
    )


def test_controller_start_reading_is_noop_and_reads_reuse_ocr_cache():
    reader = FakeReader()
    controller = Controller(
        ocr_reader=cast(screen_ocr.Reader, reader),
        eye_tracker=None,
        mouse=None,
        keyboard=None,
    )
    try:
        controller.start_reading_nearby()
        assert reader.read_screen_calls == []

        first = controller.read_nearby((1, 4))
        second = controller.read_nearby((2, 3))

        assert second is first
        assert controller.latest_screen_contents() is first
        assert reader.read_screen_calls == [None]
    finally:
        controller.shutdown()

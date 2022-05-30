import bisect
from collections import deque
from dataclasses import dataclass
from talon import actions, tracking_system, ui
from talon.types import Point2d


class Mouse(object):
    def move(self, coordinates):
        actions.mouse_move(*coordinates)

    def click(self):
        actions.mouse_click()

    def click_down(self):
        actions.mouse_drag()

    def click_up(self):
        actions.mouse_release()

    def scroll_down(self, n=1):
        for _ in range(n):
            actions.user.mouse_scroll_down()

    def scroll_up(self, n=1):
        for _ in range(n):
            actions.user.mouse_scroll_up()


class Keyboard(object):
    def type(self, text):
        actions.insert(text)

    def shift_down(self):
        actions.key("shift:down")

    def shift_up(self):
        actions.key("shift:up")

    def left(self, n=1):
        for _ in range(n):
            actions.key("left")

    def right(self, n=1):
        for _ in range(n):
            actions.key("right")


@dataclass
class BoundingBox(object):
    left: int
    right: int
    top: int
    bottom: int


class TalonEyeTracker(object):
    def __init__(self):
        # !!! Using unstable private API that may break at any time !!!
        tracking_system.register("gaze", self._on_gaze)
        self._gaze = None
        self.is_connected = True
        # Keep approximately 10 seconds of frames on Tobii 5
        self._queue = deque(maxlen=1000)
        self._ts_queue = deque(maxlen=1000)

    def _on_gaze(self, frame):
        self._gaze = frame.gaze
        self._queue.append(frame)
        self._ts_queue.append(frame.ts)

    def has_gaze_point(self):
        return self._gaze

    def get_gaze_point_or_default(self):
        if not self._gaze:
            return (0, 0)
        return self._gaze_to_pixels(self._gaze)

    def get_gaze_point_at_timestamp(self, timestamp):
        if not self._queue:
            print("No gaze history available")
            return (0, 0)
        frame_index = bisect.bisect_left(self._ts_queue, timestamp)
        if frame_index == len(self._queue):
            frame_index -= 1
        frame = self._queue[frame_index]
        if abs(frame.ts - timestamp) > 0.1:
            print(
                "No gaze history available at that time: {}. Range: [{}, {}]".format(
                    timestamp, self._ts_queue[0], self._ts_queue[-1]
                )
            )
            # Fall back to latest frame.
            frame = self._queue[-1]
        return self._gaze_to_pixels(frame.gaze)

    def get_gaze_bounds_during_time_range(self, start_timestamp, end_timestamp):
        if not self._queue:
            print("No gaze history available")
            return None
        start_index = bisect.bisect_left(self._ts_queue, start_timestamp)
        if start_index == len(self._queue):
            start_index -= 1
        end_index = bisect.bisect_left(self._ts_queue, end_timestamp)
        if end_index == len(self._queue):
            end_index -= 1
        left = right = top = bottom = None
        for i in range(start_index, end_index + 1):
            frame = self._queue[i]
            if frame.ts < start_timestamp - 0.1 or frame.ts > end_timestamp + 0.1:
                continue
            left = min(frame.gaze.x, left) if left else frame.gaze.x
            top = min(frame.gaze.y, top) if top else frame.gaze.y
            right = max(frame.gaze.x, right) if right else frame.gaze.x
            bottom = max(frame.gaze.y, bottom) if bottom else frame.gaze.y
        if not left:
            return None
        top_left = self._gaze_to_pixels(Point2d(x=left, y=top))
        bottom_right = self._gaze_to_pixels(Point2d(x=right, y=bottom))
        return BoundingBox(
            left=top_left[0],
            top=top_left[1],
            right=bottom_right[0],
            bottom=bottom_right[1],
        )

    @staticmethod
    def _gaze_to_pixels(gaze):
        rect = ui.main_screen().rect
        pos = rect.pos + gaze * rect.size
        pos = rect.clamp(pos)
        return (pos.x, pos.y)

    def move_to_gaze_point(self, offset=(0, 0)):
        gaze = self.get_gaze_point_or_default()
        x = gaze[0] + offset[0]
        y = gaze[1] + offset[1]
        actions.mouse_move(x, y)

from talon import actions


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


class Windows(object):
    def get_monitor_size(self):
        pass
        # primary = dragonfly.Monitor.get_all_monitors()[0]
        # return (primary.rectangle.dx, primary.rectangle.dy)
    
    def get_foreground_window_center(self):
        pass
        # window_position = dragonfly.Window.get_foreground().get_position()
        # return (window_position.x_center, window_position.y_center)

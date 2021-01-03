import dragonfly


class Mouse(object):
    def move(self, coordinates):
        dragonfly.Mouse("[{}, {}]".format(*coordinates)).execute()

    def click(self):
        dragonfly.Mouse("left").execute()

    def click_down(self):
        dragonfly.Mouse("left:down").execute()

    def click_up(self):
        dragonfly.Mouse("left:up").execute()

    def scroll_down(self, n=1):
        dragonfly.Mouse("wheeldown:{}".format(n)).execute()

    def scroll_up(self, n=1):
        dragonfly.Mouse("wheelup:{}".format(n)).execute()


class Keyboard(object):
    def type(self, text):
        dragonfly.Text(text.replace("%", "%%")).execute()

    def shift_down(self):
        dragonfly.Key("shift:down").execute()

    def shift_up(self):
        dragonfly.Key("shift:up").execute()

    def left(self, n=1):
        dragonfly.Key("left:{}".format(n)).execute()

    def right(self, n=1):
        dragonfly.Key("right:{}".format(n)).execute()


class Windows(object):
    def get_monitor_size(self):
        primary = dragonfly.Monitor.get_all_monitors()[0]
        return (primary.rectangle.dx, primary.rectangle.dy)
    
    def get_foreground_window_center(self):
        window_position = dragonfly.Window.get_foreground().get_position()
        return (window_position.x_center, window_position.y_center)

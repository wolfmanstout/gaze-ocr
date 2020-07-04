import dragonfly


class Mouse(object):
    def move(self, coordinates):
        dragonfly.Mouse("[{}, {}]".format(*coordinates)).execute()

    def click_down(self):
        dragonfly.Mouse("left:down").execute()

    def click_up(self):
        dragonfly.Mouse("left:up").execute()


class Keyboard(object):
    def type(self, text):
        dragonfly.Text(text.replace("%", "%%")).execute()


class Windows(object):
    def get_foreground_window_center(self):
        window_position = dragonfly.Window.get_foreground().get_position()
        return (window_position.x_center, window_position.y_center)

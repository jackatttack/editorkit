"""Accessory: the window's accessory as a column of tiles, with an optional
Controls row behind ⋯ in the header. Layouts build on it so every tool's
second header works the same way.

    accessory = Accessory(window, [path], controls=tiles.Controls(window))
"""
from .. import tiles


# --- Settings -------------------------------------------------------------

MORE_ICON = '⋯'
MORE_BUTTON = 'more'           # the header button's name


def controls(window, intro='', stack=()):
    """⋯ in the header and a Controls row (with ? help) for any window, with
    or without a layout: returns the Controls tile to add() to. stack is any
    other tiles for the accessory, below the controls.

        controls = layouts.controls(window, intro='What this tool does.')
        controls.add('wrap', '↩', toggled, about='Wrap long lines.')
    """
    tile = tiles.Controls(window, intro=intro)
    Accessory(window, stack, tile)
    return tile


class Accessory:

    def __init__(self, window, stack, controls=None):
        self.window = window
        self.controls = controls
        stack = list(stack)
        if controls is not None:
            controls.hidden = True
            stack.insert(0, controls)
            window.add_button(MORE_ICON, lambda _window: self.toggle_controls(),
                              name=MORE_BUTTON)
        self.column = tiles.Column(window, stack, on_resize=self.fit)
        self.fit(self.column.height_needed())

    def fit(self, height):
        self.window.set_accessory(self.column, height)

    def toggle_controls(self):
        showing = self.controls.hidden
        self.column.set_visible(self.controls, showing)
        self.window.set_button(MORE_BUTTON, on=showing)
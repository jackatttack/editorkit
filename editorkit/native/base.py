"""What every tile shares: the window it lives in, its colours and a clock.

A tile is a ui.View that knows its window. Colours come from the window's
palette, which follows the editor's theme; a tile built before its window
has been shown reads the theme directly, so it never waits for one.
"""
import ui

from ..windows import look


# --- Settings -------------------------------------------------------------

ROW_HEIGHT = 36          # fields and buttons
PADDING = 6              # around a tile's contents
GAP = 6                  # between neighbours
CORNER_RADIUS = 10       # the card kit's buttons' corners
FONT_SIZE = 14
BUTTON_FONT = ('<system>', 15)
WASH = 0.12              # a button's fill: the theme's text colour at this strength (--wash-strong)
RULE = 0.14              # its hairline edge (--rule)


# --- Colours --------------------------------------------------------------

def palette_for(window):
    """The window's palette, or the editor theme's when the window has not
    been built yet."""
    palette = getattr(window, 'palette', None)
    return palette if palette is not None else look.palette()


def style_field(field, palette, monospace=True):
    """A ui.TextField in tile style: themed, plain, no autocorrect."""
    field.font = ('Menlo' if monospace else '<system>', FONT_SIZE)
    field.background_color = palette.background
    field.text_color = palette.text
    field.tint_color = palette.accent
    field.corner_radius = CORNER_RADIUS
    field.bordered = False
    field.autocorrection_type = False
    field.spellchecking_type = False
    field.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
    field.clear_button_mode = 'while_editing'
    return field


def wash(colour, alpha):
    """colour at alpha: the theme's text colour as a faint fill or line, so it
    reads on light and dark themes alike (the web pages' --wash and --rule)."""
    red, green, blue = ui.parse_color(colour)[:3]
    return (red, green, blue, alpha)


def paint_button(button, palette, on=False):
    """A button lit (the accent) or not (a faint wash with a hairline edge),
    as the card kit's buttons are."""
    button.background_color = palette.accent if on else wash(palette.text, WASH)
    button.tint_color = palette.on_accent if on else palette.text
    button.border_width = 0 if on else 0.5
    button.border_color = wash(palette.text, RULE)


def make_button(title, action, palette):
    """A themed button; a tap calls action(sender)."""
    button = ui.Button(title=title, font=BUTTON_FONT)
    paint_button(button, palette)
    button.corner_radius = CORNER_RADIUS
    button.action = action
    return button


# --- The base -------------------------------------------------------------

class Tile(ui.View):
    """Base for tiles: keeps the window, the palette and a clock.

    every(callback) adds callback(now) to the tile's clock. The window calls
    tick(now) on its pages, sheet and accessory, so a tile placed in any of
    them can carry a tool's regular work (taking in results, rechecking).
    """

    def __init__(self, window):
        self.window = window
        self.palette = palette_for(window)
        self.clock = []
        self.background_color = look.CLEAR

    def every(self, callback):
        self.clock.append(callback)
        return callback

    def tick(self, now):
        for callback in list(self.clock):
            callback(now)
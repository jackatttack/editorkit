"""How windows look and feel: every timing and size in one place (editable),
and the palette, taken from the editor's theme so windows always match it."""
from .. import themes

# ---- Feel (editable) --------------------------------------------------------
GROW_SECONDS = 0.28           # pin -> panel: the panel grows out of the pin
SHRINK_SECONDS = 0.24         # panel -> pin
CONTENT_FADE_SECONDS = 0.16   # pages fade in after a grow, and out before a shrink
HANDOFF_SECONDS = 0.32        # a picture's trip to or from the keyboard's place
GHOST_FADE_SECONDS = 0.14     # the picture fading off the landed panel
PIN_FADE_SECONDS = 0.16
CLOSE_SECONDS = 0.2
HOLD_SECONDS = 0.22           # how long a still finger takes to pick something up
SLOP = 8                      # points a finger may wander and still be a tap or a hold
HOLD_MOVE_SECONDS = 0.35      # hold anywhere on a panel this long to move it
HOLD_MOVE_SLOP = 10           # points a finger may wander during that hold
LIFT_GROW = 4                 # points a lifted pin grows by
LIFT_ALPHA = 0.85
LIFT_SECONDS = 0.12
SNAP_SECONDS = 0.22
GRAB_ALPHA = 0.92             # a held panel dims a touch
DOCK_LINE = 0.7               # let go with the panel's top below this share of the
                              #   editor's height: it goes to the keyboard's place
TAB_LINE = -16                # let go with a window's top this far above the code:
                              #   it goes into the tab row
TAB_DROP_ALL = False          # True: every window can be dropped into the tab row (to_tab);
                              #   False: only windows with their own on_tab_drop
TAB_APPEAR_SECONDS = 0.35     # a window's new tab fades in over this as the window lands in it
TAB_SHRINK_ALPHA = 0.35       # how see-through a window is as it flies into its tab
DOCK_LINE_ALPHA = 0.35
DOCK_ALPHA = 0.6              # the panel while it is past the dock line
PULL_OUT = 50                 # in the keyboard's place, pull up this far to come back
CONSOLE_SLIDE_SECONDS = 0.3   # the console slide windows ask Pythonista for
PANEL_OVERHANG = 24           # a panel poking this far past the console's edge (right;
                              #   from the console, the left) crosses over
PIN_OVERHANG = 4              # a pin's pill poking this far past it crosses over
EDGE_DWELL_SECONDS = 0.35     # held poking out this long: it crosses without letting go
FLING_SPEED = 900             # a fling this fast (points a second) lines a pin or panel
                              #   up with the edge it was flung at; it never crosses

CLOSE_KEYBOARD_ON_OPEN = True # opening a window puts the keyboard away
CLOSE_KEYBOARD_ON_DRAG = True # moving or resizing a window puts it away too (not while
                              #   a window holds the keyboard's place: that would fold it)
BLOCK_SWIPES = True           # side swipes off while a drag is on
SNAP_PINS_TO_SIDES = True     # False: a pin stays exactly where it is dropped
MINIMISE_TO = 'tray'          # – sends a window to 'tray' (a chip in the home's bar), 'pin',
                              #   or 'tab' (a stand-in tab in Pythonista's tab row)
PIN_STYLE = 'soft'            # 'soft' (the theme's bar colour, outlined) or 'accent' (its tint)

# ---- Size (editable) --------------------------------------------------------
EDGE = 12
EMOJI = '🐍'                  # every window's default emoji
PIN_HEIGHT = 36
PIN_MAX_WIDTH = 240
PIN_FONT = ('<system-bold>', 15)
TOUCH_PAD = 8                 # a clear rim around a pin that still counts as the pin
PIN_STACK_GAP = 6             # new pins stack down the right edge
DEFAULT_HEIGHT_SHARE = 0.6    # a new window: the editor's width, this share of its height
DEFAULT_MAX_WIDTH = 600       # ...but never wider than this (a wide screen: the iPad)
DEFAULT_MAX_HEIGHT = 640      # ...nor taller than this
DEFAULT_MIN_SIZE = (96, 44)   # header only; Window(min_size=...) asks for more
KEYBOARD_HEIGHT = 300
TOP_BAR_HEIGHT = 128          # Window(home='top_bar'): header plus one row of controls
ABOVE_KEYBOARD_HEIGHT = 240   # Window(home='above_dock') and move_to('above_dock')
BACKDROP_ALPHA = 0.6          # Window(backdrop='tinted'): the page area's opacity
HEADER_FILL_ALPHA = 0.94      # a tinted or clear window keeps its header this solid
INSET_TOP_REACH = 24          # a window this close to the top insets the code
CORNER_RADIUS = 14
HEADER_HEIGHT = 44
TAB_HEIGHT = 34
BUTTON_WIDTH = 84
CLOSE_WIDTH = 36
EMOJI_GRIP_WIDTH = 44
HANDLE_SIZE = 60              # the resize corner's touch square (the ◢ stays small in its
                              # corner); was 36, too small against an iPad's screen corner
HANDLE_MIN_SIZE = 24          # short windows shrink the corner (never over half the space
                              # under the header), down to this
TIDY_MIN_WIDTH = 240          # ek.tidy(): windows never narrower than this if it can help it
TIDY_MIN_HEIGHT = 150         # nor shorter (a header and a few lines)
TIDY_ASPECT = 1.2             # the cell shape (width / height) tidy aims for
TIDY_UNDO_SECONDS = 30        # a second tidy within this puts the windows back
HEADER_BUTTON_SIZE = 30       # the header's square buttons: ✕  –  >_ or { }  ⌨ or ⇡
HEADER_BUTTON_GAP = 4
# Full screen (2026-11-12): ＋ shows the window's page as a Pythonista sheet
# (fullsheet.py); ⤡, −, or closing the sheet brings it back to its window.
FULL_BUTTON = True            # every window gets the ＋ button
FULL_ICON = '＋'
FULL_EXIT_ICON = '⤡'
FULL_PAGE_TICK_SECONDS = 0.05 # the sheet's page clock (fullsheet.py), as the windows clock
FULL_STYLE = 'fullscreen'     # Pythonista's present style: 'fullscreen' stays put
                              # (− or ⤡ leaves); 'sheet' is a card a swipe can dismiss
COMPACT_WIDTH = 230           # narrower than this: the header keeps the emoji and ✕
BIG_TEXT_LIMIT = 40           # one line up to this long is drawn big, like a display
BIG_TEXT_SIZE = 48            # its starting size; it shrinks to fit
LABEL_LINE_LIMIT = 12         # up to this many lines: a label; more: a scrolling text view

# ---- Machinery --------------------------------------------------------------
TICK_SECONDS = 1 / 30.0       # the clock: set once, never changed (stability guide)
THEME_CHECK_SECONDS = 1.0     # how often the manager looks for a theme change
CLEAR = (0, 0, 0, 0)          # None is not see-through on a view hosted by UIKit
FLEXIBLE_SIZE = 2 | 16        # UIViewAutoresizingFlexibleWidth | FlexibleHeight


class Palette:
    """Window colours from the editor's theme. Theme keys are matched in order
    of preference; anything missing falls back to a dark default."""

    def __init__(self, colours):
        def pick(*names):
            for name in names:
                if colours.get(name):
                    return colours[name]
            return None

        self.background = pick('background') or '#1e1e24'
        self.panel = pick('bar_background', 'tab_background') or self.background
        self.text = pick('default_text') or '#e6e6ea'
        self.dim = pick('line_number') or '#8a8a96'
        self.accent = pick('tint') or '#ff2d55'
        self.edge = pick('separator_line', 'gutter_border') or '#33333d'
        self.on_accent = self.background
        self.syntax = {}               # codeview class -> colour, from the theme's scopes

    def update(self, colours, syntax=None):
        """Take a new theme's colours in place, so every window and tile
        holding this palette sees them (the theme changed)."""
        self.__init__(colours)
        self.syntax = dict(syntax or {})


def palette():
    result = Palette(themes.theme_colours())
    result.syntax = themes.syntax_colours()
    return result
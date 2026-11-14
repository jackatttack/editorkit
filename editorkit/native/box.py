"""Box: the row of chips where a window's folded pieces wait.

An owner window (pieces made with Window(owner=it)) gets one automatically
under its header while something is folded into it; the tray home (the
Toolbox hub) uses the same parts in its own row. Each chip shows a piece's
emoji and title: tap brings the piece back out, hold then let go closes it.
Chips scroll sideways when they overflow.

    box = tiles.Box(window)                  # on_tap / on_hold default to show / close
    box.show(window.tray())                  # the pieces, most recent first
"""
import time

import ui

from .base import Tile

HEIGHT = 56
CHIP_HEIGHT = 40
CHIP_GAP = 8
CHIP_FONT = ('<system-bold>', 15)
HOLD_TO_CLOSE_SECONDS = 0.45     # hold a chip this long, then let go: close
TAP_SLOP = 8                     # points a finger may wander and still tap


class Chip(ui.View):
    """One folded piece. Tap: bring it back. Hold, then let go: close it."""

    def __init__(self, piece, palette, on_tap, on_hold):
        self.piece = piece
        self.on_tap = on_tap
        self.on_hold = on_hold
        self.corner_radius = CHIP_HEIGHT / 2.0
        self.border_width = 1
        self.label = ui.Label(font=CHIP_FONT, alignment=ui.ALIGN_CENTER,
                              text='%s  %s' % (piece.emoji, piece.title))
        self.label.touch_enabled = False
        self.add_subview(self.label)
        self.paint(palette)
        self.width = ui.measure_string(self.label.text, font=CHIP_FONT)[0] + 28
        self.height = CHIP_HEIGHT
        self.pressed_at = None
        self.travel = 0.0

    def paint(self, palette):
        self.background_color = palette.background
        self.border_color = palette.edge
        self.label.text_color = palette.text

    def layout(self):
        self.label.frame = (0, 0, self.width, self.height)

    def touch_began(self, touch):
        self.pressed_at = time.time()
        self.travel = 0.0
        self.alpha = 0.6

    def touch_moved(self, touch):
        self.travel += (abs(touch.location.x - touch.prev_location.x)
                        + abs(touch.location.y - touch.prev_location.y))
        if self.travel > TAP_SLOP:
            self.pressed_at = None            # a scroll, not a tap or a hold
            self.alpha = 1.0

    def touch_ended(self, touch):
        self.alpha = 1.0
        if self.pressed_at is None:
            return
        held = time.time() - self.pressed_at
        self.pressed_at = None
        if held >= HOLD_TO_CLOSE_SECONDS:
            self.on_hold(self.piece)
        else:
            self.on_tap(self.piece)


class Box(Tile):
    """A row of Chips, one per folded piece, most recent first."""

    HEIGHT = HEIGHT

    def __init__(self, window, on_tap=None, on_hold=None, empty_text=''):
        Tile.__init__(self, window)
        self.on_tap = on_tap or (lambda piece: piece.show())
        self.on_hold = on_hold or (lambda piece: piece.close())
        self.scroll = ui.ScrollView()
        self.scroll.shows_horizontal_scroll_indicator = False
        self.scroll.background_color = (0, 0, 0, 0)
        self.add_subview(self.scroll)
        self.empty = ui.Label(text=empty_text, alignment=ui.ALIGN_CENTER, font=('<system>', 13))
        self.empty.text_color = self.palette.dim
        self.empty.touch_enabled = False
        self.add_subview(self.empty)
        self.chips = []

    def layout(self):
        self.scroll.frame = (0, 0, self.width, self.height)
        self.empty.frame = (0, 0, self.width, self.height)
        self.place_chips()

    def show(self, pieces):
        palette = getattr(self.window, 'palette', None) or self.palette
        for chip in self.chips:
            self.scroll.remove_subview(chip)
        self.chips = [Chip(piece, palette, self.on_tap, self.on_hold) for piece in pieces]
        for chip in self.chips:
            self.scroll.add_subview(chip)
        self.empty.hidden = bool(self.chips)
        self.place_chips()

    def place_chips(self):
        x = CHIP_GAP
        top = (self.height - CHIP_HEIGHT) / 2.0
        for chip in self.chips:
            chip.frame = (x, top, chip.width, CHIP_HEIGHT)
            x += chip.width + CHIP_GAP
        self.scroll.content_size = (x, self.height)

    def restyle(self):
        palette = getattr(self.window, 'palette', None) or self.palette
        self.empty.text_color = palette.dim
        for chip in self.chips:
            chip.paint(palette)
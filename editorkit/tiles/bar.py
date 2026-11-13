"""Bar: one slim line saying what a folded-away part holds; a tap opens it.

    bar = tiles.Bar(window, on_tap=lambda bar: unfold())
    bar.set_text('def · in deck · 133')

Used where space is tight (the keyboard's place) to stand in for a field
and its rows: one job on screen, the rest a tap away.
"""
import ui

from .base import PADDING, Tile


# --- Settings -------------------------------------------------------------

FONT = ('<system>', 13)
OPEN_ICON = '▾'
ICON_WIDTH = 24


class Bar(Tile):
    HEIGHT = 30                  # what a layout gives it

    def __init__(self, window, on_tap=None):
        Tile.__init__(self, window)
        self.on_tap = on_tap

        self.label = ui.Label(font=FONT)
        self.label.text_color = self.palette.text
        self.label.touch_enabled = False
        self.add_subview(self.label)

        self.icon = ui.Label(font=FONT, alignment=ui.ALIGN_CENTER, text=OPEN_ICON)
        self.icon.text_color = self.palette.dim
        self.icon.touch_enabled = False
        self.add_subview(self.icon)

    def set_text(self, text):
        if text != self.label.text:
            self.label.text = text

    def layout(self):
        self.icon.frame = (self.width - PADDING - ICON_WIDTH, 0, ICON_WIDTH, self.height)
        self.label.frame = (PADDING * 2, 0, max(0, self.icon.x - PADDING * 2), self.height)

    def touch_ended(self, touch):
        if self.on_tap:
            self.on_tap(self)
"""Split: two tiles, one above the other, with a hairline between.

    split = tiles.Split(window, folders, code, ratio=0.45)

The top tile takes ratio of the height. Ticks are passed on to both.
"""
import ui

from .base import Tile


class Split(Tile):

    def __init__(self, window, top, bottom, ratio=0.45):
        Tile.__init__(self, window)
        self.top_tile = top
        self.bottom_tile = bottom
        self.ratio = ratio
        self.line = ui.View(background_color=self.palette.edge)
        for view in (top, self.line, bottom):
            self.add_subview(view)

    def layout(self):
        split = round(self.height * self.ratio)
        self.top_tile.frame = (0, 0, self.width, split)
        self.line.frame = (0, split, self.width, 1)
        self.bottom_tile.frame = (0, split + 1, self.width, max(0, self.height - split - 1))

    def tick(self, now):
        Tile.tick(self, now)
        for tile in (self.top_tile, self.bottom_tile):
            tick = getattr(tile, 'tick', None)
            if tick:
                tick(now)
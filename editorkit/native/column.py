"""Column: tiles stacked top to bottom, each at its own HEIGHT.

    top = tiles.Column(window, [controls, field],
                       on_resize=lambda height: window.set_accessory(top, height))
    top.set_visible(controls, True)

Hidden tiles take no room. When one is shown or hidden, on_resize(height)
is called with the new total, so the owner can give the column that much
room (the accessory, in query_list). Ticks are passed on to every tile.
"""
from .base import Tile


class Column(Tile):

    def __init__(self, window, stack, on_resize=None):
        Tile.__init__(self, window)
        self.stack = list(stack)
        self.on_resize = on_resize
        for tile in self.stack:
            self.add_subview(tile)

    def height_needed(self):
        return sum(tile.HEIGHT for tile in self.stack if not tile.hidden)

    def set_visible(self, tile, visible):
        tile.hidden = not visible
        if self.on_resize:
            self.on_resize(self.height_needed())
        self.layout()

    def refit(self):
        """After hiding or showing several tiles at once: resize the owner
        once and lay out."""
        if self.on_resize:
            self.on_resize(self.height_needed())
        self.layout()

    def layout(self):
        y = 0
        for tile in self.stack:
            if tile.hidden:
                continue
            tile.frame = (0, y, self.width, tile.HEIGHT)
            y += tile.HEIGHT

    def tick(self, now):
        Tile.tick(self, now)
        for tile in self.stack:
            tick = getattr(tile, 'tick', None)
            if tick:
                tick(now)
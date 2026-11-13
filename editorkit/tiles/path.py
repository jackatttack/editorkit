"""Path: where you are, as a row of folder names; tap one to go there.

    path = tiles.Path(window, on_pick=go)     # go(folder) gets the full path
    path.show('/…/Documents/projects/editorkit')

    Documents › projects › editorkit

The row starts at the nearest folder named STOP_NAME above the one shown
(local and iCloud Documents both work) and scrolls to keep the current
folder, in bold, in view.
"""
import os

import ui

from .base import PADDING, Tile


# --- Settings -------------------------------------------------------------

STOP_NAME = 'Documents'
SEPARATOR = '›'
SEPARATOR_WIDTH = 14
FONT = ('<system>', 13)
CURRENT_FONT = ('<system-bold>', 13)
CHARACTER_WIDTH = 7.5        # rough width of one character, for sizing buttons
ITEM_PADDING = 12


def folder_chain(folder, stop_name=STOP_NAME):
    """[(name, path)] from the stop folder down to folder."""
    chain = []
    current = os.path.normpath(folder)
    while True:
        chain.append((os.path.basename(current) or current, current))
        parent = os.path.dirname(current)
        if os.path.basename(current) == stop_name or parent == current:
            break
        current = parent
    return list(reversed(chain))


class Path(Tile):
    HEIGHT = 32                  # what a layout gives it

    def __init__(self, window, on_pick=None):
        Tile.__init__(self, window)
        self.on_pick = on_pick
        self.items = []          # [(view, width)], left to right
        self.scroll = ui.ScrollView()
        self.scroll.shows_horizontal_scroll_indicator = False
        self.add_subview(self.scroll)

    def show(self, folder):
        for view, _ in self.items:
            self.scroll.remove_subview(view)
        self.items = []
        chain = folder_chain(folder)
        for number, (name, path) in enumerate(chain):
            if number:
                self.add_separator()
            last = number == len(chain) - 1
            button = ui.Button(title=name, font=CURRENT_FONT if last else FONT)
            button.tint_color = self.palette.accent if last else self.palette.text
            button.action = lambda sender, path=path: self.picked(path)
            self.add_item(button, ITEM_PADDING + CHARACTER_WIDTH * len(name))
        self.layout()
        overflow = self.scroll.content_size[0] - self.scroll.width
        self.scroll.content_offset = (max(0, overflow), 0)

    def picked(self, path):
        if self.on_pick:
            self.on_pick(path)

    def add_separator(self):
        label = ui.Label(text=SEPARATOR, font=FONT, alignment=ui.ALIGN_CENTER)
        label.text_color = self.palette.dim
        label.touch_enabled = False
        self.add_item(label, SEPARATOR_WIDTH)

    def add_item(self, view, width):
        self.scroll.add_subview(view)
        self.items.append((view, width))

    def layout(self):
        self.scroll.frame = (PADDING, 0, max(0, self.width - 2 * PADDING), self.height)
        x = 0
        for view, width in self.items:
            view.frame = (x, 0, width, self.height)
            x += width
        self.scroll.content_size = (x, self.height)
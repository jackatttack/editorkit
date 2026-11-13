"""Chips: a row of word buttons that light up when on (Search's Names, Code
and scope).

    chips = tiles.Chips(window)
    chips.add('names', 'Names', toggled, on=True)    # a tap calls toggled(name)
    chips.set_on('names', False)
    chips.set_label('scope', 'in deck ▾')

Each chip is as wide as its words; the row runs left to right and a chip
that would run past the edge is cut to fit.
"""
import ui

from .base import GAP, PADDING, ROW_HEIGHT, Tile, make_button


# --- Settings -------------------------------------------------------------

CHIP_FONT = ('<system>', 15)     # used to measure a chip's words
CHIP_PADDING = 14                # each side of the words
MIN_WIDTH = 44


class Chips(Tile):
    HEIGHT = ROW_HEIGHT + PADDING      # what a layout gives it

    def __init__(self, window):
        Tile.__init__(self, window)
        self.entries = []              # [{'name', 'button'}], left to right

    def add(self, name, label, action, on=False):
        button = make_button(label, lambda sender, name=name: action(name), self.palette)
        self.add_subview(button)
        self.entries.append({'name': name, 'button': button})
        self.paint(button, on)
        self.layout()
        return button

    def entry(self, name):
        for entry in self.entries:
            if entry['name'] == name:
                return entry
        raise KeyError('no chip named %r' % name)

    def set_on(self, name, on=True):
        self.paint(self.entry(name)['button'], on)

    def set_label(self, name, label):
        self.entry(name)['button'].title = label
        self.layout()

    def paint(self, button, on):
        button.background_color = self.palette.accent if on else self.palette.background
        button.tint_color = self.palette.on_accent if on else self.palette.text

    def layout(self):
        top = (self.height - ROW_HEIGHT) / 2.0
        left = PADDING
        for entry in self.entries:
            button = entry['button']
            if button.hidden:
                continue
            words = ui.measure_string(button.title or '', font=CHIP_FONT)[0]
            width = max(MIN_WIDTH, words + 2 * CHIP_PADDING)
            width = min(width, max(MIN_WIDTH, self.width - PADDING - left))
            button.frame = (left, top, width, ROW_HEIGHT)
            left += width + GAP
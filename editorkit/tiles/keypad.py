"""Keypad: pages of keys in rows, filling the space it is given.

    keypad = tiles.Keypad(window, pages, on_key=pressed, first='123')
    keypad.show_page('f(x)')

pages maps a page name to rows; a row is a list of key specs (dicts):
label (shown), kind ('digit', 'op', 'action' or 'go': sets the look), span
(relative width, default 1), plus whatever the tool needs (insert, do, …).
A tap calls on_key(spec). Rows share the height evenly and keys share their
row by span, so a pad suits the keyboard's place at any size.
"""
import ui

from .base import Tile


# --- Settings -------------------------------------------------------------

GAP = 6
CORNER_RADIUS = 8
FONT = ('<system>', 20)
SMALL_FONT = ('<system>', 15)        # labels longer than SHORT_LABEL
SHORT_LABEL = 3


class Keypad(Tile):

    def __init__(self, window, pages, on_key=None, first=None):
        Tile.__init__(self, window)
        self.pages = pages
        self.on_key = on_key
        self.page = None
        self.rows = []                   # [[(button, span)]] for the page shown
        self.show_page(first or next(iter(pages)))

    def show_page(self, name):
        for row in self.rows:
            for button, _ in row:
                self.remove_subview(button)
        self.page = name
        self.rows = []
        for specs in self.pages[name]:
            row = []
            for spec in specs:
                button = self.make_key(spec)
                self.add_subview(button)
                row.append((button, spec.get('span', 1)))
            self.rows.append(row)
        self.layout()

    def make_key(self, spec):
        palette = self.palette
        label = spec['label']
        button = ui.Button(title=label, font=FONT if len(label) <= SHORT_LABEL else SMALL_FONT)
        button.corner_radius = CORNER_RADIUS
        kind = spec.get('kind', 'digit')
        if kind == 'go':
            button.background_color, button.tint_color = palette.accent, palette.on_accent
        elif kind == 'action':
            button.background_color, button.tint_color = palette.edge, palette.text
        elif kind == 'op':
            button.background_color, button.tint_color = palette.background, palette.accent
        else:
            button.background_color, button.tint_color = palette.background, palette.text
        button.action = lambda sender, spec=spec: self.pressed(spec)
        return button

    def pressed(self, spec):
        if self.on_key:
            self.on_key(spec)

    def layout(self):
        if not self.rows:
            return
        count = len(self.rows)
        row_height = max(0, (self.height - GAP * (count + 1)) / float(count))
        for number, row in enumerate(self.rows):
            y = GAP + number * (row_height + GAP)
            total = sum(span for _, span in row) or 1
            unit = max(0, (self.width - GAP * (len(row) + 1)) / float(total))
            x = GAP
            for button, span in row:
                width = unit * span + GAP * (span - 1)
                button.frame = (x, y, width, row_height)
                x += width + GAP
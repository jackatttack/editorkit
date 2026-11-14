"""Card: a message laid over the page as the window's sheet; a tap closes it.

    card = tiles.Card(window, 'What this does…', on_close=done)
    window.show_sheet(card)
    card.set_text('Something else')

A tap calls on_close() when given (the owner closes the sheet), otherwise
it closes the sheet itself.
"""
import ui

from .base import Tile


# --- Settings -------------------------------------------------------------

MARGIN = 16
HINT_HEIGHT = 28
TEXT_FONT = ('<system>', 15)
HINT_FONT = ('<system>', 12)
HINT_TEXT = 'Tap to close'


class Card(Tile):

    def __init__(self, window, text='', on_close=None):
        Tile.__init__(self, window)
        self.background_color = self.palette.panel     # opaque: a sheet
        self.on_close = on_close

        self.label = ui.Label(font=TEXT_FONT)
        self.label.number_of_lines = 0
        self.label.text_color = self.palette.text
        self.label.touch_enabled = False
        self.add_subview(self.label)

        self.hint = ui.Label(font=HINT_FONT, alignment=ui.ALIGN_CENTER, text=HINT_TEXT)
        self.hint.text_color = self.palette.dim
        self.hint.touch_enabled = False
        self.add_subview(self.hint)
        self.set_text(text)

    def set_text(self, text):
        self.label.text = text or ''
        self.layout()

    def layout(self):
        width = max(0, self.width - 2 * MARGIN)
        self.label.frame = (MARGIN, MARGIN, width,
                            max(0, self.height - 2 * MARGIN - HINT_HEIGHT))
        self.hint.frame = (MARGIN, self.height - MARGIN - HINT_HEIGHT, width, HINT_HEIGHT)

    def touch_ended(self, touch):
        if self.on_close:
            self.on_close()
        else:
            self.window.close_sheet()
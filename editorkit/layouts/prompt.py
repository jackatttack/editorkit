"""prompt: ask for one line of text, as a sheet over the page.

    +----------------------------+
    | Rename find.py          ✕  |   title and close
    | [ find.py            ]  ✓  |   Field (Return or ✓ answers)
    +----------------------------+

✕ closes it with no answer. Used by: Files (rename).

    prompt = layouts.prompt(window)
    prompt.ask('Rename find.py', 'find.py', on_answer=lambda text: ...)
"""
import ui

from .. import native
from ..native.base import PADDING, ROW_HEIGHT, make_button


# --- Settings -------------------------------------------------------------

TITLE_FONT = ('<system-bold>', 15)
CLOSE_ICON = '✕'
ANSWER_ICON = '✓'


class Prompt(native.Tile):

    def __init__(self, window):
        native.Tile.__init__(self, window)
        self.background_color = self.palette.panel        # opaque: a sheet
        self.on_answer = None

        self.title = ui.Label(font=TITLE_FONT)
        self.title.text_color = self.palette.text
        self.title.touch_enabled = False
        self.add_subview(self.title)

        self.close_button = make_button(CLOSE_ICON, lambda sender: self.close(),
                                        self.palette)
        self.add_subview(self.close_button)

        self.field = native.Field(window, on_return=self.answered)
        self.field.add_button(ANSWER_ICON, self.answered)
        self.add_subview(self.field)

    def ask(self, title, value='', on_answer=None):
        self.title.text = title
        self.field.set_value(value)
        self.on_answer = on_answer
        self.window.show_sheet(self)
        self.field.focus()

    def answered(self, field, text=None):
        answer = self.field.value()
        callback = self.on_answer
        self.close()
        if callback:
            callback(answer)

    def close(self):
        self.on_answer = None
        self.field.unfocus()
        self.window.close_sheet()

    def layout(self):
        top = PADDING
        self.close_button.frame = (self.width - PADDING - ROW_HEIGHT, top,
                                   ROW_HEIGHT, ROW_HEIGHT)
        self.title.frame = (PADDING * 2, top,
                            max(0, self.close_button.x - PADDING * 3), ROW_HEIGHT)
        self.field.frame = (0, top + ROW_HEIGHT + PADDING, self.width, native.Field.HEIGHT)


def prompt(window):
    """A Prompt for window: ask(title, value, on_answer) lays it over the page."""
    return Prompt(window)
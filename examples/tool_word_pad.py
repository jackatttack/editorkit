"""Word pad: Python words to type, in the keyboard's place.

The finished tool from Lesson 7 (The keyboard's place): ek.Pair joins a
view over the code to its keys, built fresh by make_keys() whenever ⌨
calls them up. The view lists what you typed. Edit WORDS to make it yours.

ek.run_tool(main) keeps this script's names alive after it ends, so the
windows' callbacks (WordPad's methods) can use them.
"""
import editorkit as ek
from editorkit.web import cards, tiles

# --- Settings ------------------------------------------------------------------

WORDS = ['self', 'return ', 'def ', 'print()', 'True', 'False', 'None',
         'for ', ' in ', 'if ', 'elif ', 'else:', 'import ', 'lambda ', 'with ', 'try:']
KEY = 'example-word-pad'
TYPED_SHOWN = 16                # the last this many words stay on the view


def word_page():
    """Every word as a card; a tap types it."""
    page = cards.Page()
    page.grid([cards.Card(word.strip(), item=word) for word in WORDS], min_width=90)
    return page


class WordPad:

    def __init__(self):
        self.typed = []
        self.view = ek.Window('Word pad', emoji='🔤', key=KEY)
        self.view.add_page('Typed', 'Tap ⌨ for the words, then a word to type it.')

    def type_word(self, word):
        ek.insert(word)
        self.typed.append(word.strip())
        self.view.set_page_content('Typed', ' · '.join(self.typed[-TYPED_SHOWN:]))

    def make_keys(self):
        """The keys: a fresh window in the keyboard's place, each time ⌨ asks."""
        keys = ek.Window('Words', emoji='🔤', key=KEY + '-keys', home='dock')
        board = tiles.Cards(keys, on_pick=self.type_word, zoom_key=KEY,
                            dismiss_keyboard=False)
        keys.add_page('Words', board)
        board.show(word_page())
        return keys


def main():
    pad = WordPad()
    ek.Pair(pad.view, pad.make_keys).show()


ek.run_tool(main)

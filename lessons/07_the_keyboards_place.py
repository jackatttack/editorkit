"""Lesson 7: The keyboard's place.

Run this script. A window can sit where the keyboard goes and act as one:
here, a pad of Python words that types at the cursor. Then the pad becomes
the keys of a tool with ek.Pair.
"""
import editorkit as ek
from editorkit.web import cards, tiles
from editorkit.lessons import Lesson

lesson = Lesson("The keyboard's place", __file__)
WORDS = ['self', 'return ', 'def ', 'print()', 'True', 'False', 'None',
         'for ', ' in ', 'if ', 'import ', 'lambda ']
state = {}


def word_page():
    """A card per word; each card's item is the word it types."""
    page = cards.Page()
    page.grid([cards.Card(word.strip(), item=word) for word in WORDS], min_width=90)
    return page


@lesson.step("A window in the keyboard's place")
def dock_window():
    """Window(home='dock') lives where the keyboard goes. With the cursor
    in the code, a tap on a card types its word there, like a key.
    dismiss_keyboard=False keeps the pad up while you scroll it.

    Try it, then tap into the code and tap some words. – folds the pad."""
    window = lesson.new_window('Words', emoji='🔤', key='lesson-words', home='dock')
    board = tiles.Cards(window, on_pick=ek.insert, dismiss_keyboard=False)
    window.add_page('Words', board)
    board.show(word_page())
    window.show()


@lesson.step('A tool and its keys')
def pair():
    """ek.Pair(view, make_keys) makes one tool of two windows: the view
    over the code, and its keys in the keyboard's place, built fresh by
    make_keys() whenever ⌨ calls them up. Folding the keys leaves no pin:
    the view is the tool.

    Try it: tap words and watch the view list them. Fold the keys, then ⌨."""
    view = lesson.new_window('Typed', emoji='📝')
    view.add_page('Typed', 'Nothing typed yet.')
    typed = []

    def type_word(word):
        ek.insert(word)
        typed.append(word.strip())
        view.set_page_content('Typed', ' · '.join(typed[-12:]))

    def make_keys():
        keys = ek.Window('Words', emoji='🔤', key='lesson-pair-keys', home='dock')
        board = tiles.Cards(keys, on_pick=type_word, zoom_key='lesson-words',
                            dismiss_keyboard=False)
        keys.add_page('Words', board)
        board.show(word_page())
        return keys

    state['make_keys'] = make_keys
    ek.Pair(view, make_keys).show()


@lesson.step('A board above its pad')
def fill_above():
    """fill=True makes the view fill the space above its keys, the way a
    game board sits over its pad. Resize the view by hand and it keeps
    your size from then on.

    Try it: the view fills the screen above the words."""
    if 'make_keys' not in state:
        return 'Try step 2 first: it makes the keys.'
    view = lesson.new_window('Board', emoji='🎯')
    view.add_page('Board', 'I fill the space above the keys.')
    ek.Pair(view, state['make_keys'], fill=True).show()


lesson.run()

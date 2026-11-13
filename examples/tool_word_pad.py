"""Word pad: Python words to type, in the keyboard's place.

The finished tool from Lesson 7 (The keyboard's place): ek.Pair joins a
view over the code to its keys, built fresh by make_keys() whenever ⌨
calls them up. The view lists what you typed. Edit WORDS to make it yours.
"""
WORDS = ['self', 'return ', 'def ', 'print()', 'True', 'False', 'None',
         'for ', ' in ', 'if ', 'elif ', 'else:', 'import ', 'lambda ', 'with ', 'try:']


def main():
    # Pythonista clears a script's names when it ends, but these windows
    # live on: everything the callbacks use is local to main().
    import editorkit as ek
    from editorkit.web import cards, tiles

    words = list(WORDS)
    typed = []
    view = ek.Window('Word pad', emoji='🔤', key='example-word-pad')
    view.add_page('Typed', 'Tap ⌨ for the words, then a word to type it.')

    def word_page():
        page = cards.Page()
        page.grid([cards.Card(word.strip(), item=word) for word in words], min_width=90)
        return page

    def type_word(word):
        ek.insert(word)
        typed.append(word.strip())
        view.set_page_content('Typed', ' · '.join(typed[-16:]))

    def make_keys():
        keys = ek.Window('Words', emoji='🔤', key='example-word-pad-keys', home='dock')
        board = tiles.Cards(keys, on_pick=type_word, zoom_key='example-word-pad',
                            dismiss_keyboard=False)
        keys.add_page('Words', board)
        board.show(word_page())
        return keys

    ek.Pair(view, make_keys).show()


main()
"""Tab switcher: every open tab as a card; tap one to switch to it.

The finished tool from Lesson 6 (Tabs and files): ek.open_tabs and
ek.selected_tab draw the cards, ek.select_tab switches, and an
ek.on_change listener for 'file' keeps the cards up to date. Closing the
window removes the listener: a tool tidies up after itself.
"""


def main():
    # Pythonista clears a script's names when it ends, but this window lives
    # on: everything its callbacks use is local to main(), so they keep it.
    import os

    import editorkit as ek
    from editorkit.web import cards, tiles

    window = ek.Window('Tabs', emoji='🗂', key='example-tabs', size=(320, 360))
    board = tiles.Cards(window, on_pick=ek.select_tab, zoom_key='example-tabs')
    window.add_page('Tabs', board)

    def draw(event=None):
        showing = ek.selected_tab()
        page = cards.Page()
        page.grid([cards.Card(os.path.basename(path), item=path,
                              body=cards.text('● showing now' if path == showing
                                              else os.path.basename(os.path.dirname(path))))
                   for path in ek.open_tabs()], min_width=150)
        board.show(page)

    listener = ek.on_change(draw, kinds=['file'], key='example-tabs-watch')
    window.on('close', lambda _window: ek.remove_listener(listener))
    draw()
    window.show()


main()
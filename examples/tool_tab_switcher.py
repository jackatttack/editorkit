"""Tab switcher: every open tab as a card; tap one to switch to it.

The finished tool from Lesson 6 (Tabs and files): ek.open_tabs and
ek.selected_tab draw the cards, ek.select_tab switches, and an
ek.on_change listener for 'file' keeps the cards up to date. Closing the
window removes the listener: a tool tidies up after itself.

ek.run_tool(main) keeps this script's names alive after it ends, so the
window's callbacks can use them.
"""
import os

import editorkit as ek
from editorkit.web import cards, tiles

# --- Settings ------------------------------------------------------------------

KEY = 'example-tabs'
SIZE = (320, 360)


def tabs_page():
    """Every open tab as a card, the one showing marked."""
    showing = ek.selected_tab()
    page = cards.Page()
    page.grid([cards.Card(os.path.basename(path), item=path,
                          body=cards.text('● showing now' if path == showing
                                          else os.path.basename(os.path.dirname(path))))
               for path in ek.open_tabs()], min_width=150)
    return page


def main():
    window = ek.Window('Tabs', emoji='🗂', key=KEY, size=SIZE)
    board = tiles.Cards(window, on_pick=ek.select_tab, zoom_key=KEY)
    window.add_page('Tabs', board)
    listener = ek.on_change(lambda *_event: board.show(tabs_page()), kinds=['file'],
                            key=KEY + '-watch')
    window.on('close', lambda _window: ek.remove_listener(listener))
    board.show(tabs_page())
    window.show()


ek.run_tool(main)

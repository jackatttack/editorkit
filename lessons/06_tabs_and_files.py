"""Lesson 6: Tabs and files.

Run this script. You build a tab switcher: every open tab as a card, the
one showing marked, kept up to date as you switch. Then open a file at a
line, and show and hide the file browser.
"""
import os

import editorkit as ek
from editorkit.web import cards, tiles
from editorkit.lessons import Lesson

lesson = Lesson('Tabs and files', __file__)
LESSONS = os.path.dirname(os.path.abspath(__file__))
SIZE = (340, 380)
state = {}


def draw_tabs():
    """The switcher's page: a card per open tab, in the tab bar's order."""
    showing = ek.selected_tab()
    page = cards.Page()
    page.note('Tap a tab to switch to it.')
    page.grid([cards.Card(os.path.basename(path), item=path,
                          body=cards.text('● showing now' if path == showing
                                          else os.path.basename(os.path.dirname(path))))
               for path in ek.open_tabs()], min_width=150)
    state['board'].show(page)


@lesson.step('Every open tab')
def tab_switcher():
    """ek.open_tabs() is the path of every open tab, in the tab bar's
    order; ek.selected_tab() is the one showing; ek.select_tab(path)
    switches to it.

    Try it, then tap a card. 📜 in the lesson brings this file back."""
    window = ek.Window('Tabs', emoji='🗂', key='lesson-tabs', size=SIZE, owner=lesson.window)
    board = tiles.Cards(window, on_pick=ek.select_tab, zoom_key='lesson-tabs')
    window.add_page('Tabs', board)
    state.update(window=window, board=board)
    draw_tabs()
    window.show()
    return 'Showing %s.' % os.path.basename(ek.current_file() or '')


@lesson.step('Keep up with the tabs')
def follow_tabs():
    """ek.on_change(callback, kinds=['file']) calls back whenever the file
    showing changes. A key names the listener, so running this again
    replaces it instead of adding a second.

    Try it, then switch tabs any way you like: the switcher keeps up."""
    if 'board' not in state:
        return 'Try step 1 first: it opens the switcher.'
    state['watch'] = ek.on_change(lambda event: draw_tabs(), kinds=['file'],
                                  key='lesson-tabs-watch')
    return 'Watching the tabs.'


@lesson.step('Open a file at a line')
def open_at_line():
    """ek.open_file(path) opens a file in a tab. To land on a line too, use
    ek.Opener(window).go(path, line): it waits for the tab to show its text,
    selects the line and scrolls it into view.

    Try it: Lesson 1 opens at its first step."""
    if 'window' not in state:
        return 'Try step 1 first: the opener ticks on its window.'
    state['opener'] = ek.Opener(state['window'])     # kept: it ticks on the window's clock
    state['opener'].go(os.path.join(LESSONS, '01_windows.py'), 12)
    return 'Lesson 1 is open at line 12. 📜 brings this lesson back.'


@lesson.step('The file browser')
def file_browser():
    """ek.toggle_browser() shows or hides Pythonista's own file browser;
    ek.browser_visible() says which. show_browser and hide_browser are there
    when you know which you want.

    Try it twice: the browser comes, then goes."""
    state.setdefault('browser', ek.browser_visible())
    ek.toggle_browser()
    return 'The browser is %s.' % ('showing' if ek.browser_visible() else 'hidden')


@lesson.step('Put it back')
def put_back():
    """Stop watching the tabs, and leave the browser as it was before.

    Try it, then Done ✓ closes the switcher."""
    if 'watch' in state:
        ek.remove_listener(state.pop('watch'))
    if 'browser' in state:
        (ek.show_browser if state.pop('browser') else ek.hide_browser)()
    return 'Back to how it was.'


lesson.run()

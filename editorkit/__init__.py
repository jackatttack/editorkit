"""editorkit: script Pythonista's own editor from Python.

    import editorkit as ek

    ek.annotate(12, 'Test failed here', style='error')
    ek.highlight('TODO')
    ek.toolbar_button('⚡', action)
    ek.keyboard(keys=[...], second_row=[...])
    ek.pin(view, line=20)
    ek.float_view(view)
    ek.on_change(callback)
    ek.text(); ek.selection(); ek.select(10, 20); ek.replace(10, 20, 'x')
    ek.insert('print()'); ek.find_all('todo'); ek.replace_all('a', 'b')
    ek.open_tabs(); ek.selected_tab(); ek.select_tab(path); ek.open_file(path)
    ek.on_tab_pull(lambda path: ..., window)   # hold a tab, drag it down
    ek.tidy()                                  # lay open windows out evenly (again: undo)
    ek.show_browser()
    ek.use_theme('PythonistaDark'); ek.install_theme('My Theme', colours, scopes)

Everything acts on the script open in the editor right now, lasts until
Pythonista quits, and is safe to call from any thread. It works by reaching
Pythonista's own (private) classes through objc_util, so a Pythonista update
could change things. See README.md and docs/FINDINGS.txt.
"""
__version__ = '0.3.2'

from .annotations import STYLES, annotate, clear_annotations
from .browser import browser_visible, hide_browser, show_browser, toggle_browser
from .events import on_change, remove_listener, stop_events
from .highlight import clear_highlights, highlight
from .keyrow import keyboard, reset_keyboard
from .stores import store
from .script import (find_all, insert, replace, replace_all, reveal, select, selection,
                     text, visible_lines)
from .tabs import current_file, open_file, open_tabs, select_tab, selected_tab
from .tabpull import on_pull as on_tab_pull
from .themes import (current_theme, install_theme, refresh_theme, theme_colours,
                     theme_names, use_theme)
from .windows import Window, close_all as close_windows, live_windows, show
from .windows import stop as stop_windows
from .windows import tidy
from .wrench import add_wrench_action, remove_wrench_action, wrench_actions
from .windows.places import plain_keyboard
from .toolbar import clear_toolbar, remove_toolbar_button, toolbar_button
from .views import clear_views, float_view, pin, remove_view
from .job import Job
from .opener import Opener
from .pair import Pair
from .tiles.textbox import edit_text
from . import browse, clip, fileops, files, layouts, matches, tabpull, tiles
from . import web

# The core asks for HTML pages through a hook; the root wires the web
# package into it, so the core never imports it (the web fence).
from .windows import content as _content
_content.make_html_page = web.page_for_html
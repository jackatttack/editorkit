"""Script windows: a script shown as code over the editor, one per file.

📜 opens one for the open script. The page is the whole file, numbered and
coloured; tap a line to open the file there. ▶ runs it in the shared
Console (deck.console), so every script window's output comes to the one
Console. ✂️ brings Scissors up in the keyboard's place for this file, its
range tinted here; ⚡ opens Quick for it. Each file has its own window
(keyed by its path), so several can be open; minimised they wait in the
tray.

Files previews through script windows too (preview_window): one with its
home in the dock, swapping files in place (ScriptTool.set_path). When a
preview's ✂️ is tapped it tells Files first (on_own_keys), so it leaves
Files, then goes back to being the file's tab with the Scissors bar over it.

The view follows the file: while it is the open tab, the editor's text
(unsaved edits included); otherwise the file on disk. It is rechecked every
CHECK_SECONDS and redrawn only when it changed.

    from editorkit_toolbox import scriptview
    scriptview.open_script_window()            # the open script
    scriptview.open_script_window(path)
"""
import os
import time

import ui
import editorkit as ek
from editorkit import tiles
from editorkit.web import codeview
from editorkit.web import tiles as web_tiles

from . import console, runner


# --- Settings -------------------------------------------------------------

EMOJI = '📜'
KEY_PREFIX = 'deck.script:'      # + the file's real path: one window per file
RUN_ICON = '▶'
SCISSORS_ICON = '✂️'
QUICK_ICON = '⚡'
FIND_ICON = '🔍'                 # this script in the editor, with the Find bar
CHECK_SECONDS = 1.0              # how often the view looks for changes
MAX_LINES = 3000                 # longer files show this many, then say so
NO_FILE = 'Tap a file in Files to preview it here.'


# --- The tool -------------------------------------------------------------

class ScriptTool:

    def __init__(self, window, path, on_own_keys=None):
        self.window = window
        self.path = path
        self.on_own_keys = on_own_keys   # called once, before Scissors comes (Files' preview)
        self.shown_text = None       # the text on the page now
        self.tinted = None           # (first, last) lines Scissors is working on
        self.next_check = 0.0
        self.opener = ek.Opener(window)
        # Scrolling must not put the keyboard away: Scissors rides there as
        # this window's Pair keys, and hiding the keyboard would end them.
        self.code = web_tiles.Code(window, on_pick=self.line_picked, dismiss_keyboard=False)
        window.add_page('Code', self.code)
        window.add_button(RUN_ICON, lambda *_: self.run(), 'run')
        # ✂️: back to the file's tab with the Scissors bar over it.
        window.add_button(SCISSORS_ICON, lambda *_: self.to_scissors(), 'scissors')
        window.add_button(QUICK_ICON, lambda *_: self.open_quick(), 'quick')
        window.add_button(FIND_ICON, lambda *_: self.find_in_editor(), 'find')
        window.every(self.tick)
        self.refresh()

    def refresh(self, force=False):
        """Redraw if the script (or the tinted band) changed since last shown."""
        if not self.path:
            if self.shown_text is not None or self.next_check == 0.0 or force:
                self.code.say(NO_FILE)
            self.shown_text = None
            return
        text = console.script_text(self.path)
        if text is None:
            if self.shown_text is not None or self.next_check == 0.0 or force:
                self.code.say("Can't read %s." % runner.short_name(self.path))
            self.shown_text = None
            return
        if text == self.shown_text and not force:
            return
        self.shown_text = text
        self.code.set_section(codeview.preview_section(
            0, runner.short_name(self.path), text, python=self.path.endswith('.py'),
            limit=MAX_LINES, line_item=lambda number: number, tinted=self.tinted))

    def set_path(self, path):
        """Show another file in this window (Files' preview swaps in place)."""
        if path == self.path:
            return
        self.path = path
        self.tinted = None
        self.shown_text = None
        self.window.set_title(os.path.basename(path) if path else 'Preview')
        self.refresh(force=True)

    def run(self):
        if self.path:
            console.run_script(self.path)

    def to_scissors(self):
        """✂️: this file back as its tab, with the Scissors bar over it. The
        window goes (it was the tab's code view, as a drop into the tab row
        does); a Files preview tells Files first, and so leaves it."""
        if not self.path:
            return
        if self.on_own_keys is not None:
            leaving, self.on_own_keys = self.on_own_keys, None
            leaving(self.window)
        path = self.path
        self.window.close()
        ek.open_file(path)
        # During a tab switch there is a moment with no editor view; a top
        # bar shown then lands on the outgoing view and vanishes with it.
        # So the bar comes once the switch has settled.
        ui.delay(open_scissors_bar_now, SCISSORS_AFTER_TAB_SECONDS)

    def show_range(self, lines, focus=None):
        """Tint lines=(first, last) as Scissors' range (None: no band), and
        scroll to focus."""
        if lines == self.tinted and not focus:
            return
        self.tinted = lines
        self.refresh(force=True)
        if focus:
            self.code.set_current(focus)

    def tick(self, now=None):
        if time.time() < self.next_check:
            return
        self.next_check = time.time() + CHECK_SECONDS
        self.refresh()

    def open_quick(self):
        """⚡: Quick for this script (imported here: quick imports this module)."""
        if not self.path:
            return
        from . import quick
        quick.open_quick(self.path)

    def find_in_editor(self):
        """🔍: this script in the editor with the Find bar on it (compact
        search); this window folds to the tray."""
        if not self.path:
            return
        self.window.minimise()
        from . import find
        find.open_find(path=self.path)

    def show_line(self, line):
        """Scroll to line and ring it (None: leave the view as it is)."""
        if line:
            self.code.set_current(line)

    def line_picked(self, line):
        """A tapped line (its item is the line number): open the file there."""
        if not self.path:
            return
        self.code.set_current(line)
        self.opener.go(self.path, line)


# --- Opening --------------------------------------------------------------

SCISSORS_AFTER_TAB_SECONDS = 0.4   # ✂️: wait this long after the tab switch before the bar


def open_scissors_bar_now():
    """The Scissors bar over the (new) open tab; a failure prints, never vanishes."""
    try:
        from . import scissors_bar
        scissors_bar.open_scissors_bar()
    except Exception:
        import traceback
        print('deck: the Scissors bar did not open:')
        traceback.print_exc()


def window_key(path):
    return KEY_PREFIX + os.path.realpath(path)


def live_window(key):
    live = ek.live_windows()
    for window in (live.values() if hasattr(live, 'values') else live):
        if getattr(window, 'script_key', None) == key:
            return window
    return None


def back_to_tab(window, path):
    """A script window dropped into the tab row: it closes, and its file
    shows as a tab again (opening one if it was closed)."""
    window.close()
    ek.open_file(path)


def open_script_window(path=None, line=None):
    """Show path (default: the open script) in its own window, or bring its
    window back if it is already live; with line, scroll there and ring it.
    Returns the window, or None when there is no script."""
    path = path or ek.current_file()
    if not path or not os.path.isfile(path):
        return None
    key = window_key(path)
    window = live_window(key)
    if window is None:
        window = ek.Window(os.path.basename(path), emoji=EMOJI, key=key)
        # Dragged up into the tab row and let go: back to being its file's tab.
        window.on_tab_drop(lambda dropped, path=path: back_to_tab(dropped, path))
        window.script_key = key      # how live_window() finds it again
        window.script_tool = ScriptTool(window, path)
    window.show()
    window.script_tool.show_line(line)
    return window


def preview_window(path, key, on_own_keys=None):
    """A script window for Files' preview, not yet shown: home in the dock,
    under key (Files picks one no live window holds). on_own_keys(window)
    runs once, just before it brings its own keys."""
    window = ek.Window(os.path.basename(path) if path else 'Preview', emoji=EMOJI,
                       key=key, home='dock')
    window.script_key = key
    window.script_tool = ScriptTool(window, path, on_own_keys=on_own_keys)
    return window
"""Console: run code and watch its output, in one shared window.

A window over the code, showing a feed of cards (editorkit.web.tiles.Feed): each
run is a card titled with what ran, ⏳ while running, then ✓ ✗ or ■ with its
time. Earlier runs stay above as history (this session); 📋 copies a card,
▾ folds it, ✕ removes it, ⌫ clears them all.

▶ runs the open script as the editor holds it (unsaved edits included), or
only the selected lines when there is a selection. Script windows
(deck.scriptview) and Scissors run here too. ↻ runs the last thing again
(a whole script as it stands now). Output streams in: stdout plain, stderr
tinted. A traceback shows each frame's line; tap one to open the file
there. ■ stops the run (pure-Python loops; a long C call ends first).

Code the Console runs can call show(thing) with no import: a picture, a
figure, a table (a list of dicts), a dict, rows, a file path, HTML or text
is drawn in that run's card, in order with what it prints (editorkit.render).
Any tool can post a card of its own: console.show(thing, title).

The code runs on an ek.Job thread through deck.runner, which never touches
ui; output and show() arrive on the window's clock.

    from editorkit_toolbox import console
    console.open_console()           # the Console, shown
    console.run_script(path)         # run a file in the shared Console
    console.show(figure, 'Plot')     # a card in the shared Console
"""
import builtins
import os

import editorkit as ek
from editorkit import files, tiles
from editorkit.web import codeview
from editorkit.web.tiles import Feed

from . import runner


# --- Settings -------------------------------------------------------------

TITLE = 'Console'
EMOJI = '📟'
WINDOW_KEY = 'deck.console'
MAX_LINES = 2000                 # output rows shown per run; the rest are counted
RUN_ICON = '▶'
AGAIN_ICON = '↻'
STOP_ICON = '■'
CLEAR_ICON = '⌫'
READY_NOTE = '▶ runs the open script, or only the selected lines. ↻ runs the last again.'

# How each output stream shows (codeview row kinds).
KIND_FOR_STREAM = {'out': 'plain', 'err': 'error'}

# The last line of a run, by its status.
STATUS_WORDS = {'done': 'Finished in %.2f s',
                'error': 'Failed after %.2f s',
                'stopped': 'Stopped after %.2f s'}

WHOLE_SCRIPT = 'whole script'    # runner.pick_code's label for the whole file


Row = codeview.Row
MISSING = object()               # no builtin show() was there before a run


# --- Scripts --------------------------------------------------------------

def same_file(first, second):
    return (bool(first) and bool(second)
            and os.path.realpath(first) == os.path.realpath(second))


def script_text(path):
    """A script as it stands: the editor's text (unsaved edits included)
    while it is the open tab, else the file on disk; None if unreadable."""
    if same_file(ek.current_file(), path):
        return ek.text()
    return files.read_text(path)


# --- The tool -------------------------------------------------------------

class ConsoleTool:

    def __init__(self, window):
        self.window = window
        self.entry = None            # the newest run's card in the feed
        self.shown = 0               # output rows shown this run
        self.hidden = 0              # output rows past MAX_LINES, counted only
        self.stop_wanted = False
        self.again = None            # the last run's plan, for ↻
        self.opener = ek.Opener(window)
        self.job = ek.Job(window, self.work, on_items=self.lines_arrived,
                          on_done=self.finished, on_error=self.crashed)
        # Every run is a card; earlier runs stay above as history.
        self.feed = Feed(window, on_pick=self.picked)
        window.add_page('Output', self.feed)
        window.add_button(RUN_ICON, lambda *_: self.run(), 'run')
        window.add_button(AGAIN_ICON, lambda *_: self.run_again(), 'again')
        window.add_button(STOP_ICON, lambda *_: self.stop(), 'stop')
        window.add_button(CLEAR_ICON, lambda *_: self.clear(), 'clear')
        window.on('close', lambda _window: self.stop())
        self.feed.add(TITLE, [Row(READY_NOTE, 'note')])

    # --- What to run -------------------------------------------------------
    # Each run is a plan: a function giving (source, path, label). ↻ calls
    # the last plan again, so a whole script reruns as it now stands.

    def run(self):
        """▶: the selected lines, else the whole open script."""
        path = ek.current_file() or ''
        source, first_line, label = runner.pick_code(ek.text(), ek.selection())
        if label == WHOLE_SCRIPT and path:
            self.start(lambda: (script_text(path), path, WHOLE_SCRIPT))
        else:
            self.start(lambda: (source, path, label))

    def run_file(self, path):
        """A whole file (a script window's ▶)."""
        self.start(lambda: (script_text(path), path, WHOLE_SCRIPT))

    def run_part(self, path, start, end):
        """A range of a file (Scissors): its whole lines, dedented, line
        numbers kept; the whole file when start == end. ↻ reruns the same
        characters of the file as it then stands."""
        def plan():
            text = script_text(path)
            if text is None or start == end:
                return text, path, WHOLE_SCRIPT
            source, first_line, label = runner.pick_code(text, (start, end))
            return source, path, label
        self.start(plan)

    def run_again(self):
        if self.again is None:
            self.note('Nothing has run yet.')
            return
        self.start(self.again)

    # --- Running -----------------------------------------------------------

    def start(self, plan):
        """Run what plan() gives, as a new card. While a run is going, it
        waits for ■; after ■, a new run abandons one stuck in a long C call."""
        if self.job.running and not self.stop_wanted:
            self.note('Still running: ■ stops it.')
            return
        source, path, label = plan()
        if source is None:
            self.note("Can't read %s." % runner.short_name(path))
            return
        if not source.strip():
            self.note('Nothing to run.')
            return
        self.again = plan
        self.stop_wanted = False
        self.shown = self.hidden = 0
        name = os.path.basename(path) if path else runner.short_name(path)
        self.entry = self.feed.add('%s · %s' % (name, label), status='running')
        self.job.start(source, path)

    def work(self, run, source, path):
        """On the Job's thread: run the code, handing each line to run.put.
        While it runs, show(thing) is a builtin: what it is given goes to
        this run's card, in order with the printed lines."""
        def show(thing):
            run.put(('show', thing))
        saved = builtins.__dict__.get('show', MISSING)
        builtins.show = show
        try:
            return runner.run_source(
                source, path, run.put,
                should_stop=lambda: run.cancelled or self.stop_wanted)
        finally:
            if saved is MISSING:
                builtins.__dict__.pop('show', None)
            else:
                builtins.show = saved

    def stop(self):
        if self.job.running and not self.stop_wanted:
            self.stop_wanted = True
            self.note('Stopping…')

    # --- Showing -----------------------------------------------------------

    def lines_arrived(self, items):
        """This beat's output: printed lines as rows, show() things as parts
        of their own, in the order they came."""
        rows = []
        for stream, payload in items:
            if stream == 'show':
                self.add_rows(rows)
                rows = []
                if self.entry is not None:
                    self.entry.append(payload)
                continue
            if self.shown >= MAX_LINES:
                self.hidden += 1
                continue
            rows.append(Row(payload, KIND_FOR_STREAM.get(stream, 'plain')))
            self.shown += 1
        self.add_rows(rows)

    def finished(self, result):
        rows = []
        if self.hidden:
            rows.append(Row('… %d more lines not shown' % self.hidden, 'note'))
        rows.extend(result.rows)
        self.add_rows(rows)
        if self.entry is not None:
            words = STATUS_WORDS.get(result.status, '%.2f s') % result.seconds
            self.entry.finish(result.status, words)

    def crashed(self, text):
        """The runner itself failed (a console bug, not the script's)."""
        self.add_rows([Row(line, 'error') for line in text.rstrip().split('\n')])
        if self.entry is not None:
            self.entry.finish('error', 'the Console itself failed')

    def add_rows(self, rows):
        if rows and self.entry is not None:
            self.entry.append(rows)

    def note(self, text):
        """A note in the running card, else a small card of its own."""
        if self.entry is not None and self.entry.status == 'running':
            self.entry.append([Row(text, 'note')])
        else:
            self.feed.add(TITLE, [Row(text, 'note')])

    def clear(self):
        self.feed.clear()
        self.entry = None

    # --- Tapping -----------------------------------------------------------

    def picked(self, item):
        """A tapped thing that points at a file: a traceback frame (path,
        line), a Search hit (opened at the match), a name card, a ViewHit,
        or a Scissors line. Opens it in the editor there."""
        target = getattr(item, 'hit', item)                 # ViewHit -> its Hit
        if isinstance(target, tuple) and len(target) == 2 and isinstance(target[0], str):
            path, line = target
            self.feed.set_current(item)
            self.opener.go(path, line)
            return
        path = getattr(target, 'path', None)
        if not path:
            return
        self.feed.set_current(item)
        line = getattr(target, 'line', None)
        start, end = getattr(target, 'start', None), getattr(target, 'end', None)
        if line and start is not None and end is not None and end > start:
            self.opener.go(path, line, start, end)
        elif line:
            self.opener.go(path, line)
        else:
            self.opener.go(path)


# --- Opening --------------------------------------------------------------

def open_console():
    """Open the Console over the code (a new one replaces any other).
    Returns the tool (tool.window)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = ConsoleTool(window)
    window.console_tool = tool       # how shared() finds it again
    window.show()
    return tool


def shared():
    """The Console that is already live (shown or in the tray), else a new
    one. Everything runs through this one window."""
    live = ek.live_windows()
    for window in (live.values() if hasattr(live, 'values') else live):
        tool = getattr(window, 'console_tool', None)
        if tool is not None:
            return tool
    return open_console()


def run_script(path):
    """Run a whole file in the shared Console, bringing it into view."""
    tool = shared()
    tool.window.show()
    tool.run_file(path)


def run_part(path, start, end):
    """Run part of a file (characters start..end, as whole lines) in the
    shared Console, bringing it into view."""
    tool = shared()
    tool.window.show()
    tool.run_part(path, start, end)


def show(thing, title=None):
    """A card of its own in the shared Console, bringing it into view:
    anything editorkit.render takes. Returns the card (append to it, or
    finish it with a status)."""
    tool = shared()
    tool.window.show()
    return tool.feed.add(title or 'Shown', thing)

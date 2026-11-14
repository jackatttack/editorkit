"""Walkthrough: live UI checks, step by step, with a person watching.

    from editorkit.walkthrough import Step, Walkthrough
    Walkthrough('regression', [
        Step('Open Find', do=open_find, settle=1.2,
             check=lambda c: [('This file mode', c['find'].in_file, True)],
             ask='Is Find open over the code?'),
    ]).start()

A small 🧪 window at the top of the code runs each step: do(context), then
after settle seconds check(context), which looks at state only and returns
(label, actual, expected) tuples, each logged PASS or FAIL. If the step
asks something, the question waits for the person watching: ✓, ✗ (then a
note) or ↷ to skip. ⏸ pauses between steps. Steps share context, a dict.

Everything goes to scratch/ui_checks/<name>_<time>.txt, with
editorkit.trace switched on for the run so breadcrumbs land beside the
steps. A step with where='console' asks from over the console.
"""
import os
import time
import traceback

import ui

from . import layouts, native, trace
from .windows import Window


# --- Settings -------------------------------------------------------------

LOG_FOLDER = os.path.expanduser('~/Documents/scratch/ui_checks')
SETTLE_SECONDS = 0.8         # default wait between a step's action and its check
NEXT_SECONDS = 0.3           # pause before the next step starts
TITLE = 'UI check'
EMOJI = '🧪'
WINDOW_KEY = 'ui-check'
SIZE = (0, 170)
TEXT_FONT = ('<system>', 15)
MARKS = {'pass': '✓', 'fail': '✗', 'skip': '↷'}


class Step:

    def __init__(self, name, do=None, check=None, ask=None, settle=SETTLE_SECONDS,
                 where='editor'):
        self.name = name
        self.do = do                 # do(context): the action
        self.check = check           # check(context) -> [(label, actual, expected)]
        self.ask = ask               # a yes/no question for the person, or None
        self.settle = settle         # seconds between do and check
        self.where = where           # 'editor' or 'console': where to ask from


class Board(native.Tile):
    """The runner's page: the step and what it asks."""

    def __init__(self, window):
        native.Tile.__init__(self, window)
        self.label = ui.Label(font=TEXT_FONT)
        self.label.number_of_lines = 0
        self.label.text_color = self.palette.text
        self.add_subview(self.label)

    def set_text(self, text):
        self.label.text = text

    def layout(self):
        self.label.frame = (12, 4, max(0, self.width - 24), max(0, self.height - 8))


class Walkthrough:

    def __init__(self, name, steps):
        self.name = name
        self.steps = list(steps)
        self.context = {}
        self.index = -1
        self.waiting = None          # (step, auto checks failed) while a question waits
        self.note_for = None         # the step whose ✗ note is being asked for
        self.paused = False
        self.resume_wanted = False
        self.counts = {'pass': 0, 'fail': 0, 'skip': 0, 'error': 0}
        self.log_path = os.path.join(LOG_FOLDER, '%s_%s.txt'
                                     % (name, time.strftime('%Y%m%d_%H%M%S')))
        self.trace_was = trace.ENABLED

        self.window = Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, home='top_bar',
                             size=SIZE, dockable=False)
        self.board = Board(self.window)
        self.window.add_page('Check', self.board)
        self.window.add_button('✓', lambda window: self.answer('pass'), name='pass')
        self.window.add_button('✗', lambda window: self.answer('fail'), name='fail')
        self.window.add_button('↷', lambda window: self.answer('skip'), name='skip')
        self.window.add_button('⏸', lambda window: self.toggle_pause(), name='pause')
        self.prompt = layouts.prompt(self.window)

    # --- Running ------------------------------------------------------------

    def start(self):
        os.makedirs(LOG_FOLDER, exist_ok=True)
        trace.ENABLED = True
        self.log('=== %s: %d steps ===' % (self.name, len(self.steps)))
        self.board.set_text('Starting %s…' % self.name)
        self.window.show()
        self.window.after(0.6, lambda now: self.next())
        return self

    def next_soon(self):
        self.window.after(NEXT_SECONDS, lambda now: self.next())

    def next(self):
        if self.paused:
            self.resume_wanted = True
            return
        self.index += 1
        if self.index >= len(self.steps):
            self.finish()
            return
        step = self.steps[self.index]
        self.board.set_text('%s  %s…' % (self.number(), step.name))
        self.log('step %s: %s' % (self.number(), step.name))
        try:
            if step.do:
                step.do(self.context)
        except Exception:
            self.log_error('do')
            self.counts['error'] += 1
            self.next_soon()
            return
        self.window.after(step.settle, lambda now, step=step: self.check(step))

    def check(self, step):
        failed = False
        if step.check:
            try:
                results = step.check(self.context) or []
            except Exception:
                self.log_error('check')
                results, failed = [], True
            if results is True or results is False:
                results = [('check', results, True)]
            for label, actual, wanted in results:
                ok = actual == wanted
                failed = failed or not ok
                self.log('  %s %s: %r (expected %r)'
                         % ('PASS' if ok else 'FAIL', label, actual, wanted))
        if step.ask:
            self.waiting = (step, failed)
            self.bring_forward(step)
            self.board.set_text('%s  %s\n%s' % (self.number(), step.name, step.ask))
            self.log('  asked: %s' % step.ask)
            return
        self.counts['fail' if failed else 'pass'] += 1
        self.next_soon()

    def number(self):
        return '%d/%d' % (self.index + 1, len(self.steps))

    def bring_forward(self, step):
        """Ask from where the person is looking: over the console, or at the
        top of the code (moving there again brings the window to the front)."""
        window = self.window
        if step.where == 'console':
            if window.place != 'console':
                window.to_console()
        elif window.place == 'console':
            window.to_panel()
        elif window.place in ('pin', 'tray'):
            window.show()
        else:
            window.move_to('top_bar', keyboard=False)

    # --- Answers ------------------------------------------------------------

    def answer(self, verdict):
        if self.note_for is not None:
            # ✗'s note prompt was closed without a note: ↷ carries on.
            if verdict == 'skip':
                step, self.note_for = self.note_for, None
                self.window.close_sheet()
                self.record(step, 'fail', '(no note)', False)
            return
        if self.waiting is None:
            return
        step, failed = self.waiting
        self.waiting = None
        if verdict == 'fail':
            self.note_for = step
            self.prompt.ask('What did you see?', '', on_answer=self.noted)
            return
        self.record(step, verdict, '', failed)

    def noted(self, note):
        step, self.note_for = self.note_for, None
        if step is not None:
            self.record(step, 'fail', note, False)

    def record(self, step, verdict, note, auto_failed):
        self.log('  you: %s%s' % (MARKS[verdict], (': ' + note) if note else ''))
        if verdict == 'pass' and auto_failed:
            verdict = 'fail'             # the state was wrong, whatever it looked like
        self.counts[verdict] += 1
        self.next_soon()

    def toggle_pause(self):
        self.paused = not self.paused
        self.window.set_button('pause', on=self.paused)
        if not self.paused and self.resume_wanted:
            self.resume_wanted = False
            self.next_soon()

    # --- The end ------------------------------------------------------------

    def finish(self):
        summary = ('%(pass)d passed, %(fail)d failed, %(skip)d skipped, %(error)d errors'
                   % self.counts)
        self.log('=== done: %s ===' % summary)
        trace.ENABLED = self.trace_was
        self.board.set_text('Done: %s\nLog: scratch/ui_checks/%s'
                            % (summary, os.path.basename(self.log_path)))
        self.bring_forward(Step('end'))

    # --- The log ------------------------------------------------------------

    def log(self, text):
        line = '%s %s\n' % (time.strftime('%H:%M:%S'), text)
        try:
            with open(self.log_path, 'a', encoding='utf-8') as handle:
                handle.write(line)
        except OSError:
            pass
        trace.note('check', text[:80])

    def log_error(self, stage):
        self.log('  ERROR in %s:\n%s' % (stage, traceback.format_exc()))
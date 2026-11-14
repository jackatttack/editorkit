"""Lessons: scripts that teach by running over their own code.

    import editorkit as ek
    from editorkit.lessons import Lesson

    lesson = Lesson('Windows', __file__)

    @lesson.step('A window over your code')
    def hello():
        \"\"\"The explanation: shown on the step's card.\"\"\"
        ek.show('Hello', key='lesson-hello')

    lesson.run()

Running the script opens a lesson window over the editor, a card page per
step: the docstring, the step's code, and what happened when it was tried.
▶ Try it runs the step; ◀ and Next ▶ move between steps; 📜 brings the
step's code into view. On every step the lesson shows its own file in the
editor, selects that step's function and puts a banner on its first line,
so the window and the code it explains sit together. Done ✓ closes the
lesson, its banner, and the windows it opened (keys starting 'lesson-').

Pythonista clears a script's names when it finishes, but the steps run
later: run() keeps a copy of the script's names and each step runs
against that copy, so steps use ek and friends as written.
step_spans, line_range and step_page are pure (tests/smoke_lessons.py).
"""
import ast
import contextlib
import io
import inspect
import os
import sys
import textwrap
import traceback
import types
from collections import namedtuple

from .web import cards, prose


# --- Settings -------------------------------------------------------------

WINDOW_KEY = 'editorkit-lesson'
EMOJI = '🎓'
SIZE = (380, 380)                # the lesson window's first size
OPEN_DELAY = 0.8                 # seconds for the editor to switch to the lesson's tab
CLEANUP_PREFIX = 'lesson-'       # Done closes windows whose keys start with this
RESULT_LIMIT = 600               # characters of a returned value shown
CANCELLED_WORDS = 'Cancelled: a dialog raises KeyboardInterrupt when you tap Cancel.'
RUNNING_WORDS = ('This step runs on a background thread, so dialogs and waits can show. '
                 'What it returns appears here.')

Step = namedtuple('Step', 'title function background docs')
Step.__new__.__defaults__ = (False, None)
Span = namedtuple('Span', 'first last code')   # first line (decorator), last line, body


# --- Pure -------------------------------------------------------------------

def is_docstring(node):
    return (isinstance(node, ast.Expr) and isinstance(getattr(node, 'value', None), ast.Constant)
            and isinstance(node.value.value, str))


def step_spans(source, names):
    """{function name: Span} for the module-level functions named: the line
    the step starts on (its decorator), its last line, and its body without
    the docstring, dedented."""
    lines = source.split('\n')
    spans = {}
    for node in ast.parse(source).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in names:
            continue
        first = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        start = node.body[0].lineno
        if is_docstring(node.body[0]):
            start = node.body[0].end_lineno + 1
        code = textwrap.dedent('\n'.join(lines[start - 1:node.end_lineno])).strip('\n')
        spans[node.name] = Span(first, node.end_lineno, code)
    return spans


def line_range(text, first, last):
    """(start, end) character indices of lines first..last (1-based) in text."""
    from .script import lines_in
    return lines_in(text, first, last)


def paragraphs_html(doc):
    """A docstring as paragraphs of card text (single line breaks joined)."""
    parts = [' '.join(part.split()) for part in (doc or '').split('\n\n')]
    return ''.join('<p>%s</p>' % cards.text(part) for part in parts if part)


def run_captured(function):
    """Call function, catching what it prints: (outcome, printed). outcome
    is None, ('value', text) or ('error', traceback text). A dialog's Cancel
    (KeyboardInterrupt) is an outcome too, not a crash."""
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            value = function()
    except KeyboardInterrupt:
        outcome = ('value', CANCELLED_WORDS)
    except Exception:
        outcome = ('error', traceback.format_exc(limit=4))
    else:
        outcome = None if value is None else ('value', str(value)[:RESULT_LIMIT])
    return outcome, printed.getvalue()[:RESULT_LIMIT]


def step_page(lesson_title, index, count, title, doc, code, outcome=None, printed='', docs=None):
    """The page for one step, in the docs' look (editorkit.web.prose): the
    title, the docstring, the step's code (with ⧉ Copy), then what happened.
    printed is what the step printed ('' for nothing); outcome is None,
    ('value', text) or ('error', traceback text)."""
    page = cards.Page()
    page.heading('%s · step %d of %d' % (lesson_title, index + 1, count))
    blocks = [prose.heading(title, 2), prose.text(doc or '')]
    if code:
        blocks.append(prose.code(code))
    if printed:
        blocks.append(prose.callout('It printed', prose.code(printed, python=False)))
    if outcome is not None:
        kind, words = outcome
        if kind == 'running':
            blocks.append(prose.note(RUNNING_WORDS, '⏳ Running'))
        elif kind == 'error':
            blocks.append(prose.callout('⚠️ It raised an error',
                                        prose.code(words, python=False), kind='danger'))
        else:
            blocks.append(prose.note(words, 'It returned', 'tip'))
    page.prose(*blocks)
    last = index + 1 >= count
    extras = [cards.Action('📜 Show me in the code', ('code',), look='quiet')]
    if docs:
        extras.append(cards.Action('📖 Read the docs', ('docs', docs), look='quiet'))
    page.buttons([[cards.Action('◀ Back', ('back',), look='quiet' if index == 0 else None),
                   cards.Action('▶ Try it', ('try',), look='go'),
                   cards.Action('Done ✓' if last else 'Next ▶', ('next',))],
                  extras])
    return page


# --- The lesson ---------------------------------------------------------------

class Lesson:

    def __init__(self, title, path, emoji=EMOJI):
        self.title = title
        self.path = os.path.abspath(path)
        self.emoji = emoji
        self.steps = []
        self.index = 0
        self.outcome = None
        self.printed = ''
        self.banner_line = None      # the line holding the lesson's own banner, if any
        self.spans = {}
        self.namespace = {}
        self.window = None
        self.board = None
        self.job = None              # runs background steps (made on first use)
        self.running_index = None    # the step a background run belongs to

    def step(self, title, background=False, docs=None):
        """Decorator: the function is the next step, titled title.

        background=True runs it on a background thread (an ek.Job) for
        anything that waits or must not run on the main thread: dialogs,
        input, sleeps, downloads. The card shows ⏳ until it returns.
        docs='ui.Button' adds 📖 Read the docs, opening Explain's Docs tab
        at that entry (when Toolbox is installed)."""
        def add(function):
            self.steps.append(Step(title, function, background, docs))
            return function
        return add

    def show_view(self, view, title='View', key=None, **options):
        """view (any ui.View, a scene.SceneView too) as the page of a lesson
        window, so the code stays in sight beside it. Owned by the lesson, so
        Done closes it. Returns the window.

            lesson.show_view(button_demo, 'Buttons')
        """
        window = self.new_window(title, key=key, **options)
        window.add_page(title, view)
        window.show()
        return window

    def new_window(self, title, key=None, **options):
        """A window for a step: owned by the lesson (folding the lesson takes
        it along, Done closes it) and keyed from its title, so trying the
        step again replaces it instead of adding another. Takes everything
        ek.Window does.

            window = lesson.new_window('Hello', emoji='👋')

        (lesson.window, with no call, is the lesson's own window.)
        """
        import editorkit as ek
        key = key or 'lesson-' + '-'.join(title.lower().split())
        return ek.Window(title, key=key, owner=self.window, **options)

    def run(self):
        """Open the lesson window at the first step (call at the end of the
        lesson script)."""
        import editorkit as ek
        from .web import tiles
        self.namespace = dict(sys._getframe(1).f_globals)
        with open(self.path, encoding='utf-8') as handle:
            source = handle.read()
        self.spans = step_spans(source, [step.function.__name__ for step in self.steps])
        self.window = ek.Window(self.title, emoji=self.emoji, key=WINDOW_KEY, size=SIZE,
                                on_close=self.closed)
        self.board = tiles.Cards(self.window, on_pick=self.picked, zoom_key='lesson')
        self.window.add_page('Lesson', self.board)
        self.window.show()
        self.go(0)

    # --- Steps ------------------------------------------------------------

    def go(self, index):
        self.index = index
        self.outcome = None
        self.printed = ''
        self.draw()
        self.mark()

    def draw(self):
        step = self.steps[self.index]
        span = self.spans.get(step.function.__name__)
        page = step_page(self.title, self.index, len(self.steps), step.title,
                         inspect.getdoc(step.function), span.code if span else '',
                         self.outcome, getattr(self, 'printed', ''), step.docs)
        self.board.show(page)

    def picked(self, item):
        kind = item[0] if isinstance(item, tuple) and item else None
        if kind == 'back':
            self.go(max(0, self.index - 1))
        elif kind == 'next':
            if self.index + 1 >= len(self.steps):
                self.window.close()
            else:
                self.go(self.index + 1)
        elif kind == 'try':
            self.try_step()
        elif kind == 'code':
            self.mark()
        elif kind == 'docs':
            self.open_docs(item[1])

    def try_step(self):
        """Run the step against the script's names, as they were at run().
        What it prints is caught for the step's page ("It printed"), since the
        console is hidden behind the lesson. A background step runs on the
        lesson's Job and its page shows ⏳ until it returns."""
        step = self.steps[self.index]
        if self.job is not None and self.job.running:
            return                   # one background run at a time
        original = step.function
        function = types.FunctionType(original.__code__, self.namespace, original.__name__,
                                      original.__defaults__, original.__closure__)
        if not step.background:
            self.show_result(run_captured(function))
            return
        self.running_index = self.index
        self.outcome, self.printed = ('running', ''), ''
        self.draw()
        self.background_job().start(function)

    def background_job(self):
        if self.job is None:
            import editorkit as ek
            self.job = ek.Job(self.window, lambda run, function: run_captured(function),
                              on_done=self.background_done, on_error=self.background_failed)
        return self.job

    def background_done(self, result):
        """A background step finished: show it if its step is still showing."""
        if self.running_index == self.index:
            self.show_result(result)

    def background_failed(self, text):
        if self.running_index == self.index:
            self.show_result((('error', text), ''))

    def show_result(self, result):
        self.outcome, self.printed = result
        self.draw()

    def open_docs(self, entry):
        """📖: Explain's Docs tab at entry. The docs come with Toolbox, so a
        lesson run without it says so instead."""
        try:
            from editorkit_toolbox import docs
        except ImportError:
            self.show_result((('value', 'Read the docs for %s in Pythonista\'s own help.' % entry),
                              ''))
            return
        docs.open_docs([entry])

    # --- In the editor ----------------------------------------------------------

    def mark(self):
        """Show the step's code: the lesson's file, the step selected and in
        view, a banner on its first line."""
        import editorkit as ek
        span = self.spans.get(self.steps[self.index].function.__name__)
        if span is None:
            return
        current = ek.current_file() or ''
        if os.path.realpath(current) != os.path.realpath(self.path):
            ek.open_file(self.path)
            self.window.after(OPEN_DELAY, lambda *_args: self.mark_now(span))
            return
        self.mark_now(span)

    def mark_now(self, span):
        import editorkit as ek
        self.clear_banner()
        self.banner_line = span.first
        ek.annotate(span.first, 'Step %d of %d: %s' % (
            self.index + 1, len(self.steps), self.steps[self.index].title), style='note')
        start, end = line_range(ek.text(), span.first, span.last)
        ek.select(start, end, scroll=False)
        ek.reveal(start)

    def clear_banner(self):
        """Take away the lesson's own banner: only that note, so the reader's
        notes stay, and only while the lesson's file is the one showing."""
        import editorkit as ek
        line, self.banner_line = self.banner_line, None
        if line is None:
            return
        if os.path.realpath(ek.current_file() or '') == os.path.realpath(self.path):
            ek.remove_annotation(line)

    def closed(self, *_args):
        """Done or ✕: clear the banner, close the windows the lesson opened."""
        import editorkit as ek
        self.clear_banner()
        for window in ek.live_windows():
            if str(getattr(window, 'key', '')).startswith(CLEANUP_PREFIX):
                window.close()
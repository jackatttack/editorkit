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
import inspect
import os
import sys
import textwrap
import traceback
import types
from collections import namedtuple

from .web import cards


# --- Settings -------------------------------------------------------------

WINDOW_KEY = 'editorkit-lesson'
EMOJI = '🎓'
SIZE = (380, 380)                # the lesson window's first size
OPEN_DELAY = 0.8                 # seconds for the editor to switch to the lesson's tab
CLEANUP_PREFIX = 'lesson-'       # Done closes windows whose keys start with this
RESULT_LIMIT = 600               # characters of a returned value shown

Step = namedtuple('Step', 'title function')
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
    lines = text.split('\n')
    start = sum(len(line) + 1 for line in lines[:first - 1])
    end = sum(len(line) + 1 for line in lines[:last]) - 1
    return start, max(start, min(end, len(text)))


def paragraphs_html(doc):
    """A docstring as paragraphs of card text (single line breaks joined)."""
    parts = [' '.join(part.split()) for part in (doc or '').split('\n\n')]
    return ''.join('<p>%s</p>' % cards.text(part) for part in parts if part)


def step_page(lesson_title, index, count, title, doc, code, outcome=None):
    """The card page for one step. outcome is None, ('value', text) or
    ('error', traceback text)."""
    page = cards.Page()
    page.heading('%s · step %d of %d' % (lesson_title, index + 1, count))
    grid = [cards.Card(title, None, paragraphs_html(doc))]
    if code:
        grid.append(cards.Card('The code', None, cards.code(code)))
    if outcome is not None:
        kind, words = outcome
        if kind == 'error':
            grid.append(cards.Card('⚠️ It raised an error', None, cards.code(words),
                                   '#FF5A5F'))
        else:
            grid.append(cards.Card('It returned', None, cards.text(words), '#62D26F'))
    page.grid(grid)
    last = index + 1 >= count
    page.buttons([[cards.Action('◀ Back', ('back',), look='quiet' if index == 0 else None),
                   cards.Action('▶ Try it', ('try',), look='go'),
                   cards.Action('Done ✓' if last else 'Next ▶', ('next',))],
                  cards.Action('📜 Show me in the code', ('code',), look='quiet')])
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
        self.spans = {}
        self.namespace = {}
        self.window = None
        self.board = None

    def step(self, title):
        """Decorator: the function is the next step, titled title."""
        def add(function):
            self.steps.append(Step(title, function))
            return function
        return add

    def run(self):
        """Open the lesson window at the first step (call at the end of the
        lesson script)."""
        import editorkit as ek
        from . import tiles
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
        self.draw()
        self.mark()

    def draw(self):
        step = self.steps[self.index]
        span = self.spans.get(step.function.__name__)
        page = step_page(self.title, self.index, len(self.steps), step.title,
                         inspect.getdoc(step.function), span.code if span else '',
                         self.outcome)
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

    def try_step(self):
        """Run the step against the script's names, as they were at run()."""
        original = self.steps[self.index].function
        function = types.FunctionType(original.__code__, self.namespace, original.__name__,
                                      original.__defaults__, original.__closure__)
        try:
            value = function()
        except Exception:
            self.outcome = ('error', traceback.format_exc(limit=4))
        else:
            self.outcome = None if value is None else ('value', str(value)[:RESULT_LIMIT])
        self.draw()

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
        ek.clear_annotations()
        ek.annotate(span.first, 'Step %d of %d: %s' % (
            self.index + 1, len(self.steps), self.steps[self.index].title), style='note')
        start, end = line_range(ek.text(), span.first, span.last)
        ek.select(start, end, scroll=False)
        ek.reveal(start)

    def closed(self, *_args):
        """Done or ✕: clear the banner, close the windows the lesson opened."""
        import editorkit as ek
        ek.clear_annotations()
        live = ek.live_windows()
        for window in list(live.values() if hasattr(live, 'values') else live):
            if str(getattr(window, 'key', '')).startswith(CLEANUP_PREFIX):
                window.close()
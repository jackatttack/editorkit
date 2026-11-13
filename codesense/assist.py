"""Tier 2: slow analysis on one background thread.

jedi (0.9, shipped with Pythonista) for completions, call signatures and
definitions; pyflakes for lint. Measured warm: completions 5-45 ms,
signatures and definitions 6-13 ms. A cold first call took about 860 ms on a
4000-line file, which is why this never runs on the main thread.

    assistant = Assistant()
    assistant.start()
    assistant.request('complete', version, text, position)    # UTF-16 caret
    ...later, from a clock tick...
    answer = assistant.take('complete', version)               # None until ready

Only the newest request of each kind is kept. Every answer carries the
caller's version (a counter or a text hash); take() drops an answer whose
version is not the one asked for, so a stale answer never reaches the
screen. Python threads cannot be cancelled: an answer slower than its
budget is still delivered, marked late. A text that made jedi recurse
forever is skipped from then on.
"""
import ast
import importlib
import threading
import time

from . import units
from .suggest import Suggestion
from .timing import Ledger

# ---- Settings (editable) ----------------------------------------------------
KINDS = ('complete', 'signature', 'definition', 'lint')
BUDGET_MS = {'complete': 150, 'signature': 100, 'definition': 100, 'lint': 400}
MAX_COMPLETIONS = 60
IDLE_WAIT_SECONDS = 0.5


class Answer(object):
    """The result of one request.

    items         Suggestions (complete); dicts with name, params and index
                  (signature); dicts with name, path, line and description
                  (definition); dicts with line, column and message (lint)
    error         None, or what went wrong
    late          True when it took longer than its budget
    """
    __slots__ = ('kind', 'version', 'items', 'error', 'milliseconds', 'late')

    def __init__(self, kind, version, items, error, milliseconds, late):
        self.kind = kind
        self.version = version
        self.items = items
        self.error = error
        self.milliseconds = milliseconds
        self.late = late

    def __repr__(self):
        state = 'error %s' % self.error if self.error else '%d items' % len(self.items)
        return 'Answer(%s v%r, %s, %.0f ms%s)' % (
            self.kind, self.version, state, self.milliseconds, ', late' if self.late else '')


def _load(module_name):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


class Assistant(object):
    def __init__(self, ledger=None, use_jedi=True, use_pyflakes=True):
        self.ledger = ledger if ledger is not None else Ledger()
        self.jedi = _load('jedi') if use_jedi else None
        self.pyflakes_checker = _load('pyflakes.checker') if use_pyflakes else None
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.pending = {}            # kind -> newest request
        self.answers = {}            # kind -> newest answer
        self.jedi_failed = set()     # hashes of texts jedi recursed forever on
        self.running = False
        self.thread = None

    # ---- Lifecycle ----

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name='codesense-assistant')
        self.thread.daemon = True
        self.thread.start()

    def stop(self, wait_seconds=1.0):
        self.running = False
        self.wake.set()
        if self.thread is not None:
            self.thread.join(wait_seconds)
            self.thread = None

    # ---- Asking and collecting ----

    def request(self, kind, version, text, position=0, path=None):
        if kind not in KINDS:
            raise ValueError('unknown kind %r' % kind)
        with self.lock:
            self.pending[kind] = {'kind': kind, 'version': version, 'text': text,
                                  'position': position, 'path': path}
        self.wake.set()

    def take(self, kind, version=None):
        """The newest answer for kind, removed; None if there is none yet, or
        if it is for a different version (it is dropped)."""
        with self.lock:
            answer = self.answers.pop(kind, None)
        if answer is not None and version is not None and answer.version != version:
            return None
        return answer

    def wait(self, kind, version=None, timeout_seconds=5.0):
        """Block until the answer arrives. For tests and scripts; never call
        this on the main thread."""
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with self.lock:
                answer = self.answers.get(kind)
            if answer is not None and (version is None or answer.version == version):
                return self.take(kind)
            time.sleep(0.02)
        return None

    # ---- The worker ----

    def _run(self):
        while self.running:
            self.wake.wait(IDLE_WAIT_SECONDS)
            self.wake.clear()
            while self.running:
                with self.lock:
                    if not self.pending:
                        break
                    kind = next(iter(self.pending))
                    request = self.pending.pop(kind)
                answer = self._answer(request)
                with self.lock:
                    self.answers[kind] = answer

    def _answer(self, request):
        kind = request['kind']
        start = time.perf_counter()
        items, error = [], None
        try:
            items = self._lint(request) if kind == 'lint' else self._jedi(request)
        except RecursionError as problem:
            self.jedi_failed.add(hash(request['text']))
            error = 'RecursionError: %s' % problem
        except Exception as problem:
            error = '%s: %s' % (type(problem).__name__, problem)
        milliseconds = (time.perf_counter() - start) * 1000
        self.ledger.record(kind, milliseconds)
        return Answer(kind, request['version'], items, error, milliseconds,
                      milliseconds > BUDGET_MS.get(kind, 200))

    def _jedi(self, request):
        if self.jedi is None:
            raise RuntimeError('jedi is not available')
        text = request['text']
        if hash(text) in self.jedi_failed:
            raise RuntimeError('jedi recursed forever on this text before; skipped')
        index = units.to_python(text, request['position'])
        line = units.line_number(text, index)
        column = index - (text.rfind('\n', 0, index) + 1)
        script = self.jedi.Script(text, line, column, request['path'])
        kind = request['kind']
        if kind == 'complete':
            return [Suggestion(found.name, getattr(found, 'type', ''),
                               getattr(found, 'description', ''), 'jedi')
                    for found in script.completions()[:MAX_COMPLETIONS]]
        if kind == 'signature':
            return [{'name': signature.name,
                     'params': [param.name for param in signature.params],
                     'index': getattr(signature, 'index', None)}
                    for signature in script.call_signatures()]
        return [{'name': found.name,
                 'path': str(found.module_path) if found.module_path else None,
                 'line': found.line,
                 'description': getattr(found, 'description', '')}
                for found in script.goto_definitions()]

    def _lint(self, request):
        if self.pyflakes_checker is None:
            raise RuntimeError('pyflakes is not available')
        try:
            tree = ast.parse(request['text'])
        except SyntaxError as error:
            return [{'line': error.lineno or 0, 'column': error.offset or 0,
                     'message': 'syntax error: %s' % error.msg}]
        checker = self.pyflakes_checker.Checker(tree, request['path'] or '<editor>')
        items = [{'line': message.lineno, 'column': getattr(message, 'col', 0),
                  'message': message.message % message.message_args}
                 for message in checker.messages]
        items.sort(key=lambda item: (item['line'], item['column']))
        return items
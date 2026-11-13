"""Running code for the mini console, on a Job's thread, never touching ui.

    source, first_line, label = runner.pick_code(ek.text(), ek.selection())
    result = runner.run_source(source, path, run.put, should_stop)

pick_code chooses what to run: the selected lines (whole lines, dedented),
or the whole script. Blank lines go in front of a selection, so a traceback
names the script's own line numbers.

run_source compiles and runs the code as path's __main__ on the calling
thread. Output from THIS thread only goes to put(('out' | 'err', line)),
one call per line; prints from any other thread go where they always did.
should_stop() is checked on every line of the script's own frames, so Stop
ends a pure-Python endless loop. It cannot interrupt a long C call such as
time.sleep(600) until that call returns.

The result is Result(status, seconds, rows): status 'done', 'error' or
'stopped'; rows are codeview Rows for a traceback, with item=(path, line)
on each frame that is a real file, so a tap can open it.

Limits (first version): a fresh namespace per run; input() is not wired
up; threads the script starts print to the normal console.
"""
import builtins
import contextlib
import linecache
import os
import sys
import textwrap
import threading
import time
import traceback
from collections import namedtuple

from editorkit.web.codeview import Row


# --- Settings -------------------------------------------------------------

CONSOLE_NAME = '<console>'       # the file name of code with no saved path
DOCUMENTS = os.path.expanduser('~/Documents')


# --- Internals ------------------------------------------------------------

RUNNER_FILE = os.path.realpath(__file__)
Result = namedtuple('Result', 'status seconds rows')
_routing_lock = threading.Lock()


class Stopped(BaseException):
    """Raised inside the running code when Stop is tapped. A BaseException,
    so the script's own 'except Exception' cannot swallow it."""


# --- What to run ----------------------------------------------------------

def pick_code(text, selection):
    """(source, first_line, label) for ▶: the selected lines, whole and
    dedented, or the whole script when nothing is selected."""
    text = text or ''
    if not selection or len(selection) < 2 or selection[0] == selection[1]:
        return text, 1, 'whole script'
    start, end = sorted(selection[:2])
    line_start = text.rfind('\n', 0, start) + 1
    if text[end - 1:end] == '\n':
        line_end = end                       # selection ends at a line's end
    else:
        newline = text.find('\n', end)
        line_end = len(text) if newline == -1 else newline + 1
    block = textwrap.dedent(text[line_start:line_end])
    first = text.count('\n', 0, line_start) + 1
    last = first + block.rstrip('\n').count('\n')
    label = 'line %d' % first if first == last else 'lines %d-%d' % (first, last)
    return '\n' * (first - 1) + block, first, label


def short_name(path):
    """A path as the console names it: relative to Documents when inside."""
    if not path or not os.path.isabs(path):
        return path or CONSOLE_NAME
    try:
        relative = os.path.relpath(path, DOCUMENTS)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith('..') else relative


# --- Running --------------------------------------------------------------

def run_source(source, path, put, should_stop=lambda: False):
    """Run source as path's __main__ on this thread. See the module notes."""
    filename = path or CONSOLE_NAME
    out = LineSplitter(put, 'out')
    err = LineSplitter(put, 'err')
    started = time.time()
    status, rows = 'done', []
    namespace = {'__name__': '__main__', '__file__': filename,
                 '__builtins__': builtins}
    with lines_known(filename, source):
        try:
            code = compile(source, filename, 'exec')
        except SyntaxError as error:
            return Result('error', time.time() - started, syntax_rows(error, filename))
        with captured(out, err), script_folder(path):
            sys.settrace(stopper(filename, should_stop))
            try:
                exec(code, namespace)
            except Stopped:
                status = 'stopped'
            except SystemExit as exit:
                if exit.code not in (None, 0):
                    rows = [Row('SystemExit: %s' % exit.code, 'note')]
            except BaseException as error:
                status = 'error'
                rows = traceback_rows(error)
            finally:
                sys.settrace(None)
                out.flush_rest()
                err.flush_rest()
    return Result(status, time.time() - started, rows)


def stopper(filename, should_stop):
    """A trace function that raises Stopped in the script's own frames once
    should_stop() is true. Other modules' frames are not traced (speed)."""
    def local(frame, event, arg):
        if should_stop():
            raise Stopped()
        return local

    def global_trace(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None
        if should_stop():
            raise Stopped()
        return local
    return global_trace


class LineSplitter:
    """A stream that hands each complete line to put((stream, line))."""

    def __init__(self, put, stream):
        self.put = put
        self.stream = stream
        self.partial = ''

    def write(self, text):
        text = str(text)
        pieces = (self.partial + text).split('\n')
        self.partial = pieces.pop()
        for line in pieces:
            self.put((self.stream, line.rstrip('\r')))
        return len(text)

    def flush(self):
        pass

    def flush_rest(self):
        if self.partial:
            self.put((self.stream, self.partial.rstrip('\r')))
            self.partial = ''


class StreamRouter:
    """Stands in for sys.stdout or sys.stderr while a run is going: writes
    from a routed thread go to that run, every other write to the stream it
    replaced."""

    def __init__(self, original):
        self.original = original
        self.routes = {}             # thread ident -> LineSplitter

    def write(self, text):
        route = self.routes.get(threading.get_ident())
        if route is None:
            return self.original.write(text)
        return route.write(text)

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self.original, name)


@contextlib.contextmanager
def captured(out, err):
    """Route this thread's stdout and stderr to out and err. The last run to
    finish puts the original streams back, unless something else has
    replaced them since."""
    ident = threading.get_ident()
    routers = []
    with _routing_lock:
        for name, target in (('stdout', out), ('stderr', err)):
            current = getattr(sys, name)
            if type(current).__name__ != 'StreamRouter':
                current = StreamRouter(current)
                setattr(sys, name, current)
            current.routes[ident] = target
            routers.append((name, current))
    try:
        yield
    finally:
        with _routing_lock:
            for name, router in routers:
                router.routes.pop(ident, None)
                if not router.routes and getattr(sys, name) is router:
                    setattr(sys, name, router.original)


@contextlib.contextmanager
def lines_known(filename, source):
    """Let tracebacks show the text that ran (unsaved edits included), not
    the file on disk. mtime None keeps linecache.checkcache off it."""
    previous = linecache.cache.get(filename)
    linecache.cache[filename] = (len(source), None, source.splitlines(True), filename)
    try:
        yield
    finally:
        if previous is None:
            linecache.cache.pop(filename, None)
        else:
            linecache.cache[filename] = previous


@contextlib.contextmanager
def script_folder(path):
    """Run from the script's folder, with it on sys.path, as Pythonista does.
    The working directory is shared by every thread: it is put back after."""
    folder = os.path.dirname(path) if path and os.path.isabs(path) else ''
    old_cwd = os.getcwd()
    added = bool(folder) and folder not in sys.path
    if folder and os.path.isdir(folder):
        os.chdir(folder)
    if added:
        sys.path.insert(0, folder)
    try:
        yield
    finally:
        if added and folder in sys.path:
            sys.path.remove(folder)
        try:
            os.chdir(old_cwd)
        except OSError:
            pass


# --- Tracebacks as rows ---------------------------------------------------

def frame_item(filename, line):
    """What a tap on a frame hands back: (path, line), or None when the
    frame is not a real file (code with no saved path)."""
    if line and os.path.isfile(filename):
        return (filename, line)
    return None


def traceback_rows(error):
    """The error as Rows: one note and one code row per frame (the runner's
    own frames left out), then the error itself."""
    frames = [frame for frame in traceback.extract_tb(error.__traceback__)
              if os.path.realpath(frame.filename) != RUNNER_FILE]
    rows = [Row('Traceback (most recent call last)', 'heading')]
    for frame in frames:
        rows.append(Row('%s, in %s' % (short_name(frame.filename), frame.name), 'note'))
        rows.append(Row(frame.line or '', 'code',
                        frame_item(frame.filename, frame.lineno), frame.lineno))
    for line in traceback.format_exception_only(type(error), error):
        for part in line.rstrip('\n').split('\n'):
            rows.append(Row(part, 'error'))
    return rows


def syntax_rows(error, filename):
    """A SyntaxError as Rows: where, the line (tappable), and the message."""
    rows = [Row('%s, line %s' % (short_name(filename), error.lineno), 'note')]
    if error.text:
        rows.append(Row(error.text.rstrip('\n'), 'code',
                        frame_item(filename, error.lineno), error.lineno))
    rows.append(Row('%s: %s' % (type(error).__name__, error.msg), 'error'))
    return rows
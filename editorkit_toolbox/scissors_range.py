"""The Scissors range as pure functions: no ui, no editor.

A range is (start, end) in Python character indices into the script's
text, start <= end. Lines are 1-based. tests/smoke_scissors.py checks
every function here.
"""
import bisect


# --- Settings -------------------------------------------------------------

EDGE_CHARS = 12                  # characters shown at each end of the range
NEWLINE_MARK = '⏎'
TAB_MARK = '→'


# --- Lines ----------------------------------------------------------------

def line_starts(text):
    """The index where each line starts; a final newline starts an empty
    last line."""
    starts = [0]
    for index, char in enumerate(text):
        if char == '\n':
            starts.append(index + 1)
    return starts


def line_at(text, index):
    """The 1-based line holding index."""
    return bisect.bisect_right(line_starts(text), index)


def range_lines(text, start, end):
    """(first, last) lines the range covers. A range ending just after a
    newline ends on that line, not the next."""
    first = line_at(text, start)
    last_index = end - 1 if end > start and text[end - 1:end] == '\n' else end
    return first, line_at(text, max(start, last_index))


def lines_range(text, first, last):
    """(start, end) covering whole lines first..last, the last line's newline
    included. Lines are clamped to the script and put in order."""
    starts = line_starts(text)
    count = len(starts)
    first, last = sorted((first, last))
    first = min(max(first, 1), count)
    last = min(max(last, 1), count)
    end = starts[last] if last < count else len(text)
    return starts[first - 1], end


# --- Nudging --------------------------------------------------------------

def nudge(start, end, which, delta, length):
    """Move one end by delta characters: which is 'top' or 'bottom'. An end
    never passes the other end or leaves the text."""
    if which == 'top':
        start = min(max(0, start + delta), end)
    else:
        end = max(min(length, end + delta), start)
    return start, end


def clamp(start, end, length):
    """A range kept inside text of length (after the script got shorter)."""
    start = min(max(0, start), length)
    return start, min(max(start, end), length)


# --- Showing --------------------------------------------------------------

def shown(part):
    return part.replace('\n', NEWLINE_MARK).replace('\t', TAB_MARK)


def edges(text, start, end, size=EDGE_CHARS):
    """(head, tail): the range's first and last characters, newlines and
    tabs made visible. A short range is all head, with tail ''."""
    part = text[start:end]
    if len(part) <= 2 * size:
        return shown(part), ''
    return shown(part[:size]), shown(part[-size:])


def describe(text, start=None, end=None):
    """One line about the range, or about the whole script when start is None."""
    if start is None:
        lines = text.count('\n') + (1 if text and not text.endswith('\n') else 0)
        return 'Whole script · %d lines · %d chars' % (lines, len(text))
    first, last = range_lines(text, start, end)
    where = 'line %d' % first if first == last else 'lines %d–%d' % (first, last)
    return '%s · %d chars' % (where, end - start)
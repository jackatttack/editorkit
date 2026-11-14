"""Scissors' moves as pure functions: no ui, no editor.

A selection is (start, end) in Python character indices into the script's
text, start <= end; start == end is a bare cursor. Lines are 1-based.

    mode(text, start, end)        'word' or 'lines': what the arrows do
    hop(text, start, end, way)    word mode: the word left, right, above, below
    grow(text, start, end)        cursor -> word -> whole line -> one more line
    shrink(text, start, end)      the other way, when there is no history
    word_at(text, index)          the word at the cursor (reset)
    paste(text, start, end, piece)  where a paste goes, re-indented

tests/smoke_scissors_moves.py checks every function here.
"""
import re
import textwrap

# --- Settings -------------------------------------------------------------

WORD = re.compile(r'[A-Za-z0-9_]+')      # what counts as a word to hop between


# --- Lines ----------------------------------------------------------------

def line_bounds(text, index):
    """(start, end) of the line holding index, without its newline."""
    start = text.rfind('\n', 0, index) + 1
    end = text.find('\n', index)
    return start, (len(text) if end == -1 else end)


def lines_of(text, start, end):
    """(first, last) lines the selection touches. A selection ending just
    after a newline stops on that line, unless the next line is empty: then
    it is that empty line it ends on (grow selects blank lines that way)."""
    first = text.count('\n', 0, start) + 1
    last = text.count('\n', 0, end) + 1
    if end > start and text[end - 1] == '\n' and end < len(text) and text[end] != '\n':
        last -= 1
    return first, max(first, last)


def line_span(text, first, last):
    """(start, end) of lines first..last, without the last line's newline
    (what the editor selects for whole lines)."""
    lines = text.split('\n')
    first = max(1, min(first, len(lines)))
    last = max(first, min(last, len(lines)))
    start = sum(len(line) + 1 for line in lines[:first - 1])
    end = start + sum(len(line) + 1 for line in lines[first - 1:last]) - 1
    return start, max(start, end)


def indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def words(text):
    return [(match.start(), match.end()) for match in WORD.finditer(text)]


# --- Mode -----------------------------------------------------------------

def mode(text, start, end):
    """'lines' when the selection covers a whole line (its indent to its
    end) or runs over more than one; else 'word'."""
    if end <= start:
        return 'word'
    if '\n' in text[start:end].rstrip('\n'):
        return 'lines'
    line_start, line_end = line_bounds(text, start)
    first_char = line_start + len(indent_of(text[line_start:line_end]))
    return 'lines' if start <= first_char and end >= line_end else 'word'


# --- Words ----------------------------------------------------------------

def word_at(text, index):
    """The word holding or touching index; else the nearest on its line
    (the next one first); else the bare cursor (index, index)."""
    line_start, line_end = line_bounds(text, index)
    found = [word for word in words(text) if line_start <= word[0] and word[1] <= line_end]
    for word in found:
        if word[0] <= index <= word[1]:
            return word
    after = [word for word in found if word[0] > index]
    if after:
        return after[0]
    return found[-1] if found else (index, index)


def near(text, line_start, line_end, column):
    """The word on a line closest to column (the cursor there if none)."""
    target = min(line_start + column, line_end)
    found = [word for word in words(text) if line_start <= word[0] and word[1] <= line_end]
    if not found:
        return target, target
    for word in found:
        if word[0] <= target <= word[1]:
            return word
    return min(found, key=lambda word: abs(word[0] - target))


def hop(text, start, end, way):
    """Word mode: the next word 'left', 'right', 'up' or 'down'. Up and down
    keep the column and skip blank lines. At an edge, nothing moves."""
    if way == 'right':
        later = [word for word in words(text) if word[0] >= end and word != (start, end)]
        return later[0] if later else (start, end)
    if way == 'left':
        before = [word for word in words(text) if word[1] <= start and word != (start, end)]
        return before[-1] if before else (start, end)
    line_start, line_end = line_bounds(text, start)
    column = start - line_start
    if way == 'up':
        probe = line_start - 1
        while probe >= 0:
            above_start, above_end = line_bounds(text, probe)
            if text[above_start:above_end].strip():
                return near(text, above_start, above_end, column)
            probe = above_start - 1
        return start, end
    probe = line_end + 1
    while probe <= len(text):
        below_start, below_end = line_bounds(text, probe)
        if text[below_start:below_end].strip():
            return near(text, below_start, below_end, column)
        if below_end >= len(text):
            break
        probe = below_end + 1
    return start, end


# --- Growing and shrinking ------------------------------------------------

def grow(text, start, end):
    """One step out: a cursor or part of a word becomes the word; a word (or
    any part of a line) becomes the whole line; lines take one more line.
    At the end of the script nothing changes."""
    if mode(text, start, end) == 'lines':
        first, last = lines_of(text, start, end)
        if last >= text.count('\n') + 1:
            return start, end
        return line_span(text, first, last + 1)
    word = word_at(text, start)
    has_word = word[1] > word[0]
    if end == start and has_word:
        return word
    if has_word and word[0] <= start and end <= word[1] and (start, end) != word:
        return word
    first, _ = lines_of(text, start, end)
    return line_span(text, first, first)


def shrink(text, start, end):
    """One step in, for when grow left no history: lines lose their last
    line; one line becomes its first word; a word becomes the cursor."""
    if mode(text, start, end) == 'lines':
        first, last = lines_of(text, start, end)
        if last > first:
            return line_span(text, first, last - 1)
        line_start, line_end = line_bounds(text, start)
        return word_at(text, line_start + len(indent_of(text[line_start:line_end])))
    return start, start


# --- Pasting --------------------------------------------------------------

def reindent(block, indent):
    return '\n'.join(indent + line if line.strip() else '' for line in block.split('\n'))


def paste(text, start, end, piece):
    """(start, end, replacement, (new start, new end)) for a paste.

    One line replaces the selection as it is. Several lines are re-indented:
    they replace selected lines at the first line's indent; at a cursor or
    word they go on the line below, at its line's indent (on a blank line,
    on that line)."""
    if '\n' not in piece.strip('\n'):
        line = piece.strip('\n')
        return start, end, line, (start, start + len(line))
    block = textwrap.dedent(piece.strip('\n'))
    if mode(text, start, end) == 'lines':
        first, last = lines_of(text, start, end)
        span_start, span_end = line_span(text, first, last)
        first_end = line_bounds(text, span_start)[1]
        new = reindent(block, indent_of(text[span_start:first_end]))
        return span_start, span_end, new, (span_start, span_start + len(new))
    line_start, line_end = line_bounds(text, start)
    line = text[line_start:line_end]
    if line.strip():
        new = '\n' + reindent(block, indent_of(line))
        return line_end, line_end, new, (line_end + 1, line_end + len(new))
    new = reindent(block, line)
    return line_start, line_end, new, (line_start, line_start + len(new))
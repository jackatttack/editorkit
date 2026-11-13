"""Line operations for compact Scissors: pure text in, text out.

Every operation takes the script's text and a 1-based, inclusive line range
(first, last) and returns (new_text, (first, last)): where those same lines
are afterwards, so the band stays on them and a second press carries on
(↑ ↑ ↑ walks a block up three lines).

No ui and no Pythonista imports: apps/deck/tests/smoke_lineops.py checks it
headless.
"""


# --- Settings -------------------------------------------------------------

INDENT = '    '
COMMENT = '#'


# --- Lines and characters -----------------------------------------------------

def split_lines(text):
    return text.split('\n')


def real_count(lines):
    """Lines that hold text: the empty line after a final newline does not count."""
    if len(lines) > 1 and lines[-1] == '':
        return len(lines) - 1
    return len(lines)


def line_of(text, index):
    """The 1-based line holding character index."""
    return text.count('\n', 0, max(0, index)) + 1


def clamp(text, first, last):
    """first..last kept inside the script, last never before first."""
    count = real_count(split_lines(text))
    first = max(1, min(first, count))
    last = max(first, min(last, count))
    return first, last


def span(text, first, last):
    """(start, end) characters of lines first..last, without the last
    line's newline (what the editor selects)."""
    lines = split_lines(text)
    start = sum(len(line) + 1 for line in lines[:first - 1])
    end = start + sum(len(line) + 1 for line in lines[first - 1:last]) - 1
    return start, max(start, end)


def changed_span(old, new):
    """The smallest edit turning old into new: (start, end in old, the
    replacement). Editing only this keeps the editor's undo tidy."""
    limit = min(len(old), len(new))
    head = 0
    while head < limit and old[head] == new[head]:
        head += 1
    tail = 0
    while tail < limit - head and old[len(old) - 1 - tail] == new[len(new) - 1 - tail]:
        tail += 1
    return head, len(old) - tail, new[head:len(new) - tail]


# --- Operations ---------------------------------------------------------------

def move(text, first, last, step):
    """Lines first..last past their neighbour: step -1 up, +1 down. At the
    top or bottom nothing changes."""
    lines = split_lines(text)
    count = real_count(lines)
    top, bottom = first - 1, last            # lines[top:bottom] is the block
    if (step < 0 and top == 0) or (step > 0 and bottom >= count):
        return text, (first, last)
    block = lines[top:bottom]
    if step < 0:
        lines[top - 1:bottom] = block + [lines[top - 1]]
    else:
        lines[top:bottom + 1] = [lines[bottom]] + block
    return '\n'.join(lines), (first + step, last + step)


def duplicate(text, first, last):
    """A copy of the lines just below them; the copy becomes the range."""
    lines = split_lines(text)
    block = lines[first - 1:last]
    lines[last:last] = block
    size = last - first + 1
    return '\n'.join(lines), (last + 1, last + size)


def delete(text, first, last):
    """The lines gone; the range becomes the line now in their place."""
    lines = split_lines(text)
    del lines[first - 1:last]
    new_text = '\n'.join(lines or [''])
    line = clamp(new_text, first, first)[0]
    return new_text, (line, line)


def indent(text, first, last):
    lines = split_lines(text)
    for index in range(first - 1, last):
        if lines[index].strip():
            lines[index] = INDENT + lines[index]
    return '\n'.join(lines), (first, last)


def dedent(text, first, last):
    lines = split_lines(text)
    for index in range(first - 1, last):
        line = lines[index]
        if line.startswith('\t'):
            lines[index] = line[1:]
        else:
            spaces = len(line) - len(line.lstrip(' '))
            lines[index] = line[min(spaces, len(INDENT)):]
    return '\n'.join(lines), (first, last)


def toggle_comment(text, first, last):
    """Comment the lines (at their shallowest indent), or uncomment them
    when every line with words is already a comment. Blank lines stay."""
    lines = split_lines(text)
    body = [index for index in range(first - 1, last) if lines[index].strip()]
    if not body:
        return text, (first, last)
    if all(lines[index].lstrip().startswith(COMMENT) for index in body):
        for index in body:
            line = lines[index]
            pad = len(line) - len(line.lstrip())
            rest = line[pad + len(COMMENT):]
            if rest.startswith(' '):
                rest = rest[1:]
            lines[index] = line[:pad] + rest
    else:
        column = min(len(lines[index]) - len(lines[index].lstrip()) for index in body)
        for index in body:
            lines[index] = lines[index][:column] + COMMENT + ' ' + lines[index][column:]
    return '\n'.join(lines), (first, last)


# --- Blocks ---------------------------------------------------------------------

def _indent_of(line):
    return len(line) - len(line.lstrip())


def _opens_block(line):
    return line.rstrip().endswith(':')


def block_around(text, line, outer=False):
    """(first, last) of the block holding line, by indentation: a line that
    opens a block (ends in ':') is its own header, otherwise the nearest
    header above with less indent. Decorators above the header come too;
    trailing blank lines do not. outer=True skips the line's own block, to
    widen to the one around it. No header: (line, line)."""
    lines = split_lines(text)
    count = real_count(lines)
    line = max(1, min(line, count))
    start = line - 1
    while start > 0 and not lines[start].strip():
        start -= 1
    if outer or not _opens_block(lines[start]):
        base = _indent_of(lines[start])
        above = start - 1
        while above >= 0 and (not lines[above].strip()
                              or _indent_of(lines[above]) >= base
                              or not _opens_block(lines[above])):
            above -= 1
        if above < 0:
            return (line, line)
        start = above
    head = _indent_of(lines[start])
    end = start
    below = start + 1
    while below < count and (not lines[below].strip() or _indent_of(lines[below]) > head):
        if lines[below].strip():
            end = below
        below += 1
    while (start > 0 and lines[start - 1].strip().startswith('@')
           and _indent_of(lines[start - 1]) == head):
        start -= 1
    return (start + 1, end + 1)
"""Matches in text: marks for the code view, and replacing one or all.

Pure Python, so tests/smoke_matches.py checks it headless. Works line by
line (a match never spans lines), with a compiled pattern from
editorkit.files.make_pattern. Columns are Python indices within a line.

    marks = matches.marks_in(text, pattern, replacement='pear')
    hits = matches.hits_from_marks(marks)
    new_text, count = matches.replace_all(text, pattern, 'pear')
    spot = matches.replacement_at(text, pattern, line, start, end, 'pear')
"""
import re


def replacement_for(match, replacement, regex=False):
    """What one match becomes: the text as given, or with regex on, with
    its groups filled in (\\1)."""
    if not regex:
        return replacement
    try:
        return match.expand(replacement)
    except (re.error, IndexError):
        return replacement


def marks_in(text, pattern, replacement=None, regex=False):
    """{line: [(start, end)]} for every match, or with a replacement
    [(start, end, new)] to preview it. Empty matches are skipped."""
    marks = {}
    for number, line in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(line):
            if match.end() == match.start():
                continue
            mark = (match.start(), match.end())
            if replacement is not None:
                mark += (replacement_for(match, replacement, regex),)
            marks.setdefault(number, []).append(mark)
    return marks


def hits_from_marks(marks, index=0):
    """[(index, line, start, end)] in reading order: what ◀ ▶ step through."""
    return [(index, line, mark[0], mark[1]) for line in sorted(marks) for mark in marks[line]]


def replace_all(text, pattern, replacement, regex=False):
    """(new text, how many replaced), keeping every line ending as it was."""
    count = [0]

    def swap(match):
        if match.end() == match.start():
            return match.group(0)
        count[0] += 1
        return replacement_for(match, replacement, regex)

    out = []
    for line in text.splitlines(True):
        body = line.rstrip('\r\n')
        out.append(pattern.sub(swap, body) + line[len(body):])
    return ''.join(out), count[0]


def replacement_at(text, pattern, line, start, end, replacement, regex=False):
    """(begin, finish, new) in text's indices for the match at line, start..end,
    or None when that match is no longer there (the text moved)."""
    lines = text.splitlines(True)
    if not 1 <= line <= len(lines):
        return None
    body = lines[line - 1].rstrip('\r\n')
    match = pattern.match(body, start)
    if match is None or match.end() != end:
        return None
    line_start = sum(len(part) for part in lines[:line - 1])
    return (line_start + start, line_start + end, replacement_for(match, replacement, regex))
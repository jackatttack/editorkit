"""Positions. The editor counts UTF-16 units; Python counts characters.
codesense takes and returns UTF-16 positions and converts at the edges.
ASCII text (most code) takes a fast path: the two counts are the same."""


def utf16_length(text):
    return len(text) if text.isascii() else len(text.encode('utf-16-le')) // 2


def to_python(text, position):
    """The Python index for a UTF-16 position. Only the text up to the
    position is looked at: those characters hold at least that many units."""
    prefix = text[:position]
    if prefix.isascii():
        return len(prefix)
    data = prefix.encode('utf-16-le')[:position * 2]
    return len(data.decode('utf-16-le', errors='ignore'))


def to_utf16(text, index):
    """The UTF-16 position for a Python index."""
    return utf16_length(text[:index])


def line_bounds(text, index):
    """(start, end) Python indices of the line holding index; end excludes
    the newline."""
    start = text.rfind('\n', 0, index) + 1
    end = text.find('\n', index)
    return start, (len(text) if end < 0 else end)


def line_number(text, index):
    """The 1-based line holding a Python index."""
    return text.count('\n', 0, index) + 1
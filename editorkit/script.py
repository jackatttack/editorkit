"""The open script's text by Python index: read it, select, replace, insert
and find. Pythonista's editor counts UTF-16 units; these functions convert
inside, so emoji and other wide characters never shift a position. Every
public function is safe to call from any thread.

    source = ek.text()
    start, end = ek.selection()            # equal when it is just the cursor
    ek.select(10, 20)                      # and scroll to it
    ek.replace(10, 20, 'new')
    ek.insert('print()')                   # at the cursor, over any selection
    for start, end in ek.find_all('todo'):
        ...
    ek.replace_all('colour', 'color', whole_word=True)

The lower layer, editing.py, works in UTF-16 units on the main thread.
"""
import re

import editor as pythonista_editor
from objc_util import NSRange, ObjCClass

from . import _app


# Never leave the buffer truly empty: suspected to crash Pythonista (the
# Editor Deck's finding, 2026-11-02). Emptying the script leaves one newline.
EMPTY_SCRIPT = '\n'


# --- Positions (pure) -----------------------------------------------------

def utf16_length(text):
    return len(text.encode('utf-16-le')) // 2


def utf16_offset(text, index):
    """The editor position of Python character index in text."""
    return utf16_length(text[:index])


def python_index(text, offset):
    """The Python character index of editor position offset in text."""
    units = 0
    for index, character in enumerate(text):
        if units >= offset:
            return index
        units += 2 if ord(character) > 0xFFFF else 1
    return len(text)


def find_all(term, source=None, case_sensitive=False, whole_word=False, regex=False):
    """[(start, end)] Python index ranges of every match of term, in order.
    source defaults to the open script. A bad regex finds nothing."""
    if not term:
        return []
    if source is None:
        source = text()
    pattern = term if regex else re.escape(term)
    if whole_word:
        pattern = r'\b(?:%s)\b' % pattern
    try:
        compiled = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
    except re.error:
        return []
    return [(match.start(), match.end()) for match in compiled.finditer(source)
            if match.end() > match.start()]


# --- The open script ------------------------------------------------------

@_app.on_main
def text():
    """The open script's whole text as the editor holds it, saved or not;
    '' when no script is open."""
    view = _app.text_view()
    if view is not None:
        return str(view.text())
    try:
        return pythonista_editor.get_text() or ''
    except Exception:
        return ''


@_app.on_main
def selection():
    """(start, end) of the selection in Python indices, equal when it is just
    the cursor; None when no script is open."""
    try:
        chosen = pythonista_editor.get_selection()
    except Exception:
        return None
    if not chosen:
        return None
    source = text()
    return python_index(source, chosen[0]), python_index(source, chosen[1])


@_app.on_main
def select(start, end=None, scroll=True):
    """Select start..end (Python indices); end None puts the cursor at start."""
    source = text()
    end = start if end is None else end
    pythonista_editor.set_selection(utf16_offset(source, start),
                                    utf16_offset(source, end), scroll=scroll)


@_app.on_main
def reveal(index, top=60):
    """Scroll the code so the line holding index (a Python index) sits near
    the top of the text view, top points below its upper edge, so a window
    resting over the lower part of the code never hides it."""
    from objc_util import CGPoint
    view = _app.text_view()
    if view is None:
        return
    source = text()
    position = view.positionFromPosition_offset_(view.beginningOfDocument(),
                                                 utf16_offset(source, index))
    if position is None:
        return
    caret = view.caretRectForPosition_(position)
    inset = view.contentInset()
    highest = -inset.top
    lowest = max(highest, view.contentSize().height - view.bounds().size.height
                 + inset.bottom)
    wanted = max(highest, min(caret.origin.y - top, lowest))
    view.setContentOffset_animated_(CGPoint(view.contentOffset().x, wanted), True)


@_app.on_main
def visible_lines():
    """(first, last): the 1-based lines of the open script showing in the
    code view now (a line cut off at an edge counts). Lines under a window
    resting over the code count too. None when no script is showing."""
    from objc_util import CGPoint
    view = _app.text_view()
    if view is None:
        return None
    source = text()
    inset = view.contentInset()
    offset = view.contentOffset()
    height = view.bounds().size.height
    top = offset.y + inset.top
    bottom = offset.y + height - inset.bottom - 1
    return (_line_at(view, source, CGPoint(0, top)),
            _line_at(view, source, CGPoint(0, max(top, bottom))))


def lines_in(source, first, last):
    """(start, end) character indices of lines first..last (1-based,
    inclusive) in source. Pure: the rule behind line_range."""
    lines = source.split('\n')
    start = sum(len(line) + 1 for line in lines[:first - 1])
    end = sum(len(line) + 1 for line in lines[:last]) - 1
    return start, max(start, min(end, len(source)))


def line_range(first, last=None):
    """(start, end) character indices of lines first..last (1-based,
    inclusive; last defaults to first) in the open script, ready for
    select, replace and reveal:

        ek.select(*ek.line_range(12, 14))
    """
    return lines_in(text(), first, first if last is None else last)


def _line_at(view, source, point):
    """The 1-based line of source at point, in the text view's coordinates."""
    position = view.closestPositionToPoint_(point)
    if position is None:
        return 1
    utf16 = int(view.offsetFromPosition_toPosition_(view.beginningOfDocument(), position))
    return source.count('\n', 0, python_index(source, utf16)) + 1


@_app.on_main
def replace(start, end, new_text):
    """Replace start..end (Python indices) with new_text. Goes through the
    text view so the final character can be replaced too. True on success."""
    source = text()
    if start <= 0 and end >= len(source) and not new_text:
        new_text = EMPTY_SCRIPT
    return _replace_units(utf16_offset(source, start), utf16_offset(source, end), new_text)


@_app.on_main
def insert(new_text):
    """Type new_text at the cursor, over any selection, and leave the cursor
    after it. Returns the new cursor position, or None with no script."""
    chosen = selection()
    if chosen is None:
        return None
    start, end = chosen
    if not replace(start, end, new_text):
        return None
    select(start + len(new_text), scroll=True)
    return start + len(new_text)


@_app.on_main
def replace_all(term, new_text, case_sensitive=False, whole_word=False, regex=False):
    """Replace every match of term with new_text (from the end backwards, so
    earlier positions stay right). Returns how many were replaced."""
    source = text()
    ranges = find_all(term, source, case_sensitive, whole_word, regex)
    for start, end in reversed(ranges):
        _replace_units(utf16_offset(source, start), utf16_offset(source, end), new_text)
    return len(ranges)


def _replace_units(first, last, new_text):
    """Replace editor positions first..last (UTF-16) with new_text."""
    try:
        view = _app.text_view()
        if view is not None:
            span = ObjCClass('OMTextRange').rangeWithNSRange_(NSRange(first, last - first))
            view.replaceRange_withText_(span, new_text)
        else:
            # Fallback: cannot reach the final character (pythonista-editor guide).
            pythonista_editor.replace_text(first, last, new_text)
        return True
    except Exception as error:
        print('editorkit: replace failed: %r' % (error,))
        return False
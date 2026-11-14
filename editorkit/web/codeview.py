"""Code as HTML: syntax colours, numbered rows, marked matches.

Pure Python (no ui, no editor), so tests/smoke_codeview.py checks it
headless: syntax colours and line-numbered rows, built on device lessons (no
position: sticky; context greyed by colour, not opacity). Lines wrap to the
window like the docs' code blocks (WRAP_LINES), a wrapped line carrying on
at its own indent; with WRAP_LINES False the page scrolls sideways as one.

A page shell (page_html) is loaded once into a WebView (tiles.Code); file
sections are then set or added with setResults / addResults. A tap on a
row loads LINK_SCHEME + 'go/' + the row's data-go; any touch on the page
loads LINK_SCHEME + 'scroll' (Search puts the keyboard away with it).
"""
import html
import io
import json
from collections import namedtuple
import keyword
import token
import tokenize

LINK_SCHEME = 'editorkit-code://'

# Taps (editable). The old UIWebView holds a click back about 300 ms while it
# waits out a double tap. A fast tap is sent the moment the finger lifts.
FAST_TAPS = True                 # False: wait for the browser's click, as before
TAP_SLOP = 10                    # points a finger may wander and still be a tap
TAP_MAX_SECONDS = 0.6            # held longer than this: not a tap
TAP_DRIFT = 3                    # innerWidth and clientWidth further apart than
                                 # this: natively zoomed, leave it to the click

# --- Look (editable) ------------------------------------------------------

SYNTAX_COLOURS = {
    'kw': '#ff6b7a',
    'fn': '#68D3C2',
    'cls': '#68D3C2',
    'self': '#68D3C2',
    'builtin': '#68D3C2',
    'str': '#FF9F43',
    'num': '#B58CFF',
    'com': '#8a8a8a',
}
FONT_SIZE = 13                   # the docs' code blocks' size (prose.py)
WRAP_LINES = True                # lines wrap to the window; False: one line per row, sideways
HANG = 2                         # a wrapped line carries on this many spaces past its indent

BUILTINS = {
    'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set',
    'tuple', 'open', 'bool', 'enumerate', 'zip', 'min', 'max', 'sum', 'abs',
    'isinstance', 'getattr', 'setattr', 'hasattr', 'super', 'sorted', 'any',
    'all', 'map', 'filter', 'repr', 'type', 'round', 'object', 'Exception',
}


# --- Syntax colouring -----------------------------------------------------

def token_class(tok, previous_name):
    """CSS class for one token, or None to leave it in the text colour."""
    if tok.type == token.NAME:
        if previous_name == 'def':
            return 'fn'
        if previous_name == 'class':
            return 'cls'
        if keyword.iskeyword(tok.string):
            return 'kw'
        if tok.string == 'self':
            return 'self'
        if tok.string in BUILTINS:
            return 'builtin'
        return None
    if tok.type == token.STRING:
        return 'str'
    if tok.type == token.NUMBER:
        return 'num'
    if tok.type == tokenize.COMMENT:
        return 'com'
    if token.tok_name.get(tok.type, '').startswith('FSTRING'):
        return 'str'          # Python 3.12+ splits f-strings into parts
    return None


def syntax_classes(text):
    """{line number: [(start, end, css class), ...]} for Python source.

    Half-typed code that stops tokenizing keeps the colours found before
    the error, so a broken script still shows, just less coloured.
    """
    lines = text.split('\n')
    classes = {}
    previous_name = None
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            css = token_class(tok, previous_name)
            previous_name = tok.string if tok.type == token.NAME else None
            if css is None:
                continue
            (start_row, start_col), (end_row, end_col) = tok.start, tok.end
            for row in range(start_row, end_row + 1):     # strings can span lines
                line_length = len(lines[row - 1]) if row <= len(lines) else 0
                first = start_col if row == start_row else 0
                last = end_col if row == end_row else line_length
                classes.setdefault(row, []).append((first, last, css))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return classes


# --- One line -------------------------------------------------------------

def escape(text):
    return html.escape(text, quote=False)


def coloured(line, start, end, css_at):
    """line[start:end] as HTML, one span per run of the same syntax colour."""
    pieces = []
    run_start = start
    for position in range(start, end + 1):
        if position == end or css_at[position] != css_at[run_start]:
            if position > run_start:
                text = escape(line[run_start:position])
                css = css_at[run_start]
                pieces.append('<span class="%s">%s</span>' % (css, text) if css else text)
            run_start = position
    return ''.join(pieces)


def line_html(line, classes, marks, go=None, gos=None):
    """One source line: syntax colours, and each match in a <mark>. A mark is
    (start, end), or (start, end, new text) to preview a replacement: the
    old struck through, the new beside it. With go ('file/line'), each match
    is wrapped in <span class="hit" data-go="file/line/start/end">, so a tap
    on it picks that match and setCurrentGo can outline it. gos (one go id
    per mark, or None) does the same with ids from a section builder."""
    css_at = [None] * len(line)
    for start, end, css in classes:
        for position in range(max(start, 0), min(end, len(line))):
            css_at[position] = css
    out = []
    position = 0
    for count, mark in enumerate(marks):
        start, end = max(mark[0], position), min(mark[1], len(line))
        if start >= end:
            continue
        out.append(coloured(line, position, start, css_at))
        found = coloured(line, start, end, css_at)
        if len(mark) > 2:
            shown = ('<mark class="old">%s</mark><mark class="new">%s</mark>'
                     % (found, escape(mark[2])))
        else:
            shown = '<mark>%s</mark>' % found
        if gos is not None:
            mark_go = gos[count]
        elif go is not None:
            mark_go = '%s/%d/%d' % (go, mark[0], mark[1])
        else:
            mark_go = None
        if mark_go is not None:
            shown = '<span class="hit" data-go="%s">%s</span>' % (mark_go, shown)
        out.append(shown)
        position = end
    out.append(coloured(line, position, len(line), css_at))
    return ''.join(out)


# --- Sections -------------------------------------------------------------

def line_blocks(hit_lines, line_count, context_lines):
    """Merged (first, last) line ranges: each hit line with its context.
    Ranges that touch or overlap become one block."""
    blocks = []
    for line in sorted(set(hit_lines)):
        first = max(1, line - context_lines)
        last = min(line_count, line + context_lines)
        if blocks and first <= blocks[-1][1] + 1:
            blocks[-1] = (blocks[-1][0], max(blocks[-1][1], last))
        else:
            blocks.append((first, last))
    return blocks


def file_html(label, text, marks_by_line, context_lines=0, file_index=0, python=True):
    """One file's section: its label, then blocks of numbered lines with
    every match marked.

    marks_by_line is {line number: [(start, end), ...]} in columns. Every
    row's data-go is 'file/line/start/end': the start and end of its first
    match, or 0/0 for a context line. Each match also carries its own
    data-go, so a tap on it picks exactly that match.
    """
    lines = text.splitlines()
    classes = syntax_classes(text) if python else {}
    out = ['<div class="file"><div class="path">%s</div>' % escape(label)]
    for first, last in line_blocks(marks_by_line, len(lines), context_lines):
        out.append('<div class="block">')
        for number in range(first, last + 1):
            marks = sorted(marks_by_line.get(number, []))
            code = line_html(lines[number - 1], classes.get(number, []), marks,
                             go='%d/%d' % (file_index, number))
            start, end = marks[0][:2] if marks else (0, 0)
            css = 'row hit' if marks else 'row ctx'
            out.append('<div class="%s" data-go="%d/%d/%d/%d"><span class="ln">%d</span>'
                       '<span class="code">%s</span></div>'
                       % (css, file_index, number, start, end, number, code))
        out.append('</div>')
    out.append('</div>')
    return ''.join(out)


PREVIEW_LINES = 80


def preview_html(label, text, python=True, limit=PREVIEW_LINES, file_index=0):
    """The first limit lines of a file, numbered and coloured, as one block
    under its label. Each row's data-go ('file/line/0/0') opens that line."""
    lines = text.splitlines()
    classes = syntax_classes(text) if python else {}
    out = ['<div class="file"><div class="path">%s</div>' % escape(label)]
    if lines:
        out.append('<div class="block">')
        for number, line in enumerate(lines[:limit], 1):
            code = line_html(line, classes.get(number, []), [])
            out.append('<div class="row" data-go="%d/%d/0/0"><span class="ln">%d</span>'
                       '<span class="code">%s</span></div>'
                       % (file_index, number, number, code))
        out.append('</div>')
    if len(lines) > limit:
        out.append(message_html('%d more lines: open the file to see them.'
                                % (len(lines) - limit)))
    if not lines:
        out.append(message_html('Empty file.'))
    out.append('</div>')
    return ''.join(out)


# --- Sections with items ----------------------------------------
#
# A section is (html, items): HTML for a tiles.Code page, and items,
# {go id: any Python object}. Every tappable row or match carries a go id
# 'section.counter'; a tap hands back its object (tiles.Code(on_pick=...)),
# so tools never build or parse 'file/line/start/end' strings. Builders stay
# pure, so they can run on a Job thread.

Row = namedtuple('Row', 'text kind item number')
Row.__new__.__defaults__ = ('code', None, None)
ROW_KINDS = ('code', 'plain', 'add', 'remove', 'error', 'note', 'heading')


class SectionIds:
    """Hands out go ids for one section and remembers what each stands for."""

    def __init__(self, section):
        self.section = section
        self.items = {}

    def go(self, item):
        """A new go id for item, or None when there is no item (not tappable)."""
        if item is None:
            return None
        go = '%s.%d' % (self.section, len(self.items))
        self.items[go] = item
        return go


# A tap on an element whose data-go is COPY_GO copies its code block (prose
# code blocks' ⧉ Copy): the page sends LINK_SCHEME + COPY_PATH + the text.
COPY_GO = 'ekcopy'
COPY_PATH = 'copy/'


def go_attribute(go):
    return ' data-go="%s"' % go if go is not None else ''


def file_section(section, label, text, marks_by_line, context_lines=0, python=True,
                 line_item=None, mark_item=None, row_button=None):
    """Like file_html, with items instead of strings. line_item(number, marks)
    gives a row's item, mark_item(number, mark) each match's; either may be
    None (or return None) for nothing to tap. row_button=(label,
    make_item): a small button at the start of every row with matches,
    make_item(number, marks) its item (Search's 📜); other rows keep an
    empty slot so the numbers line up. Returns (html, items)."""
    ids = SectionIds(section)
    lines = text.splitlines()
    classes = syntax_classes(text) if python else {}
    out = ['<div class="file"><div class="path">%s</div>' % escape(label)]
    for first, last in line_blocks(marks_by_line, len(lines), context_lines):
        out.append('<div class="block">')
        for number in range(first, last + 1):
            marks = sorted(marks_by_line.get(number, []))
            # Matches first, so set_current(item) finds a match before its row.
            mark_gos = [ids.go(mark_item(number, mark)) if mark_item else None
                        for mark in marks]
            row_go = ids.go(line_item(number, marks)) if line_item else None
            code = line_html(lines[number - 1], classes.get(number, []), marks, gos=mark_gos)
            css = 'row hit' if marks else 'row ctx'
            action = ''
            if row_button is not None:
                button_label, make_item = row_button
                action_go = ids.go(make_item(number, marks)) if marks else None
                action = '<span class="rowact"%s>%s</span>' % (
                    go_attribute(action_go), escape(button_label) if action_go else '')
            out.append('<div class="%s"%s>%s<span class="ln">%d</span>'
                       '<span class="code">%s</span></div>'
                       % (css, go_attribute(row_go), action, number, code))
        out.append('</div>')
    out.append('</div>')
    return ''.join(out), ids.items


def preview_section(section, label, text, python=True, limit=PREVIEW_LINES, line_item=None,
                    tinted=None):
    """Like preview_html, with items: line_item(number) gives each row's item
    (by default the line number itself). tinted=(first, last) tints those
    lines as a band (a range being worked on). Returns (html, items)."""
    ids = SectionIds(section)
    if line_item is None:
        line_item = lambda number: number
    lines = text.splitlines()
    classes = syntax_classes(text) if python else {}
    out = ['<div class="file"><div class="path">%s</div>' % escape(label)]
    if lines:
        out.append('<div class="block">')
        for number, line in enumerate(lines[:limit], 1):
            code = line_html(line, classes.get(number, []), [])
            picked = ' picked' if tinted and tinted[0] <= number <= tinted[1] else ''
            out.append('<div class="row%s"%s><span class="ln">%d</span>'
                       '<span class="code">%s</span></div>'
                       % (picked, go_attribute(ids.go(line_item(number))), number, code))
        out.append('</div>')
    if len(lines) > limit:
        out.append(message_html('%d more lines: open the file to see them.'
                                % (len(lines) - limit)))
    if not lines:
        out.append(message_html('Empty file.'))
    out.append('</div>')
    return ''.join(out), ids.items


def rows_section(section, label, rows):
    """Any list of Rows under a label (none if empty): tracebacks, diffs,
    outlines, notes. kind 'code' colours the text as Python, 'plain' leaves
    it, 'add' and 'remove' tint it as a diff, 'error' tints it red without
    striking it (stderr, exceptions), 'note' greys it, 'heading' is a small
    heading. number (optional) shows in the line-number column. A row
    with an item can be tapped. Returns (html, items)."""
    ids = SectionIds(section)
    out = ['<div class="file">']
    if label:
        out.append('<div class="path">%s</div>' % escape(label))
    out.append('<div class="block">')
    for row in rows:
        go = go_attribute(ids.go(row.item))
        if row.kind == 'heading':
            out.append('<div class="row heading"%s><span class="code">%s</span></div>'
                       % (go, escape(row.text)))
            continue
        if row.kind == 'code':
            code = line_html(row.text, syntax_classes(row.text).get(1, []), [])
        else:
            code = escape(row.text)
        number = '' if row.number is None else str(row.number)
        out.append('<div class="row %s"%s><span class="ln">%s</span>'
                   '<span class="code">%s</span></div>'
                   % (escape(row.kind), go, escape(number), code))
    out.append('</div></div>')
    return ''.join(out), ids.items


def message_html(text):
    """A quiet line of text in place of results."""
    return '<div class="note">%s</div>' % escape(text)


# --- The page shell -------------------------------------------------------

def css_colour(value):
    """A CSS colour from a Pythonista one: '#hex' or a name as is, RGB(A) as rgba()."""
    if isinstance(value, str):
        return value
    red, green, blue = (round(part * 255) for part in value[:3])
    alpha = value[3] if len(value) > 3 else 1.0
    return 'rgba(%d, %d, %d, %.3f)' % (red, green, blue, alpha)


PAGE_SCRIPT = """
function hangIndents() {
    // A wrapped line carries on at its own indent plus HANG spaces, as
    // Pythonista's editor wraps. Each row is worked out once.
    if (!WRAP_LINES) { return; }
    var codes = document.querySelectorAll('.code:not([data-hung])');
    for (var i = 0; i < codes.length; i++) {
        var text = codes[i].textContent, width = 0, at = 0;
        while (at < text.length && (text[at] === ' ' || text[at] === '\\t')) {
            width += text[at] === '\\t' ? 4 : 1;
            at += 1;
        }
        var hang = (width + HANG) + 'ch';
        codes[i].style.paddingLeft = hang;
        codes[i].style.textIndent = '-' + hang;
        codes[i].setAttribute('data-hung', '');
    }
}
function setResults(html) {
    document.getElementById('results').innerHTML = html;
    hangIndents();
    window.scrollTo(0, 0);
}
function addResults(html) {
    document.getElementById('results').insertAdjacentHTML('beforeend', html);
    hangIndents();
}
function setAndEnd(html) {
    document.getElementById('results').innerHTML = html;
    hangIndents();
    window.scrollTo(0, document.body.scrollHeight);
}
function clearCurrent() {
    var old = document.querySelectorAll('.current');
    for (var i = 0; i < old.length; i++) { old[i].classList.remove('current'); }
}
function markCurrent(element) {
    var row = element.closest('.row');
    if (element !== row) { element.classList.add('current'); }
    if (row) { row.classList.add('current'); }
}
function setCurrentGo(go) {
    clearCurrent();
    var target = document.querySelector('.hit[data-go="' + go + '"]')
              || document.querySelector('[data-go="' + go + '"]')
              || document.querySelector('.row[data-go^="' + go + '"]');
    if (!target) { return; }
    markCurrent(target);
    target.scrollIntoView({block: 'center', inline: 'nearest'});
}
function setFontSize(px) {
    document.body.style.fontSize = px + 'px';
}
// Tap breadcrumbs, read by tools/probe_dead_taps.py (dead taps, 2026-11-11).
window.ekTouches = 0;
window.ekClicks = 0;
window.ekFastTaps = 0;
window.ekLastGo = '';
function goTarget(node) {
    // The nearest tappable thing at or above node: an action wins over its card.
    while (node && !(node.getAttribute && node.getAttribute('data-go'))) {
        node = node.parentNode;
    }
    return node || null;
}
function copyBlock(button) {
    var code = button.parentNode.querySelector('.ek-block-code');
    window.location.href = SCHEME + 'copy/' + encodeURIComponent(code ? code.innerText : '');
    var label = button.textContent;
    button.textContent = 'Copied';
    setTimeout(function () { button.textContent = label; }, 1200);
}
function sendGo(target) {
    if (target.getAttribute('data-go') === 'ekcopy') { copyBlock(target); return; }
    window.ekLastGo = target.getAttribute('data-go');
    clearCurrent();
    markCurrent(target);
    window.location.href = SCHEME + 'go/' + target.getAttribute('data-go');
}
// Fast taps (FAST_TAPS, TAP_SLOP, TAP_MAX_MS and TAP_DRIFT are set by
// page_html). A tap is one finger, down and up in about the same place,
// quickly, on a page that is not still moving from a drag. It is sent on
// finger-up and its click is cancelled. Two cases are left to the browser's
// click: a web view zoomed natively (its touch targets are wrong then,
// 2026-11-12; innerWidth and clientWidth disagree), and a touch the page's
// own script already handled (preventDefault). So a tap is never lost or
// misplaced: at worst it is slow.
var ekTap = null;            // the touch that may still be a tap: {x, y, at}
var ekDragged = false;       // this touch moved too far to be a tap
var ekFastAt = 0;            // when a fast tap was last sent
var ekCoasting = false;      // the page may still be moving after a drag
var ekCoastX = 0;
var ekCoastY = 0;
function watchCoast() {
    if (window.scrollX === ekCoastX && window.scrollY === ekCoastY) {
        ekCoasting = false;
        return;
    }
    ekCoastX = window.scrollX;
    ekCoastY = window.scrollY;
    setTimeout(watchCoast, 80);
}
function nativelyZoomed() {
    return Math.abs(window.innerWidth - document.documentElement.clientWidth) > TAP_DRIFT;
}
document.addEventListener('click', function (event) {
    window.ekClicks += 1;
    if (Date.now() - ekFastAt < 700) { return; }     // already sent on finger-up
    var target = goTarget(event.target);
    if (!target) { return; }
    sendGo(target);
});
document.addEventListener('touchstart', function (event) {
    window.ekTouches += 1;
    window.location.href = SCHEME + 'scroll';
    ekDragged = false;
    if (event.touches.length === 1 && !ekCoasting) {
        ekTap = {x: event.touches[0].clientX, y: event.touches[0].clientY, at: Date.now()};
    } else {
        ekTap = null;        // a pinch, or a touch that only stops a moving page
    }
}, {passive: true});
document.addEventListener('touchmove', function (event) {
    if (!ekTap) { return; }
    var touch = event.touches[0];
    if (event.touches.length !== 1 || Math.abs(touch.clientX - ekTap.x) > TAP_SLOP
            || Math.abs(touch.clientY - ekTap.y) > TAP_SLOP) {
        ekTap = null;
        ekDragged = true;
    }
}, {passive: true});
document.addEventListener('touchcancel', function () {
    ekTap = null;
}, {passive: true});
document.addEventListener('touchend', function (event) {
    var tap = ekTap;
    ekTap = null;
    if (ekDragged) {
        // The page may coast on after a drag: no fast taps until it rests.
        ekDragged = false;
        ekCoasting = true;
        ekCoastX = window.scrollX;
        ekCoastY = window.scrollY;
        setTimeout(watchCoast, 80);
        return;
    }
    if (event.defaultPrevented) { return; }          // the page's own script took it
    if (!FAST_TAPS || !tap || Date.now() - tap.at > TAP_MAX_MS || nativelyZoomed()) {
        return;
    }
    var target = goTarget(event.target);
    if (!target) { return; }
    event.preventDefault();  // no click will follow
    ekFastAt = Date.now();
    window.ekFastTaps += 1;
    sendGo(target);
}, {passive: false});
"""

PAGE_CSS = """
:root { --accent: %(accent)s; --muted: %(muted)s; --card: %(card)s; --text: %(text)s;
    --wash: %(wash)s; --wash-strong: %(wash_strong)s; --rule: %(rule)s; --line: %(line)s; }
html, body { margin: 0; padding: 0 4px; background: %(background)s; color: %(text)s;
    font: %(size)dpx Menlo, monospace; -webkit-text-size-adjust: none; }
#results { width: max-content; min-width: 100%%; }
.file { margin: 0 0 10px 0; }
.path { color: %(accent)s; font: bold 13px -apple-system, sans-serif; padding: 6px 2px; }
.block { background: %(card)s; border-radius: 6px; margin: 0 0 6px 0; padding: 4px 0; }
.row { display: flex; min-width: max-content; min-height: 1.65em; line-height: 1.65em;
    cursor: pointer; }
.row.current { background: var(--wash-strong); box-shadow: inset 3px 0 0 %(accent)s; }
.row.picked { background: var(--wash); box-shadow: inset 3px 0 0 %(accent)s; }
.ln { flex: 0 0 40px; padding-right: 10px; text-align: right; color: %(muted)s;
    -webkit-user-select: none; }
.code { white-space: pre; tab-size: 4; padding-right: 12px; }
.row.ctx .code, .row.ctx .code span { color: %(muted)s; }
.rowact { flex: 0 0 26px; text-align: center; font-size: 13px; opacity: 0.85; }
.rowact:empty { cursor: default; }
[data-go] { cursor: pointer; }
mark { background: %(accent)s; color: #111111; border-radius: 3px; padding: 1px 0; }
mark span { color: #111111 !important; }
mark.old { background: #FF5A5F; text-decoration: line-through; }
.hit.current { outline: 2px solid %(accent)s; outline-offset: 2px; border-radius: 4px; }
.row.add .code { background: rgba(98, 210, 111, 0.18); }
.row.remove .code { background: rgba(255, 90, 95, 0.18); text-decoration: line-through; }
.row.error .code { background: rgba(255, 90, 95, 0.18); }
.row.note .code { color: %(muted)s; }
.row.heading .code { font-weight: 600; color: %(accent)s; padding-top: 6px; }
mark.new { background: #62D26F; margin-left: 2px; }
.note { padding: 12px 4px; color: %(muted)s; font-family: -apple-system, sans-serif; }
"""

# Code that flexes (WRAP_LINES): every code view wraps to the window like the
# docs' code blocks, at their size and line height; hangIndents() in the page
# script indents each wrapped line under its own code.
FLEX_CSS = """
#results { width: auto; min-width: 0; }
.row { min-width: 0; min-height: 1.5em; line-height: 1.5; padding: 1px 0; }
.code { white-space: pre-wrap; overflow-wrap: anywhere; flex: 1 1 auto; min-width: 0; }
.file { background: var(--card); border-radius: 12px; margin: 0 0 10px 0; padding: 0 0 4px;
    overflow: hidden; }
.path { padding: 9px 12px 5px; font: 600 13px -apple-system, sans-serif; }
.block { background: none; border-radius: 0; margin: 0; padding: 4px 0; }
.block + .block { border-top: 1px dashed var(--rule); }
.ln { flex: 0 0 auto; min-width: 2.4em; padding: 0 10px 0 6px; font-size: 0.85em; }
"""
# Output that wraps: pass as tiles.Code(extra_css=codeview.WRAP_CSS). Long
# lines wrap at the page edge instead of the page scrolling sideways (a
# console, logs, messages), and rows with no number drop the empty
# line-number column. Code views keep the default: one line per row.
# The old UIWebView can draw a wrapping page clipped after a resize: pair
# WRAP_CSS with tiles.Code(fresh_on_grow=True).
WRAP_CSS = """
#results { width: auto; min-width: 0; }
.row { min-width: 0; }
.code { white-space: pre-wrap; overflow-wrap: anywhere; flex: 1 1 auto; min-width: 0; }
.ln:empty { flex-basis: 6px; padding-right: 0; }
"""


def rgb_of(colour):
    """(r, g, b) 0-255 from a theme colour: '#rrggbb', '#rgb', 'rgb(a)(...)',
    or a ui colour tuple (0-1 floats). White when it cannot tell."""
    import re
    if isinstance(colour, (tuple, list)) and len(colour) >= 3:
        values = [float(value) for value in colour[:3]]
        if all(value <= 1.0 for value in values):
            return tuple(int(round(value * 255)) for value in values)
        return tuple(int(value) for value in values)
    text = str(colour or '').strip()
    if text.startswith('#') and len(text) in (7, 9):
        return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))
    if text.startswith('#') and len(text) == 4:
        return tuple(int(digit * 2, 16) for digit in text[1:4])
    match = re.match(r'rgba?\(([^)]*)\)', text)
    if match:
        parts = [part.strip() for part in match.group(1).split(',')][:3]
        try:
            return tuple(int(float(part)) for part in parts)
        except ValueError:
            pass
    return (255, 255, 255)


def wash(colour, alpha):
    """colour at alpha, as CSS: the theme's text colour as a light wash on a
    dark theme and a dark wash on a light one (RELEASE.txt 1.2)."""
    red, green, blue = rgb_of(colour)
    return 'rgba(%d, %d, %d, %.2f)' % (red, green, blue, alpha)


def page_html(palette, font_size=FONT_SIZE, extra_css=''):
    """The page shell, loaded once. palette is a window's palette (or any
    object with panel, background, text, dim and accent)."""
    values = {
        'background': css_colour(palette.panel),
        'card': css_colour(palette.background),
        'text': css_colour(palette.text),
        'muted': css_colour(palette.dim),
        'accent': css_colour(palette.accent),
        'size': font_size,
        # Shades of the theme's own text colour, so washes and lines read on
        # light and dark themes alike (RELEASE.txt 1.2).
        'wash': wash(palette.text, 0.07),
        'wash_strong': wash(palette.text, 0.12),
        'rule': wash(palette.text, 0.14),
        'line': wash(palette.text, 0.30),
    }
    css = PAGE_CSS % values + (FLEX_CSS if WRAP_LINES else '')
    # The theme's own syntax colours where it has them (RELEASE.txt 1.2).
    syntax = dict(SYNTAX_COLOURS)
    syntax.update(getattr(palette, 'syntax', None) or {})
    syntax_css = '\n'.join('.%s { color: %s; }' % item for item in syntax.items())
    script = ('var SCHEME = %s;\nvar FAST_TAPS = %s;\nvar TAP_SLOP = %d;\n'
              'var TAP_MAX_MS = %d;\nvar TAP_DRIFT = %d;\nvar WRAP_LINES = %s;\n'
              'var HANG = %d;\n%s' % (
                  json.dumps(LINK_SCHEME), json.dumps(bool(FAST_TAPS)), TAP_SLOP,
                  int(TAP_MAX_SECONDS * 1000), TAP_DRIFT, json.dumps(bool(WRAP_LINES)),
                  HANG, PAGE_SCRIPT))
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>%s\n%s\n%s</style></head><body><div id="results"></div>'
            '<script>%s</script></body></html>' % (css, syntax_css, extra_css, script))
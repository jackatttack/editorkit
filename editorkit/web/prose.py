"""Prose: pages that read like Pythonista's own documentation.

Borrowed from the docs Pythonista ships (Sphinx, pydata theme, with
Pythonista's own pythonista_styles.css on top): the system font at a
reading size, headings at weight 600, signatures in monospace with the
name in the accent colour, `inline code` as faint chips, code blocks that
wrap to the width, and notes as rounded callouts with a tinted title. All
in the editor theme's colours (var(--text), --accent, --wash, --rule), and
fluid: everything wraps, so it reads well at any window size.

    from editorkit.web import cards, prose

    page = cards.Page()
    page.prose(prose.heading('Windows', 1),
               prose.text('`ek.show(thing)` puts a window over your code.'),
               prose.signature('show', 'thing, title=None', prefix='ek.'),
               prose.code("ek.show('Hello')"),
               prose.note('Showing again swaps the content in place.', 'Tip', 'tip'))
    ek.show(page, title='Windows')

A builder returns HTML; article() wraps blocks for a card body, and
cards.Page.prose() adds them as a full-width article. Pure Python (no ui):
tests/smoke_prose.py checks it.
"""
import re

from . import codeview

escape = codeview.escape


# --- Look (editable) ---------------------------------------------------------------

# A note's colour by kind; any other kind uses the theme's line colour.
NOTE_COLOURS = {'note': 'var(--accent)', 'tip': '#62D26F', 'warning': '#FF9F43',
                'danger': '#FF5A5F'}
COPY_LABEL = '⧉ Copy'        # the page shows 'Copied' for a moment after a tap

CSS = """
.ek-prose { font: 16px/1.55 -apple-system, sans-serif; color: var(--text);
    overflow-wrap: break-word; max-width: 60em; padding: 2px 6px 10px; min-width: 0; }
.ek-card .ek-prose { font-size: 14px; padding: 0; }
.ek-prose > :first-child { margin-top: 0; }
.ek-prose > :last-child { margin-bottom: 0; }
.ek-prose h1, .ek-prose h2, .ek-prose h3, .ek-prose h4 { font-weight: 600; line-height: 1.15;
    margin: 1.5em 0 0.5em; }
.ek-prose h1 { font-size: 1.5em; } .ek-prose h2 { font-size: 1.35em; }
.ek-prose h3 { font-size: 1.2em; } .ek-prose h4 { font-size: 1.1em; }
.ek-prose p { margin: 0 0 0.85em; }
.ek-prose code { font: 0.86em Menlo, monospace; padding: 0.1em 0.3em; background: var(--wash);
    border: 1px solid var(--rule); border-radius: 0.3em; }
.ek-prose a, .ek-prose .dc-link { color: var(--accent); text-decoration: none; }
.ek-prose .dc-link code, .ek-prose a code { color: var(--accent); }
.ek-prose .ek-block { font: 13px/1.5 Menlo, monospace; white-space: pre-wrap;
    overflow-wrap: anywhere; background: var(--wash); border-radius: 10px;
    padding: 10px 12px; margin: 0 0 1em; }
.ek-copy { float: right; margin: -3px -5px 4px 10px; padding: 3px 9px; border-radius: 8px;
    font: 12px -apple-system, sans-serif; background: var(--wash-strong); color: var(--text);
    cursor: pointer; -webkit-user-select: none; }
.ek-sig { font: 0.88em/1.45 Menlo, monospace; margin: 1.3em 0 0.4em; overflow-wrap: anywhere; }
.ek-sig .kind { font-style: italic; opacity: 0.65; }
.ek-sig .prefix { color: var(--accent); font-weight: 200; }
.ek-sig .name { color: var(--accent); font-weight: 600; }
.ek-sig .params { opacity: 0.85; }
.ek-member > .ek-member-body { margin-left: 1.1em; }
.ek-terms { display: grid; grid-template-columns: fit-content(40%) minmax(0, 1fr);
    gap: 6px 14px; margin: 0 0 1em; }
.ek-terms dt { font: 0.88em/1.55 Menlo, monospace; color: var(--accent); overflow-wrap: anywhere; }
.ek-terms dd { margin: 0; }
@media (max-width: 380px) {
    .ek-terms { display: block; }
    .ek-terms dd { margin: 0 0 8px 1em; }
}
.ek-callout { border: 0.5px solid var(--k, var(--line)); border-radius: 12px;
    font-size: 0.88em; overflow: hidden; margin: 0 0 1em; }
.ek-callout-title { font-weight: 600; padding: 6px 12px; position: relative; }
.ek-callout-title::before { content: ''; position: absolute; left: 0; top: 0; right: 0; bottom: 0;
    background: var(--k, var(--line)); opacity: 0.14; pointer-events: none; }
.ek-callout-body { padding: 8px 12px 10px; }
.ek-callout-body p:last-child, .ek-callout-body .ek-block:last-child { margin-bottom: 0; }
.ek-meta { font-size: 0.8em; color: var(--muted); margin: -0.3em 0 0.9em; }
.ek-row { padding: 10px 2px 11px; border-bottom: 1px solid var(--rule); cursor: pointer; }
.ek-row:last-child { border-bottom: none; }
.ek-row .ek-sig { margin: 0 0 3px; }
.ek-row-text { font-size: 0.9em; opacity: 0.85; }
.ek-prose img { max-width: 100%; height: auto; }
.ek-prose table { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse;
    margin: 0 0 1em; font-size: 0.9em; }
.ek-prose th, .ek-prose td { padding: 4px 10px 4px 0; border-bottom: 1px solid var(--rule);
    text-align: left; vertical-align: top; }
.ek-prose ul, .ek-prose ol { padding-left: 1.3em; margin: 0 0 0.85em; }
.ek-prose li { margin: 0.2em 0; }

/* Sphinx markup (Pythonista's own docs), in the same look. */
.ek-sig .sig-prename, .ek-sig .descclassname { color: var(--accent); font-weight: 200; }
.ek-sig .sig-name, .ek-sig .descname { color: var(--accent); font-weight: 600; }
.ek-sig em { font-style: normal; }
.ek-sig em.property { font-style: italic; opacity: 0.65; }
.ek-prose dl:not(.ek-terms) > dt { font-family: Menlo, monospace; font-size: 0.88em;
    margin-top: 1em; overflow-wrap: anywhere; }
.ek-prose dl:not(.ek-terms) > dd { margin: 0.3em 0 0.6em 1.1em; }
.ek-prose dl.field-list { display: grid; grid-template-columns: fit-content(30%) minmax(0, 1fr);
    gap: 4px 12px; }
.ek-prose dl.field-list > dt { font-family: inherit; font-weight: 600; margin: 0; }
.ek-prose dl.field-list > dd { margin: 0; }
.ek-prose .admonition { --k: var(--accent); border: 0.5px solid var(--k); border-radius: 12px;
    font-size: 0.88em; overflow: hidden; margin: 0 0 1em; padding: 0 12px 10px; }
.ek-prose .admonition.warning, .ek-prose .admonition.caution,
.ek-prose .admonition.attention { --k: #FF9F43; }
.ek-prose .admonition.danger, .ek-prose .admonition.error { --k: #FF5A5F; }
.ek-prose .admonition.tip, .ek-prose .admonition.hint,
.ek-prose .admonition.important { --k: #62D26F; }
.ek-prose .admonition-title { font-weight: 600; margin: 0 -12px 8px; padding: 6px 12px;
    position: relative; }
.ek-prose .admonition-title::before { content: ''; position: absolute; left: 0; top: 0;
    right: 0; bottom: 0; background: var(--k); opacity: 0.14; pointer-events: none; }
.ek-prose .admonition > :last-child { margin-bottom: 0; }
"""


# --- Inline words ---------------------------------------------------------------------

_CODE = re.compile(r'`([^`]+)`')
_BOLD = re.compile(r'\*\*([^*]+)\*\*')


def inline(words):
    """Words as HTML: escaped, `code` as a chip, **bold** as bold."""
    html = escape(words)
    html = _CODE.sub(lambda match: '<code>%s</code>' % match.group(1), html)
    return _BOLD.sub(lambda match: '<b>%s</b>' % match.group(1), html)


# --- Blocks ---------------------------------------------------------------------------

def heading(words, level=2):
    """A heading, level 1 (biggest) to 4."""
    level = max(1, min(4, int(level)))
    return '<h%d>%s</h%d>' % (level, inline(words), level)


def meta(words):
    """A small muted line under a heading: what kind of thing, where from."""
    return '<p class="ek-meta">%s</p>' % inline(words)


def text(words):
    """Paragraphs: blank lines separate them, single line breaks are joined
    (so a docstring reads as written). A paragraph whose every line starts
    with '- ', '• ' or '* ' becomes a bulleted list."""
    out = []
    for part in re.split(r'\n\s*\n', words or ''):
        lines = [line.strip() for line in part.strip().split('\n') if line.strip()]
        if not lines:
            continue
        if all(line.startswith(('- ', '• ', '* ')) for line in lines):
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(line[2:]) for line in lines))
        else:
            out.append('<p>%s</p>' % inline(' '.join(lines)))
    return ''.join(out)


def code(source, python=True, copy=True):
    """A whole code block, syntax-coloured, wrapping to the width. copy puts
    a ⧉ Copy button in its corner: a tap puts the code on the clipboard
    (the Cards or Code tile does it; nothing to wire up)."""
    lines = (source or '').strip('\n').split('\n')
    classes = codeview.syntax_classes('\n'.join(lines)) if python else {}
    html = '\n'.join(codeview.line_html(line, classes.get(number, []), []) or ' '
                     for number, line in enumerate(lines, 1))
    button = ('<span class="ek-copy" data-go="%s">%s</span>' % (codeview.COPY_GO, COPY_LABEL)
              if copy else '')
    return '<div class="ek-block">%s<div class="ek-block-code">%s</div></div>' % (button, html)


def signature(name, params=None, prefix='', kind=''):
    """A signature line, as the docs show them: kind (class, function…) in
    italics, prefix (ui., ek.) light, the name bold, then (params).
    params=None leaves the brackets off (an attribute)."""
    parts = []
    if kind:
        parts.append('<span class="kind">%s</span> ' % escape(kind))
    if prefix:
        parts.append('<span class="prefix">%s</span>' % escape(prefix))
    parts.append('<span class="name">%s</span>' % escape(name))
    if params is not None:
        parts.append('(<span class="params">%s</span>)' % escape(params))
    return '<div class="ek-sig">%s</div>' % ''.join(parts)


def callout(title, *blocks, kind='note'):
    """A rounded callout with a tinted title, holding any blocks (words,
    code, terms): kind is note, tip, warning or danger."""
    colour = NOTE_COLOURS.get(kind, 'var(--line)')
    return ('<div class="ek-callout" style="--k:%s"><div class="ek-callout-title">%s</div>'
            '<div class="ek-callout-body">%s</div></div>'
            % (colour, escape(title), ''.join(blocks)))


def note(words, title='Note', kind='note'):
    """A callout of words (several paragraphs allowed): kind is note, tip,
    warning or danger."""
    return callout(title, text(words), kind=kind)


def terms(pairs):
    """A definition list: [(term, words)], terms in monospace. Side by side,
    stacked when the window is narrow."""
    rows = ''.join('<dt>%s</dt><dd>%s</dd>' % (escape(term), inline(words))
                   for term, words in pairs)
    return '<dl class="ek-terms">%s</dl>' % rows


def member(signature_html, *blocks):
    """A signature with its explanation indented beneath, like a documented
    function or class."""
    return ('<div class="ek-member">%s<div class="ek-member-body">%s</div></div>'
            % (signature_html, ''.join(blocks)))


def row(signature_html, words='', go=''):
    """One entry of a docs-style list: its signature, then a line of words,
    a hairline under it. go is the tap attribute (cards.Page.go(item)), so
    the whole row is one target."""
    under = '<div class="ek-row-text">%s</div>' % inline(words) if words else ''
    return '<div class="ek-row"%s>%s%s</div>' % (go, signature_html, under)


def article(*blocks):
    """Blocks wrapped as one prose article: a card body, or a whole page."""
    return '<div class="ek-prose">%s</div>' % ''.join(blocks)
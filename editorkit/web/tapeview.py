"""Tape as HTML: entries (what was asked, what came back) and a draft line.

Drawn by tiles.Tape inside a Code tile, on codeview's page shell with
tape_css added. Each entry's parts carry data-go ('input/<n>' and
'output/<n>'), so a tap says which entry and which part.
"""
from . import codeview

TAPE_CSS = """
body { font-family: Menlo, monospace; }
#results { width: auto; min-width: 0; }
.entry { padding: 6px 10px; border-bottom: 1px solid %(edge)s; text-align: right;
    overflow-x: auto; }
.input { color: %(muted)s; font-size: 13px; }
.output pre { display: inline-block; text-align: left; margin: 2px 0;
    font: 17px Menlo, monospace; color: %(text)s; white-space: pre; }
.output.error pre { color: #FF5A5F; }
.decimal { color: %(accent)s; font-size: 14px; }
.draft { padding: 10px; text-align: right; }
.expr { font-size: 24px; color: %(text)s; word-break: break-all; }
.caret { color: %(accent)s; }
.preview { color: %(muted)s; font-size: 15px; min-height: 1.3em; }
.preview.error { color: #FF5A5F; }
"""

EMPTY_TEXT = 'Nothing yet.'


def tape_css(palette):
    return TAPE_CSS % {
        'edge': codeview.css_colour(palette.edge),
        'muted': codeview.css_colour(palette.dim),
        'text': codeview.css_colour(palette.text),
        'accent': codeview.css_colour(palette.accent),
    }


def entry_html(index, entry):
    escape = codeview.escape
    error = ' error' if entry.get('error') else ''
    out = ['<div class="entry">',
           '<div class="input" data-go="input/%d">%s</div>' % (index, escape(entry.get('input', ''))),
           '<div class="output%s" data-go="output/%d"><pre>%s</pre>'
           % (error, index, escape(entry.get('output', '')))]
    if entry.get('decimal'):
        out.append('<div class="decimal">≈ %s</div>' % escape(entry['decimal']))
    out.append('</div></div>')
    return ''.join(out)


def draft_html(draft):
    if not draft:
        return ''
    escape = codeview.escape
    error = ' error' if draft.get('error') else ''
    return ('<div class="draft" data-go="draft/0"><div class="expr">%s'
            '<span class="caret">▏</span></div>'
            '<div class="preview%s">%s</div></div>'
            % (escape(draft.get('text', '')), error, escape(draft.get('preview', ''))))


def tape_html(entries, draft=None):
    body = ''.join(entry_html(index, entry) for index, entry in enumerate(entries))
    if not entries and not (draft and draft.get('text')):
        body = codeview.message_html(EMPTY_TEXT)
    return body + draft_html(draft)
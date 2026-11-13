"""Render anything as HTML for a web page (the Console's feed, any tool).

    part = render.render(thing, section=0)     # Rendered(html, items, text)

    None                     nothing
    (html, items)            a codeview section, as built
    [codeview.Row, ...]      rows (tracebacks, hits, notes), as codeview draws them
    an exception             its traceback
    PIL / ui.Image / a matplotlib figure or pyplot
                             a picture (PNG, embedded)
    [dict, dict, ...]        a table (the first dict's keys are the columns)
    dict, list, tuple        pretty JSON
    a path to a file         a coloured preview of its first lines
    HTML                     as it is
    anything else            its text (str(), or repr() for objects)

items maps go ids to objects (for taps), as codeview's sections do; text is
the plain words (what a copy takes). section numbers the go ids, so parts
rendered with different numbers can share a page. Pure except for pictures
(which need PIL, ui or matplotlib); tests/smoke_render.py checks it.
"""
import base64
import html as html_lib
import io
import json
import os
import re
import traceback
from collections import namedtuple

from . import codeview
from .. import files


# --- Settings -------------------------------------------------------------

MAX_TEXT_LINES = 400             # longer text is cut, with "… n more lines"
MAX_TABLE_ROWS = 200
PREVIEW_LINES = 40               # lines of a file shown for a path


Rendered = namedtuple('Rendered', 'html items text')
TAG = re.compile(r'<[^>]+>')
STARTS_LIKE_HTML = re.compile(r'\s*<[a-zA-Z!/]')


def plain_text(html):
    return html_lib.unescape(TAG.sub('', html))


def looks_like_html(text):
    return bool(STARTS_LIKE_HTML.match(text)) and '>' in text


def pre(text, css='fd-pre'):
    lines = text.split('\n')
    hidden = len(lines) - MAX_TEXT_LINES
    more = ''
    if hidden > 0:
        text = '\n'.join(lines[:MAX_TEXT_LINES])
        more = '<div class="note">… %d more line%s</div>' % (hidden, '' if hidden == 1 else 's')
    return '<pre class="%s">%s</pre>%s' % (css, codeview.escape(text), more)


def png_bytes(thing):
    """PNG data for a picture, or None when thing is not one."""
    try:
        if hasattr(thing, 'savefig'):                     # a figure, or pyplot itself
            buffer = io.BytesIO()
            thing.savefig(buffer, format='png', bbox_inches='tight')
            return buffer.getvalue()
        if hasattr(thing, 'save') and hasattr(thing, 'mode') and hasattr(thing, 'size'):
            buffer = io.BytesIO()                         # PIL
            thing.save(buffer, 'PNG')
            return buffer.getvalue()
        if type(thing).__name__ == 'Image' and hasattr(thing, 'to_png'):
            return thing.to_png()                         # ui.Image
    except Exception:
        return None
    return None


def image_html(data):
    return '<img class="fd-img" src="data:image/png;base64,%s">' % (
        base64.b64encode(data).decode('ascii'))


def is_section(thing):
    return (isinstance(thing, tuple) and len(thing) == 2 and isinstance(thing[0], str)
            and isinstance(thing[1], dict))


def is_rows(thing):
    return (isinstance(thing, (list, tuple)) and bool(thing)
            and all(isinstance(row, codeview.Row) for row in thing))


def is_records(thing):
    return (isinstance(thing, (list, tuple)) and bool(thing)
            and all(isinstance(record, dict) for record in thing))


def table_html(records):
    columns = list(records[0].keys())
    shown = records[:MAX_TABLE_ROWS]
    out = ['<table class="fd-table"><tr>']
    out.extend('<th>%s</th>' % codeview.escape(str(column)) for column in columns)
    out.append('</tr>')
    for record in shown:
        out.append('<tr>')
        out.extend('<td>%s</td>' % codeview.escape(str(record.get(column, '')))
                   for column in columns)
        out.append('</tr>')
    out.append('</table>')
    if len(records) > len(shown):
        out.append('<div class="note">… %d more rows</div>' % (len(records) - len(shown)))
    lines = ['\t'.join(str(column) for column in columns)]
    lines.extend('\t'.join(str(record.get(column, '')) for column in columns) for record in shown)
    return ''.join(out), '\n'.join(lines)


def file_preview(path, section):
    content = files.read_text(path)
    if content is None:
        return None
    html, items = codeview.preview_section(section, os.path.basename(path), content,
                                           python=path.endswith('.py'), limit=PREVIEW_LINES,
                                           line_item=lambda number: None)
    return Rendered(html, items, content)


def render(thing, section=0):
    """Rendered(html, items, text) for thing (see the module notes)."""
    if thing is None:
        return Rendered('', {}, '')
    if is_section(thing):
        html, items = thing
        return Rendered(html, dict(items), plain_text(html))
    if is_rows(thing):
        rows = list(thing)
        html, items = codeview.rows_section(section, '', rows)
        return Rendered(html, items, '\n'.join(row.text for row in rows))
    if isinstance(thing, BaseException):
        text = ''.join(traceback.format_exception(type(thing), thing, thing.__traceback__))
        return Rendered(pre(text, 'fd-pre fd-error'), {}, text)
    data = png_bytes(thing)
    if data:
        return Rendered(image_html(data), {}, '[picture]')
    if is_records(thing):
        html, text = table_html(list(thing))
        return Rendered(html, {}, text)
    if isinstance(thing, (dict, list, tuple)):
        text = json.dumps(thing, indent=2, default=str, ensure_ascii=False)
        return Rendered(pre(text), {}, text)
    if isinstance(thing, bytes):
        thing = thing.decode('utf-8', 'replace')
    if isinstance(thing, str):
        stripped = thing.strip()
        if stripped and '\n' not in stripped and os.path.isfile(stripped):
            preview = file_preview(stripped, section)
            if preview is not None:
                return preview
        if looks_like_html(thing):
            return Rendered(thing, {}, plain_text(thing))
        return Rendered(pre(thing), {}, thing)
    text = repr(thing)
    return Rendered(pre(text), {}, text)
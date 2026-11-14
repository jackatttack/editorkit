"""Feed: a scrolling history of entries, each a card (the Console's page).

    feed = tiles.Feed(window, on_pick=picked)        # picked gets your own items
    entry = feed.add('main.py', status='running', detail='whole script')
                                                     # a card: status, title; detail, note, time below
    entry.append('a line of output')                 # anything editorkit.render takes
    entry.append(figure)
    entry.finish('done', note='0.42 s')              # ✓ ✗ ■ by status

Each entry's header has 📋 (copy its text), ▾ (fold to the header) and ✕
(remove). Parts appended to the newest entry go straight onto the page,
so streaming output never redraws it; the page follows to the end. The
last `keep` entries are kept. Lines wrap to the window (codeview.WRAP_CSS).
"""
import json
import re
import time
from collections import namedtuple

from .. import codeview, prose, render
from .code import Code


# --- Settings -------------------------------------------------------------

KEEP_ENTRIES = 50
STATUS_MARKS = {'running': '⏳', 'done': '✓', 'error': '✗', 'stopped': '■'}
ACTIONS = (('copy', '📋'), ('fold', None), ('remove', '✕'))   # fold shows ▾ or ▸

FeedAction = namedtuple('FeedAction', 'kind entry')

FEED_CSS = """
.fd-head { margin: 16px 0 6px 0; padding: 9px 12px; background: var(--wash);
    border-radius: 12px; font: 600 15px -apple-system, sans-serif; }
.fd-head.folded { opacity: 0.75; }
.fd-row { display: flex; align-items: center; gap: 8px; }
.fd-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fd-meta { font: 13px -apple-system, sans-serif; color: var(--muted); margin-top: 3px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fd-act { padding: 3px 10px; border-radius: 10px; background: var(--wash-strong);
    cursor: pointer; font-weight: normal; }
.fd-part { margin-left: 8px; padding: 0 0 0 12px;
    border-left: 1px solid var(--rule); }
/* Printed lines arrive as one codeview section per beat: inside a card they
   run together as one stream instead of floating in separate blocks. */
.fd-part .file { margin: 0; }
.fd-part .block { margin: 0; padding: 0; background: none; border-radius: 0; }
.fd-part .path:empty { display: none; }
/* Printed lines have no line numbers: no empty gutter pushing them right. */
.fd-part .ln:empty { flex: 0 0 4px; min-width: 0; padding: 0; }
.fd-pre { font: 13px Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere;
    margin: 4px 0; }
.fd-error { color: #FF6B6B; }
.fd-img { max-width: 100%; border-radius: 10px; display: block; margin: 8px 0; }
.fd-part .ek-prose { padding: 6px 4px 2px; font-size: 15px; }
/* show()n dicts stay side by side even in a narrow Console: values are short. */
.fd-part .ek-terms { display: grid; }
.fd-part .ek-terms dd { margin: 0; }
"""


class Entry:
    """One card in a Feed. Use feed.add() to make one."""

    def __init__(self, feed, number, title, status=None, detail=''):
        self.feed = feed
        self.number = number
        self.title = title
        self.status = status
        self.detail = detail         # what ran ('whole script', 'lines 3-5'), on the meta line
        self.note = ''
        self.started = time.time()
        self.parts = []              # render.Rendered, in order
        self.folded = False

    def append(self, thing):
        self.feed.append(self, thing)
        return self

    def finish(self, status, note=''):
        self.feed.finish(self, status, note)
        return self

    def text(self):
        return '\n'.join(part.text for part in self.parts if part.text)


def head_html(entry, ids):
    """The entry's header row: status mark, title, time and note, then the
    actions (their items are FeedActions). Pure."""
    buttons = []
    for kind, label in ACTIONS:
        if kind == 'fold':
            label = '▸' if entry.folded else '▾'
        go = codeview.go_attribute(ids.go(FeedAction(kind, entry.number)))
        buttons.append('<span class="fd-act"%s>%s</span>' % (go, label))
    mark = STATUS_MARKS.get(entry.status, '')
    when = time.strftime('%H:%M:%S', time.localtime(entry.started))
    meta = ' · '.join(part for part in (entry.detail, entry.note, when) if part)
    return ('<div class="fd-head%s" id="fdh%d"><div class="fd-row">'
            '<span class="fd-title">%s</span>%s</div>'
            '<div class="fd-meta">%s</div></div>' % (
                ' folded' if entry.folded else '', entry.number,
                codeview.escape(('%s %s' % (mark, entry.title)).strip()),
                ''.join(buttons), codeview.escape(meta)))


GO_ID = re.compile(r'data-go="([^"]*)"')


def namespaced(html, items, prefix):
    """html and items with every go id given prefix, so a part built
    elsewhere (Search's results, say) cannot clash with another card's ids.
    Pure."""
    if not items:
        return html, items
    html = GO_ID.sub(lambda match: 'data-go="%s%s"' % (prefix, match.group(1)), html)
    return html, dict((prefix + key, value) for key, value in items.items())


def copy_text(text):
    """To the clipboard through editorkit.clip, never the clipboard module."""
    from ... import clip
    clip.set_text(text)


class Feed(Code):

    def __init__(self, window, on_pick=None, keep=KEEP_ENTRIES, extra_css='', **options):
        self.user_pick = on_pick
        self.keep = keep
        self.entries = []
        self.next_number = 1
        self.next_section = 1
        options.setdefault('fresh_on_grow', True)
        Code.__init__(self, window, on_pick=self.picked,
                      extra_css=codeview.WRAP_CSS + prose.CSS + FEED_CSS + extra_css,
                      **options)

    # --- Building ---------------------------------------------------------

    def take_section(self):
        number = self.next_section
        self.next_section += 1
        return number

    def head_section(self, entry):
        ids = codeview.SectionIds(self.take_section())
        return head_html(entry, ids), ids.items

    def add(self, title, thing=None, status=None, detail=''):
        """A new entry at the end; returns it."""
        entry = Entry(self, self.next_number, title, status, detail)
        self.next_number += 1
        self.entries.append(entry)
        if len(self.entries) > self.keep:
            del self.entries[:-self.keep]
            self.redraw()
        else:
            self.add_section(self.head_section(entry))
        if thing is not None:
            self.append(entry, thing)
        self.scroll_to_end()
        return entry

    def append(self, entry, thing):
        section = self.take_section()
        part = render.render(thing, section)
        if not part.html:
            return
        html, items = namespaced(part.html, part.items, 'p%d-' % section)
        part = render.Rendered(html, items, part.text)
        entry.parts.append(part)
        if entry not in self.entries or entry.folded:
            return
        if entry is self.entries[-1]:
            self.add_section(('<div class="fd-part">%s</div>' % part.html, part.items))
            self.scroll_to_end()
        else:
            self.redraw()

    def finish(self, entry, status, note=''):
        entry.status = status
        entry.note = note
        if entry in self.entries:
            self.redraw()
            if entry is self.entries[-1]:
                self.scroll_to_end()

    def clear(self):
        self.entries = []
        self.set_html('')

    def fold_all(self):
        """Fold every entry to its header (the Console does this when a new
        run starts, so the newest output has the room)."""
        if all(entry.folded for entry in self.entries):
            return
        for entry in self.entries:
            entry.folded = True
        self.redraw()

    def redraw(self):
        pieces, items = [], {}
        for entry in self.entries:
            html, head_items = self.head_section(entry)
            pieces.append(html)
            items.update(head_items)
            if entry.folded:
                continue
            for part in entry.parts:
                pieces.append('<div class="fd-part">%s</div>' % part.html)
                items.update(part.items)
        self.set_section((''.join(pieces), items))

    def scroll_to_end(self):
        self.run('window.scrollTo(0, document.body.scrollHeight)')

    # --- Taps ---------------------------------------------------------------

    def entry_numbered(self, number):
        for entry in self.entries:
            if entry.number == number:
                return entry
        return None

    def picked(self, item):
        if isinstance(item, FeedAction):
            entry = self.entry_numbered(item.entry)
            if entry is None:
                return
            if item.kind == 'copy':
                copy_text(entry.text())
            elif item.kind == 'fold':
                entry.folded = not entry.folded
                self.redraw()
            elif item.kind == 'remove':
                self.entries.remove(entry)
                self.redraw()
            return
        if self.user_pick is not None:
            self.user_pick(item)
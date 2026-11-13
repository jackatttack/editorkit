"""📖 Docs: Pythonista's own documentation, searched and read as cards.

Pythonista ships it in its app bundle: Documentation.inv (plain text, one
line per documented name: name, kind, page) and Documentation.zip (the
Sphinx HTML). Docs reads them, it does not display them: each entry's own
part of its page (Sphinx marks it by id) is pulled out of the zip and shown
in the card kit, themed like every other tool. Nothing is unpacked to disk;
the last few pages read are kept in memory.

    [ Search the docs ]
    ┌ ui.View ───────────────┐
    │ class                  │
    │ A rectangular area…    │      a tap: its signature and text as cards,
    └────────────────────────┘      ◀ Results and Insert (the name at the cursor)

With nothing typed, Pythonista's own modules are listed, each with its
summary. The search and the reading of pages are docs_index.py (pure).

    from editorkit_toolbox import docs
    docs.open_docs()
"""
import os
import time
import traceback
import zipfile
from collections import OrderedDict

import editorkit as ek
from editorkit import layouts
from editorkit.web import cards as card_kit
from editorkit.web import tiles as web_tiles

from . import docs_index


# --- Settings -------------------------------------------------------------

TITLE = 'Docs'
EMOJI = '📖'
WINDOW_KEY = 'deck-docs'
TYPING_PAUSE = 0.25
SUMMARY_COUNT = 12           # results that show their first sentence (each reads its page)
PAGES_KEPT = 8               # pages kept in memory after reading
RESULT_WIDTH = 260
CODE_LINES = 400             # a code block shows this many lines before "… n more"
START_ZOOM = 0.9
STARTERS = ('ui', 'scene', 'editor', 'console', 'dialogs', 'objc_util', 'sound',
            'photos', 'clipboard', 'keyboard', 'keychain', 'motion', 'location',
            'notification', 'appex', 'canvas', 'speech', 'reminders', 'contacts')
KIND_NAMES = {'mod': 'module'}
MEMBER_KINDS = ('method', 'attribute', 'classmethod', 'staticmethod', 'property')

CSS = """
.dc { font: 14px -apple-system, sans-serif; line-height: 1.45; color: var(--text);
    overflow-wrap: anywhere; min-width: 0; }
.dc img { max-width: 100%; height: auto; }
.dc table { display: block; max-width: 100%; overflow-x: auto; }
.dc .ek-code { margin: 8px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.dc-one .ek-grid { grid-template-columns: minmax(0, 1fr) !important; }
.dc p { margin: 6px 0; }
.dc code, .dc pre, .dc tt, .dc-sig { font-family: Menlo, monospace; font-size: 13px; }
.dc pre { background: var(--wash); padding: 8px; border-radius: 6px; white-space: pre-wrap; }
.dc dl { margin: 8px 0; }
.dc dt { font-family: Menlo, monospace; font-size: 13px; color: var(--accent); margin-top: 10px; }
.dc dd { margin-left: 12px; }
.dc h1, .dc h2, .dc h3 { font-size: 15px; margin: 12px 0 4px; }
.dc-link { color: var(--accent); }
.dc-sig { color: var(--accent); white-space: pre-wrap; }
.dc-kind { font: 12px -apple-system, sans-serif; color: var(--muted); margin-bottom: 4px; }
"""


# --- The bundle: the inventory and the zip (loaded once) ----------------------

_loaded = {}


def bundle_path(name):
    from objc_util import ObjCClass
    return os.path.join(str(ObjCClass('NSBundle').mainBundle().resourcePath()), name)


def entries():
    if 'entries' not in _loaded:
        with open(bundle_path('Documentation.inv'), encoding='utf-8', errors='replace') as handle:
            _loaded['entries'] = docs_index.parse(handle.read())
    return _loaded['entries']


def archive():
    if 'archive' not in _loaded:
        _loaded['archive'] = zipfile.ZipFile(bundle_path('Documentation.zip'))
        _loaded['pages'] = OrderedDict()
    return _loaded['archive']


def read_page(page):
    """A page's HTML from the zip ('' when missing); the last few are kept."""
    zipped = archive()
    pages = _loaded['pages']
    if page in pages:
        pages.move_to_end(page)
        return pages[page]
    try:
        text = zipped.read(page).decode('utf-8', 'replace')
    except KeyError:
        text = ''
    pages[page] = text
    while len(pages) > PAGES_KEPT:
        pages.popitem(last=False)
    return text


def section_of(entry):
    """(signature HTML, body HTML) of an entry's part of its page."""
    return docs_index.find_section(read_page(entry.page), entry.name)


def kind_name(entry):
    return KIND_NAMES.get(entry.kind, entry.kind)


def insert_name(entry):
    """What Insert types: a member's own name (add_subview), else the full name."""
    if entry.kind in MEMBER_KINDS:
        return entry.name.rsplit('.', 1)[-1]
    return entry.name


# --- Pages of cards -------------------------------------------------------------

def result_card(entry, with_summary):
    body = '<div class="dc-kind">%s</div>' % card_kit.escape(kind_name(entry))
    if with_summary:
        try:
            line = docs_index.summary(section_of(entry)[1])
        except Exception:
            line = ''
        if line:
            body += '<div class="dc">%s</div>' % card_kit.escape(line)
    return card_kit.Card(entry.name, item=entry, body=body)


def results_page(label, found):
    page = card_kit.Page()
    page.note(label)
    page.grid([result_card(entry, index < SUMMARY_COUNT) for index, entry in enumerate(found)],
              min_width=RESULT_WIDTH)
    return page


def detail_page(entry):
    signature, body = section_of(entry)
    page = card_kit.Page()
    page.buttons([card_kit.Action('◀ Results', ('back', None)),
                  card_kit.Action('Insert %s' % insert_name(entry), ('insert', insert_name(entry)),
                                  look='go')])
    page.heading(entry.name)
    page.note('%s · %s' % (kind_name(entry), entry.page))
    grid = []
    if signature:
        grid.append(card_kit.Card('Signature', body='<div class="dc-sig">%s</div>'
                                  % docs_index.clean(signature)))
    if body:
        text = docs_index.replace_code(docs_index.clean(body), render_code)
    else:
        text = '<p>No text found for this entry.</p>'
    grid.append(card_kit.Card('About', body='<div class="dc">%s</div>' % text))
    # One column that always fits the window: the text wraps, never runs off.
    page.parts.append('<div class="dc-one">')
    page.grid(grid, min_width=RESULT_WIDTH)
    page.parts.append('</div>')
    return page


def render_code(text):
    """A docs code block in the card kit's own colouring (the theme's syntax colours)."""
    return card_kit.code(text, lines=CODE_LINES, python=True)


# --- The tool -----------------------------------------------------------------

class DocsTool:

    def __init__(self, window):
        self.window = window
        self.search_due = None
        self.loaded = False
        self.last_results = None     # the results page, for ◀ Results
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                     zoom_key='docs', extra_css=CSS)
        self.view = layouts.query_list(window, 'Search the docs', on_change=self.typed,
                                       body=self.cards, compact_in_dock=False)
        window.every(self.tick)
        self.cards.say('Loading the docs…')

    def typed(self, field, text):
        self.search_due = time.time() + TYPING_PAUSE

    def look_up(self, names, term):
        """Open at the first of names the docs know (a tool asking for a name), with a
        search for term behind it for ◀ Results; just the search when none
        of the names is known."""
        try:
            everything = entries()
            archive()
        except Exception as problem:
            self.cards.say("Pythonista's docs could not be read: %s" % problem)
            return
        self.loaded = True
        found = docs_index.named(everything, list(names))
        if term:
            self.view.field.set_value(term)
            results = docs_index.search(everything, term)
            label = '%d for “%s”' % (len(results), term) if results else 'Nothing for “%s”' % term
            self.last_results = results_page(label, results)
        if found:
            self.cards.show(detail_page(found[0]))
            self.window.set_title(found[0].name.rsplit('.', 1)[-1])
        elif self.last_results is not None:
            self.cards.show(self.last_results)
        self.search_due = None       # the field was set by us: no search over the top

    def tick(self, *ignored):
        if not self.loaded:
            self.loaded = True
            try:
                entries()
                archive()
            except Exception as problem:
                self.cards.say("Pythonista's docs could not be read: %s" % problem)
                return
            self.search_due = time.time()
        if self.search_due is not None and time.time() >= self.search_due:
            self.search_due = None
            self.show_found(self.view.field.value().strip())

    def show_found(self, term):
        if term:
            found = docs_index.search(entries(), term)
            label = '%d for “%s”' % (len(found), term) if found else 'Nothing for “%s”' % term
        else:
            found = docs_index.named(entries(), STARTERS)
            label = "Pythonista's modules"
        self.last_results = results_page(label, found)
        self.cards.show(self.last_results)
        self.window.set_title(TITLE)

    def picked(self, item):
        """A card (an entry: its page of cards), ◀ Results, or Insert. A
        failure shows on the page instead of vanishing."""
        try:
            if isinstance(item, docs_index.Entry):
                self.view.field.unfocus()
                self.cards.show(detail_page(item))
                self.window.set_title(item.name.rsplit('.', 1)[-1])
            elif item[0] == 'back' and self.last_results is not None:
                self.cards.show(self.last_results)
                self.window.set_title(TITLE)
            elif item[0] == 'insert':
                ek.insert(item[1])
        except Exception as problem:
            traceback.print_exc()
            self.cards.say('Could not open that: %s' % problem)


def open_docs(names=(), term=''):
    """Open Docs over the code (or bring it back). names: dotted names to
    open at, the first the docs know (a tool asking for a name); term: a search behind it."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = DocsTool(window)
    window.docs_tool = tool
    window.show()
    if names or term:
        tool.look_up(names, term)
    return tool
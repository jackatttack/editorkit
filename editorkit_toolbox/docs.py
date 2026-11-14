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
from editorkit.web import prose
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

def result_row(page, entry, with_summary):
    """An entry as a docs-style row: its signature line (kind, module part,
    name), then its first sentence. The whole row opens it."""
    module, _dot, name = entry.name.rpartition('.')
    kind = kind_name(entry)
    signature = prose.signature(name, None, prefix=module + '.' if module else '',
                                kind='' if kind == 'module' and not module else kind)
    line = ''
    if with_summary:
        try:
            line = docs_index.summary(section_of(entry)[1])
        except Exception:
            line = ''
    return prose.row(signature, line, go=page.go(entry))


def results_page(label, found, title=None):
    """The results as one docs-style list: a heading (or the count as a small
    line), then a row per entry."""
    page = card_kit.Page()
    heading = [prose.heading(title, 2)] if title else [prose.meta(label)]
    rows = [result_row(page, entry, index < SUMMARY_COUNT) for index, entry in enumerate(found)]
    page.prose(*(heading + rows))
    return page


def detail_page(entry):
    """An entry as one article in the docs' own look (editorkit.web.prose):
    its name, its kind and page, the signature, then the text, every code
    block with ⧉ Copy."""
    signature, body = section_of(entry)
    page = card_kit.Page()
    page.buttons([card_kit.Action('◀ Results', ('back', None)),
                  card_kit.Action('Insert %s' % insert_name(entry), ('insert', insert_name(entry)),
                                  look='go')])
    blocks = [prose.heading(entry.name, 1),
              prose.meta('%s · %s' % (kind_name(entry), entry.page))]
    if signature:
        blocks.append('<div class="ek-sig">%s</div>' % docs_index.clean(signature))
    if body:
        blocks.append(docs_index.replace_code(docs_index.clean(body), render_code))
    else:
        blocks.append(prose.text('No text found for this entry.'))
    page.prose(*blocks)
    return page


def render_code(text):
    """A docs code block in the theme's syntax colours, whole, with ⧉ Copy."""
    return prose.code(text)


# --- The tool -----------------------------------------------------------------

class DocsTool:

    def __init__(self, window, field_view=None):
        """field_view: another tool's query_list whose field this shares (Explain's
        Docs tab); the owner adds self.cards as a page and routes typing here."""
        self.window = window
        self.shared = field_view is not None
        self.query = ''              # what was typed for the docs (the field may be shared)
        self.search_due = None
        self.loaded = False
        self.last_results = None     # the results page, for ◀ Results
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                     zoom_key='docs', extra_css=CSS)
        if self.shared:
            self.view = field_view
        else:
            self.view = layouts.query_list(window, 'Search the docs', on_change=self.typed,
                                           body=self.cards, compact_in_dock=False)
        window.every(self.tick)
        self.cards.say('Loading the docs…')

    def typed(self, field, text):
        self.query = text
        self.search_due = time.time() + TYPING_PAUSE

    def set_title(self, title):
        """The window's title, when the window is Docs' own."""
        if not self.shared:
            self.window.set_title(title)

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
            self.query = term
            self.view.field.set_value(term)
            results = docs_index.search(everything, term)
            label = '%d for “%s”' % (len(results), term) if results else 'Nothing for “%s”' % term
            self.last_results = results_page(label, results)
        if found:
            self.cards.show(detail_page(found[0]))
            self.set_title(found[0].name.rsplit('.', 1)[-1])
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
            self.show_found(self.query.strip())

    def show_found(self, term):
        if term:
            found = docs_index.search(entries(), term)
            label = '%d for “%s”' % (len(found), term) if found else 'Nothing for “%s”' % term
        else:
            found = docs_index.named(entries(), STARTERS)
            label = "Pythonista's modules"
        self.last_results = results_page(label, found, title=None if term else label)
        self.cards.show(self.last_results)
        self.set_title(TITLE)

    def picked(self, item):
        """A card (an entry: its page of cards), ◀ Results, or Insert. A
        failure shows on the page instead of vanishing."""
        try:
            if isinstance(item, docs_index.Entry):
                self.view.field.unfocus()
                self.cards.show(detail_page(item))
                self.set_title(item.name.rsplit('.', 1)[-1])
            elif item[0] == 'back' and self.last_results is not None:
                self.cards.show(self.last_results)
                self.set_title(TITLE)
            elif item[0] == 'insert':
                ek.insert(item[1])
        except Exception as problem:
            traceback.print_exc()
            self.cards.say('Could not open that: %s' % problem)


def open_docs(names=(), term=''):
    """Open Explain on its 📖 Docs tab (or bring it back). names: dotted names
    to open at, the first the docs know (a tool asking for a name); term: a
    search behind it."""
    from . import explain
    tool = explain.open_explain(page=explain.DOCS_PAGE)
    if names or term:
        tool.docs.look_up(names, term)
    return tool.docs
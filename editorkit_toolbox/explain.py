"""❓ Explain: what is this, and how do I use it? (docs/QUESTION_TILE.txt)

Open it, then put the cursor on something or select some code. The screen
is small, so what matters comes first and the rest is a scroll away:

    header      the name and its signature; ⤵ inserts the name, ⤵() a call
    inputs      its parameters as chips (tap: insert name=); inside a call,
                the one you are on is lit
    docs        the docs for it, rendered in full, links live (they open
                here); 📖 Read on opens the whole docs page here, at this
                entry, to scroll for context. Your own names: Your code.
    examples    the docs' code examples for it, each with ⤵ Insert
    more        one quiet row: Used here ▸ (the hits, opened in place),
                🔎 Find in all files (the hub's Find), and Members ▸ and
                Defined in ▸ when there are no docs
    outline     selected lines: their classes, methods and functions
    names       nothing under the cursor: the line's names, then the names in
                the code on screen, as chips (tap one to explain it); only
                names a tap can explain: imports, builtins, your defs and classes

It looks again when the selection changes, or the cursor moves onto
another name or line, once typing has paused. Type a name in its field to
explain that instead. Everything tapped opens here, in place; ◀ (a chip at
the top, and a header button however far you scroll) goes back.
It never runs your code, and imports a module only when asked (a typed
name, a tap, or Load). Each facet is a plain function (tool, subject,
page) in FACETS.

    from editorkit_toolbox import explain
    explain.open_explain()
"""
import difflib
import importlib.util
import inspect
import json
import os
import re
import sys
import time
import traceback

import editorkit as ek
import codesense
from codesense import units

from . import docs, docs_index
from . import explain_subject as subjects
from . import lens_detect as detect
from .docs import card_kit, layouts, web_tiles   # the card kit, layouts and tiles Docs uses
from .lookup import describe, reachable, short_signature


# --- Settings -------------------------------------------------------------

TITLE = 'Explain'
EMOJI = '❓'
WINDOW_KEY = 'deck-explain'
FIELD_HINT = 'Explain a name, or follow the cursor'
WATCH_SECONDS = 0.3          # how often to look at the cursor and the selection
TYPING_PAUSE = 0.4           # a typed name is explained once typing pauses this long
CARD_WIDTH = 200
EXAMPLES_SHOWN = 3
EXAMPLE_LINES = 14
MEMBERS_SHOWN = 40
USAGES_SHOWN = 12
SOURCE_LINES = 24            # lines of a definition shown on its card
SOURCE_LIMIT = 200           # lines read for one definition
DOC_CHARACTERS = 1500        # a docstring is cut here
VALUE_CHARACTERS = 300       # a value's repr is cut here
DEFINITIONS_SHOWN = 3        # jedi's answers
SUGGESTIONS_SHOWN = 3        # did you mean
BACK_LABEL_LENGTH = 24
BACK_ICON = '◀'              # the header's back button, there while there is history
SCREEN_LINES = 30            # lines read around the cursor when the editor cannot say what shows
SCREEN_NAMES = 60            # names shown from the code on screen
NEVER_IMPORT = ('this', 'antigravity')     # modules that do something when imported
HINT = ('Put the cursor on a name, or select some code: Explain shows its docs, '
        'its inputs and examples.')
KIND_WORDS = {'name': 'name', 'attribute': 'member', 'call': 'inside a call',
              'def': 'definition', 'import': 'import', 'number': 'number',
              'colour': 'colour', 'string': 'string', 'comment': 'comment',
              'lines': 'selection', 'text': 'text', 'nothing': 'line', 'page': 'docs page'}
# Colour carries meaning, as in Snippets: a card's edge says what kind it is.
KIND_COLOURS = {'class': '#8E6CEF', 'function': '#27AE60', 'module': '#2D9CDB',
                'value': '#F2994A', 'number': '#F2994A', 'colour': '#F2994A',
                'docs': '#EB5757', 'page': '#EB5757', 'example': '#F2C94C',
                'file': '#56CCF2', 'call': '#F2C94C', 'selection': '#BB6BD9',
                'other': '#8A8A96'}
JEDI_KINDS = ('name', 'attribute', 'call', 'def', 'import')
CSS = '''
.xp-doc { white-space: pre-wrap; font-size: 13px; line-height: 1.35; margin: 0; }
.xp-swatch { height: 48px; border-radius: 10px; border: 1px solid var(--rule); margin-bottom: 6px; }
.xp-where { color: var(--muted); font-size: 12px; margin-top: 6px; }
.xp-go { text-decoration: underline; text-underline-offset: 2px; cursor: pointer; }
'''
LINK = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.DOTALL | re.IGNORECASE)
HREF = re.compile(r'href="([^"]*)"', re.IGNORECASE)
PAGE_SECTION = re.compile(r'<(section)\b[^>]*>|<(div)\b[^>]*class="section"[^>]*>', re.IGNORECASE)


# --- Helpers ----------------------------------------------------------------

def escape(text):
    return card_kit.escape(str(text))


def importable(root):
    """True when root is a module outside your scripts (standard library,
    Pythonista's modules, site-packages): safe to import, though maybe slow."""
    if not root or root in NEVER_IMPORT:
        return False
    try:
        spec = importlib.util.find_spec(root)
    except Exception:
        return False
    origin = (getattr(spec, 'origin', None) or '') if spec is not None else ''
    return spec is not None and not ('/Documents/' in origin and 'site-packages' not in origin)


def reach(dotted, may_import):
    """The object dotted names, when Python can reach it without running
    your code. A module not yet loaded is imported only when may_import."""
    root = dotted.split('.', 1)[0] if dotted else ''
    if not root or root in NEVER_IMPORT:
        return None
    if root not in sys.modules and not may_import:
        return None
    return reachable(dotted)


def kind_of(thing):
    if inspect.ismodule(thing):
        return 'module'
    if inspect.isclass(thing):
        return 'class'
    if callable(thing):
        return 'function'
    return '%s value' % type(thing).__name__


def colour_of(kind):
    if kind in KIND_COLOURS:
        return KIND_COLOURS[kind]
    if kind.endswith('value'):
        return KIND_COLOURS['value']
    return KIND_COLOURS['other']


def docs_name(module, qualified):
    """How the docs name something: builtins bare (dict.pop), Pythonista's
    private modules without their underscore (_ui -> ui)."""
    module = (module or '').lstrip('_')
    return qualified if module in ('', 'builtins') else '%s.%s' % (module, qualified)


def python_inputs(thing):
    """[(name, default or None)] from Python's own signature; None when
    Python cannot say (most built-in and Pythonista functions)."""
    try:
        parameters = inspect.signature(thing).parameters.values()
    except (TypeError, ValueError):
        return None
    found = []
    for parameter in parameters:
        if parameter.name in ('self', 'cls'):
            continue
        prefix = {parameter.VAR_POSITIONAL: '*', parameter.VAR_KEYWORD: '**'}.get(parameter.kind, '')
        default = None if parameter.default is parameter.empty else repr(parameter.default)
        found.append((prefix + parameter.name, default))
    return found


def call_text(name, inputs):
    """name(a, b): the inputs a call must give (no defaults, no * or **)."""
    needed = [input_name for input_name, default in inputs or ()
              if default is None and not input_name.startswith('*')]
    return '%s(%s)' % (name, ', '.join(needed))


def colour_css(rgba):
    red, green, blue = (int(round(part * 255)) for part in rgba[:3])
    alpha = rgba[3] if len(rgba) > 3 else 1.0
    return 'rgba(%d, %d, %d, %.3f)' % (red, green, blue, alpha)


def one_column(page, cards):
    """Cards of long text: one column that always fits the window (as Docs)."""
    page.parts.append('<div class="dc-one">')
    page.grid(cards, min_width=CARD_WIDTH)
    page.parts.append('</div>')


def page_body(html, anchor):
    """(signature, body) of a docs page's part named anchor, else the page's
    first section (the whole page, for a link to a page)."""
    if anchor:
        signature, body = docs_index.find_section(html, anchor)
        if body:
            return signature, body
    found = PAGE_SECTION.search(html)
    if found is None:
        return '', ''
    return '', docs_index.inner(html, found.start(), found.group(1) or found.group(2))


def docs_title(page_path):
    return "Pythonista's docs" if '/ios/' in page_path else 'Python docs'


def read_block(path, line):
    try:
        with open(path, encoding='utf-8') as handle:
            return subjects.block_at(handle.read(), line, SOURCE_LIMIT)
    except Exception:
        return ''


def last_part(subject):
    return subject.dotted.rsplit('.', 1)[-1] if subject.dotted else ''


# --- Facets -----------------------------------------------------------------

def header(tool, subject, page):
    """The name, its signature and kind, ⤵ to insert; Load, did you mean."""
    thing = tool.thing
    if subject.kind == 'lines':
        title = '%d lines selected' % (subject.text.strip('\n').count('\n') + 1)
    else:
        title = subject.dotted or subject.text.strip() or 'Line %d' % subject.line
    if len(title) > 60:
        title = title[:59] + '…'
    kind = kind_of(thing) if thing is not None else KIND_WORDS.get(subject.kind, subject.kind)
    bits = [kind]
    if subject.kind == 'page':
        bits.append(subject.value[0].rsplit('/', 1)[-1])
    if subject.line:
        bits.append('line %d' % subject.line)
    where = tool.scope_names(subject.line)
    if where:
        bits.append(' › '.join(where))
    body = ''
    if subject.kind == 'colour':
        body += '<div class="xp-swatch" style="background: %s"></div>' % colour_css(subject.value)
    signature = tool.docs_signature()
    if signature:
        body += '<div class="dc-sig">%s</div>' % signature
    elif thing is not None and callable(thing) and short_signature(thing):
        body += card_kit.code(last_part(subject) + short_signature(thing), lines=3)
    elif subject.kind in ('number', 'colour'):
        body += card_kit.code(subject.text, lines=1)
    body += '<div class="xp-where">%s</div>' % escape(' · '.join(bits))
    actions = []
    if thing is not None:
        name = last_part(subject)
        actions.append(card_kit.Action('⤵', ('insert', name)))
        if callable(thing):
            actions.append(card_kit.Action('⤵()', ('insert', call_text(name, tool.inputs))))
    colour = colour_of(kind if thing is not None else subject.kind)
    page.grid([card_kit.Card(title, body=body, colour=colour, actions=actions)],
              min_width=CARD_WIDTH)
    buttons = []
    if thing is None and subject.dotted:
        root = subject.dotted.split('.', 1)[0]
        if root not in sys.modules and importable(root):
            buttons.append(card_kit.Action('Load %s to explain it' % root, ('load',), look='go'))
    if buttons:
        page.buttons(buttons)
    if thing is None and '.' in subject.dotted:
        owner_name, _, last = subject.dotted.rpartition('.')
        owner = reach(owner_name, tool.explicit)
        if owner is not None:
            members = [member for member in dir(owner) if not member.startswith('_')]
            close = ([member for member in members if member.lower() == last.lower()]
                     or difflib.get_close_matches(last, members, SUGGESTIONS_SHOWN))
            if close:
                page.note('%s has no %s · did you mean' % (owner_name, last))
                page.chips([card_kit.Chip('%s.%s' % (owner_name, member),
                                          item=('explain', '%s.%s' % (owner_name, member)),
                                          colour=KIND_COLOURS['docs']) for member in close])


def inputs(tool, subject, page):
    """Its parameters as chips: tap to insert name=. Inside a call, jedi's
    answer lights the one the cursor is on."""
    found = list(tool.inputs or [])
    current = None
    answer = tool.answers.get('signature')
    if answer is not None and not answer.error and answer.items:
        call = answer.items[0]
        if not found:
            found = [(name, None) for name in call['params']]
        index = call.get('index')
        if index is not None and index < len(call['params']):
            current = call['params'][index]
    if not found:
        return
    chips = []
    for name, default in found:
        bare = name.lstrip('*')
        label = name if default is None else '%s=%s' % (name, default)
        item = ('param', bare) if not name.startswith('*') else None
        chips.append(card_kit.Chip(label, item=item, colour=KIND_COLOURS['call'],
                                   on=bare == current))
    page.note('INPUTS · tap to insert name=')
    page.chips(chips)


def docs_facet(tool, subject, page):
    """The docs, in full, links live; else your own code; else the docstring."""
    cards = []
    if subject.kind == 'page':
        page_path, anchor, focus = subject.value
        try:
            _, body = page_body(docs.read_page(page_path), '' if focus else anchor)
        except Exception:
            body = ''
        text = tool.rich(body, page_path, page) if body else 'Nothing found at this link.'
        cards.append(card_kit.Card(docs_title(page_path), body='<div class="dc">%s</div>' % text,
                                   colour=KIND_COLOURS['docs']))
        one_column(page, cards)
        return
    if tool.entry is not None and tool.entry_body:
        cards.append(card_kit.Card(docs_title(tool.entry.page),
                                   body='<div class="dc">%s</div>'
                                   % tool.rich(tool.entry_body, tool.entry.page, page),
                                   colour=KIND_COLOURS['docs']))
        one_column(page, cards)
        page.buttons([card_kit.Action('📖 Read on in the docs',
                                      ('read', tool.entry.page, tool.entry.name))])
        return
    name = last_part(subject)
    if name and tool.text and subject.kind != 'lines':
        for line, index, text in subjects.definitions(tool.text, name)[:2]:
            stripped = text.lstrip()
            kind = ('class' if stripped.startswith('class') else
                    'function' if stripped.startswith(('def', 'async')) else 'value')
            cards.append(card_kit.Card('Your code · line %d' % line, item=('jump', index),
                                       body=card_kit.code(subjects.block_at(tool.text, line,
                                                                            SOURCE_LIMIT),
                                                          lines=SOURCE_LINES),
                                       colour=colour_of(kind)))
    thing = tool.thing
    if not cards and thing is not None:
        if kind_of(thing).endswith('value'):
            cards.append(card_kit.Card('Value', body='<pre class="xp-doc">%s</pre>'
                                       % escape(repr(thing)[:VALUE_CHARACTERS]),
                                       colour=KIND_COLOURS['value']))
        else:
            text = inspect.getdoc(thing) or ''
            if text:
                if len(text) > DOC_CHARACTERS:
                    text = text[:DOC_CHARACTERS - 1] + '…'
                cards.append(card_kit.Card('Docstring', body='<pre class="xp-doc">%s</pre>'
                                           % escape(text), colour=colour_of(kind_of(thing))))
    if cards:
        one_column(page, cards)


def examples(tool, subject, page):
    """The docs' code examples for it, each with ⤵ Insert: the entry's own,
    else the page's examples that use its name."""
    if tool.entry is None or subject.kind == 'page':
        return
    found = subjects.code_blocks(tool.entry_body or '')
    if not found:
        try:
            html = docs.read_page(tool.entry.page)
        except Exception:
            html = ''
        word = re.compile(r'\b%s\b' % re.escape(last_part(subject)))
        found = [block for block in subjects.code_blocks(html) if word.search(block)]
    found = [block for block in found if block.strip()][:EXAMPLES_SHOWN]
    if not found:
        return
    page.note('EXAMPLES · ⤵ inserts one')
    one_column(page, [card_kit.Card('Example %d' % number,
                                    body=card_kit.code(block, lines=EXAMPLE_LINES),
                                    colour=KIND_COLOURS['example'],
                                    actions=[card_kit.Action('⤵ Insert',
                                                             ('insert', subjects.insertable(block)))])
                      for number, block in enumerate(found, 1)])


def more(tool, subject, page):
    """One quiet row: where it is used here (opened in place), Find in all
    files (the hub's Find), and with no docs its members and definition."""
    if not subject.dotted or subject.kind == 'page':
        return
    name = last_part(subject)
    text = tool.text or ''
    defined_lines = set(line for line, _, _ in subjects.definitions(text, name))
    used = [hit for hit in subjects.usages(text, name, USAGES_SHOWN)[0]
            if hit[0] not in defined_lines]
    thing = tool.thing
    show_members = tool.entry is None and (inspect.isclass(thing) or inspect.ismodule(thing))
    definition = tool.answers.get('definition')
    elsewhere = []
    if tool.entry is None and definition is not None and not definition.error:
        current = os.path.realpath(ek.current_file() or '')
        elsewhere = [found for found in definition.items[:DEFINITIONS_SHOWN]
                     if found.get('path') and os.path.realpath(found['path']) != current]

    def toggle(label, key, count):
        arrow = '▾' if key in tool.opened else '▸'
        return card_kit.Action('%s · %d %s' % (label, count, arrow), ('toggle', key))

    buttons = []
    if used:
        buttons.append(toggle('Used here', 'used', len(used)))
    # The whole dotted name, as written: sys.copyright, not every copyright.
    buttons.append(card_kit.Action('🔎 Find %s in all files' % subject.dotted,
                                   ('find', subject.dotted)))
    if show_members:
        buttons.append(toggle('Members', 'members',
                              len([member for member in dir(thing) if not member.startswith('_')])))
    if elsewhere:
        buttons.append(toggle('Defined in', 'defined', len(elsewhere)))
    page.note('MORE')
    page.buttons(buttons)
    if used and 'used' in tool.opened:
        page.grid([card_kit.Card('line %d' % line, item=('jump', index),
                                 body=card_kit.code(hit_text.strip(), lines=1),
                                 colour=KIND_COLOURS['file'])
                   for line, index, hit_text in used], min_width=CARD_WIDTH)
    if show_members and 'members' in tool.opened:
        cards = []
        for member in [member for member in dir(thing) if not member.startswith('_')][:MEMBERS_SHOWN]:
            try:
                member_kind = kind_of(getattr(thing, member))
            except Exception:
                member_kind = 'member'
            cards.append(card_kit.Card(member, item=('explain', '%s.%s' % (subject.dotted, member)),
                                       body=card_kit.text(describe(thing, member, member_kind)),
                                       colour=colour_of(member_kind),
                                       actions=[card_kit.Action('⤵', ('insert', member))]))
        page.grid(cards, min_width=CARD_WIDTH)
    if elsewhere and 'defined' in tool.opened:
        cards = []
        for found in elsewhere:
            path, line = found['path'], found.get('line')
            block = read_block(path, line) if line else ''
            body = card_kit.code(block or found.get('description', ''), lines=SOURCE_LINES)
            body += '<div class="xp-where">%s</div>' % escape(
                '%s · line %s' % (os.path.basename(path), line))
            cards.append(card_kit.Card(found.get('name', '?'),
                                       item=('open', path, line) if line else None, body=body,
                                       colour=KIND_COLOURS['file']))
        one_column(page, cards)


def outline(tool, subject, page):
    if subject.kind != 'lines' or not tool.text:
        return
    first = subjects.line_start(tool.text, subject.line)
    found = subjects.outline(tool.text[first:subject.end])
    if not found:
        return
    page.note('IN THE SELECTION · %d · tap to jump' % len(found))
    cards = []
    for kind, name, signature, doc, line in found:
        index = subjects.line_start(tool.text, subject.line + line - 1)
        body = card_kit.code(name.rsplit('.', 1)[-1] + signature, lines=2)
        if doc:
            body += card_kit.text(doc)
        colour = KIND_COLOURS['class'] if kind == 'class' else KIND_COLOURS['function']
        cards.append(card_kit.Card('%s %s' % (kind, name), item=('jump', index), body=body,
                                   colour=colour))
    page.grid(cards, min_width=CARD_WIDTH)


def names(tool, subject, page):
    """Names as chips, only those a tap can explain (an import's, a builtin,
    your own def or class): a selection's; else, with nothing under the
    cursor, its line's and then the rest of the code on screen."""
    if subject.kind in ('number', 'colour', 'page') or (subject.dotted and subject.kind != 'lines'):
        return
    found, imported, defined = tool.code_index()

    def useful(first, last):
        return subjects.useful_names([hit for hit in found if first <= hit[0] <= last],
                                     imported, defined)

    if subject.kind == 'lines':
        last = subject.line + subject.text.strip('\n').count('\n')
        name_chips(page, 'NAMES · tap one to explain it', useful(subject.line, last), defined)
        return
    if not subject.line:
        page.note(HINT)
        return
    on_line = useful(subject.line, subject.line)
    first, last = tool.screen_lines(subject.line)
    on_screen = [name for name in useful(first, last) if name not in on_line][:SCREEN_NAMES]
    if not on_line and not on_screen:
        page.note(HINT)
        return
    name_chips(page, 'THIS LINE · tap one to explain it', on_line, defined)
    name_chips(page, 'ON SCREEN · lines %d-%d' % (first, last), on_screen, defined)


def name_chips(page, label, found, defined=()):
    """A note and a row of name chips, each explaining its name when tapped:
    your own defs and classes in the function colour, the rest as library."""
    if found:
        page.note(label)
        page.chips([card_kit.Chip(name, item=('explain', name),
                                  colour=(KIND_COLOURS['function']
                                          if name.split('.', 1)[0] in defined
                                          else KIND_COLOURS['other']))
                    for name in found])


FACETS = [header, inputs, docs_facet, examples, more, outline, names]


# --- The tool -----------------------------------------------------------------

class ExplainTool:

    def __init__(self, window):
        self.window = window
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom_key='explain',
                                     extra_css=docs.CSS + CSS)
        self.view = layouts.query_list(window, FIELD_HINT, on_change=self.typed,
                                       body=self.cards, compact_in_dock=False)
        self.subject = None
        self.thing = None            # the subject's Python object, when reachable
        self.entry = None            # its docs entry, when there is one
        self.entry_body = ''         # that entry's HTML
        self.inputs = None           # [(name, default)] when known
        self.names = None            # every docs entry's name (links to them explain here)
        self.opened = set()          # More's sections opened on this page
        self.scroll_target = None    # an id to scroll to once the page shows
        self.history = []            # subjects before the one showing (◀)
        self.explicit = False        # asked for by a tap or a typed name: may import
        self.text = ''               # the code the subject was read from
        self.answers = {}            # jedi's answers for this subject: kind -> Answer
        self.version = 0
        self.seen = None             # what was last explained at the cursor
        self.text_length = None
        self.next_check = 0.0
        self.typed_due = None
        self.index_key = None        # the code the symbol index was built from
        self.code_key = None         # the code the name chips were read from
        self.code_found = ([], set(), set())
        self.index = None
        self.assistant = codesense.Assistant(codesense.Ledger())
        self.assistant.start()
        window.every(self.tick)
        self.cards.say(HINT)

    # --- Looking ------------------------------------------------------------

    def typed(self, field, text):
        self.typed_due = time.time() + TYPING_PAUSE

    def look_again(self):
        self.seen = None
        self.text_length = None
        self.next_check = 0.0

    def screen_lines(self, line):
        """(first, last): the lines of code on screen; else SCREEN_LINES from
        a little above line (an older editorkit, or no code view)."""
        try:
            shown = ek.visible_lines() if hasattr(ek, 'visible_lines') else None
        except Exception:
            shown = None
        if shown:
            return tuple(shown)
        first = max(1, line - SCREEN_LINES // 3)
        return first, first + SCREEN_LINES - 1

    def code_index(self):
        """(names by line, imported, defined) for the code, worked out once per
        text: the name chips read from it."""
        if self.code_key != self.text:
            found = subjects.code_names(self.text or '')
            imported, defined = subjects.bound_names(self.text or '')
            self.code_found = (found, imported, defined)
            self.code_key = self.text
        return self.code_found

    def tick(self, *ignored):
        now = time.time()
        self.take_answers()
        if self.typed_due is not None and now >= self.typed_due:
            self.typed_due = None
            term = self.view.field.value().strip()
            if term:
                self.history = []
                self.explain_name(term, push=False)
            else:
                self.look_again()
        if self.view.field.value().strip():
            return                   # a typed name holds the page
        if now < self.next_check:
            return
        self.next_check = now + WATCH_SECONDS
        self.watch()

    def watch(self):
        """Explain again when the selection changes, or the cursor moves onto
        another name or line, but not while typing (the text keeps changing)."""
        text = ek.text() or ''
        if len(text) != self.text_length:
            self.text_length = len(text)
            return
        start, end = tuple(ek.selection() or (0, 0))
        if start != end:
            key = ('selection', start, end)
        else:
            name, span = subjects.dotted_at(text, start)
            line = subjects.line_of(text, start)
            # On no name the page lists the code on screen, so scrolling counts.
            shown = None if name else self.screen_lines(line)
            key = ('cursor', line, span if name else None, shown)
        if key == self.seen:
            return
        self.seen = key
        self.explain_here(text, start, end)

    def explain_here(self, text, start, end):
        subject = subjects.subject_at(text, start, end)
        if subject.kind != 'lines':
            thing = detect.what_is_here(text, start, end)
            if thing.kind in ('number', 'colour'):
                subject = subject._replace(kind=thing.kind, text=thing.text, start=thing.start,
                                           end=thing.end, value=thing.value, dotted='')
        self.history = []
        self.explicit = False
        self.text = text
        self.answers = {}
        self.subject = subject
        if subject.kind in JEDI_KINDS and subject.dotted:
            self.ask(text, start)
        self.render()

    def go_to(self, subject):
        """Show subject here, keeping the one before for ◀."""
        if self.subject is not None:
            self.history.append(self.subject)
        self.explicit = True
        self.version += 1            # answers for the subject before are stale now
        self.answers = {}
        if not self.text:
            self.text = ek.text() or ''
        self.subject = subject
        self.render()

    def go_back(self, *ignored):
        """◀: the subject before this one (the chip or the header button)."""
        if not self.history:
            return
        self.subject = self.history.pop()
        self.version += 1
        self.answers = {}
        self.render()

    def show_back_button(self):
        """◀ in the header while there is somewhere to go back to, so it is in
        reach however far down a long docs page you are."""
        if self.history:
            self.window.add_button(BACK_ICON, self.go_back, name='back')
        else:
            self.window.remove_button('back')

    def explain_name(self, dotted, push=True):
        """A tapped or typed name, explained here: may import its module."""
        if not push:
            self.subject = None
        self.go_to(subjects.Subject('name', dotted, -1, -1, 0, dotted, None, {}))

    def explain_page(self, page_path, anchor, title, focus=None):
        """Part of a docs page shown here (a link). With focus: the whole
        page, scrolled to that entry (Read on)."""
        label = title or anchor or page_path.rsplit('/', 1)[-1]
        self.scroll_target = focus
        self.go_to(subjects.Subject('page', label, -1, -1, 0, '', (page_path, anchor, focus), {}))

    def ask(self, text, caret):
        """jedi on its own thread: where it is defined, and a call's parameters."""
        self.version += 1
        position = units.to_utf16(text, caret)
        self.assistant.request('definition', self.version, text, position)
        self.assistant.request('signature', self.version, text, position)

    def take_answers(self):
        changed = False
        for kind in ('definition', 'signature'):
            answer = self.assistant.take(kind, self.version)
            if answer is not None:
                self.answers[kind] = answer
                changed = True
        if changed and self.subject is not None:
            self.render(to_top=False)       # the reader may be part way down

    def scope_names(self, line):
        """Where line sits: the enclosing class and def names, outermost first."""
        if not self.text or line < 1:
            return []
        key = hash(self.text)
        if self.index_key != key:
            self.index_key = key
            try:
                self.index = codesense.build_index(self.text)
            except Exception:
                self.index = None
        if self.index is None:
            return []
        try:
            path = self.index.enclosing(line)
        except Exception:
            return []
        return [getattr(part, 'name', str(part)) for part in path]

    # --- The docs -------------------------------------------------------------

    def entry_names(self):
        if self.names is None:
            try:
                self.names = set(entry.name for entry in docs.entries())
            except Exception:
                self.names = set()
        return self.names

    def find_entry(self, dotted, thing):
        """The docs entry for dotted: the name itself, the name the object
        gives itself (_ui.Button is ui.Button, a dict's pop is dict.pop), or
        the member on each class its owner is or inherits from (add_subview
        is documented once, on ui.View)."""
        try:
            everything = docs.entries()
        except Exception:
            return None                  # no docs here (PythonIDE)
        names = [dotted]
        qualified = getattr(thing, '__qualname__', None) if thing is not None else None
        if isinstance(qualified, str):
            names.append(docs_name(getattr(thing, '__module__', None), qualified))
        owner_name, _, last = dotted.rpartition('.')
        owner = reach(owner_name, self.explicit) if owner_name else None
        if inspect.isclass(owner):
            classes = owner.__mro__
        elif owner is not None and not inspect.ismodule(owner):
            classes = type(owner).__mro__
        else:
            classes = ()
        root = dotted.split('.', 1)[0]
        for klass in classes:
            if klass is object:
                continue
            names.append(docs_name(klass.__module__, '%s.%s' % (klass.__qualname__, last)))
            names.append('%s.%s.%s' % (root, klass.__name__, last))
        found = docs_index.named(everything, names)
        return found[0] if found else None

    def docs_signature(self):
        """The docs' own signature line for the subject, as HTML ('' if none)."""
        if self.entry is None:
            return ''
        try:
            signature, _ = docs.section_of(self.entry)
        except Exception:
            return ''
        return docs_index.clean(signature) if signature else ''

    def rich(self, body, page_path, page):
        """Docs HTML for a card: links made live (they open here), code in
        the card kit's colours, Sphinx's clutter cleaned away."""
        names = self.entry_names()

        def live(match):
            attributes, inner_html = match.group(1), match.group(2)
            if 'headerlink' in attributes:
                return ''
            found = HREF.search(attributes)
            item = subjects.resolve_link(found.group(1) if found else '', page_path, names)
            if item is None:
                return '<span class="dc-link">%s</span>' % inner_html
            if item[0] == 'page':
                item = item + (docs_index.plain_text(inner_html),)
            return '<span class="dc-link xp-go"%s>%s</span>' % (page.go(item), inner_html)

        return docs_index.replace_code(docs_index.clean(LINK.sub(live, body)), docs.render_code)

    # --- Showing --------------------------------------------------------------

    def look_up(self, subject):
        """What every facet shares, found once per page: the object, its docs
        entry and that entry's text, and its inputs."""
        self.thing = reach(subject.dotted, self.explicit) if subject.dotted else None
        root = subject.dotted.split('.', 1)[0] if subject.dotted else ''
        self.entry, self.entry_body, self.inputs = None, '', None
        if root and (self.thing is not None or reach(root, self.explicit) is not None):
            self.entry = self.find_entry(subject.dotted, self.thing)
        if self.entry is not None:
            try:
                self.entry_body = docs.section_of(self.entry)[1]
            except Exception:
                self.entry_body = ''
        if self.thing is not None and callable(self.thing):
            self.inputs = python_inputs(self.thing)
        if not self.inputs and self.entry is not None:
            signature = self.docs_signature()
            if signature:
                self.inputs = subjects.signature_inputs(docs_index.plain_text(signature))

    def render(self, to_top=True, keep_open=False):
        subject = self.subject
        if not keep_open:
            self.opened = set()
        self.look_up(subject)
        page = card_kit.Page()
        if self.history:
            back = self.history[-1]
            label = (back.dotted or back.text.strip() or 'back')[:BACK_LABEL_LENGTH]
            page.chips([card_kit.Chip('◀ %s' % label, item=('back',))])
        for facet in FACETS:
            try:
                facet(self, subject, page)
            except Exception as problem:
                traceback.print_exc()
                page.note('%s could not answer: %s' % (facet.__name__, problem))
        self.cards.show(page)
        self.show_back_button()
        target, self.scroll_target = self.scroll_target, None
        try:
            if target:
                self.cards.run('var e = document.getElementById(%s); if (e) e.scrollIntoView();'
                               % json.dumps(target))
            elif to_top:
                self.cards.run('window.scrollTo(0, 0);')
        except Exception:
            pass

    def picked(self, item):
        """A tap on a card, chip, button or docs link: everything opens here,
        in place. A failure shows on the page."""
        try:
            if isinstance(item, docs_index.Entry):
                self.explain_name(item.name)
                return
            kind = item[0]
            if kind == 'explain':
                self.explain_name(item[1])
            elif kind == 'page':
                self.explain_page(item[1], item[2], item[3] if len(item) > 3 else '')
            elif kind == 'read':
                self.explain_page(item[1], '', item[2], focus=item[2])
            elif kind == 'toggle':
                self.opened ^= {item[1]}
                self.render(to_top=False, keep_open=True)
            elif kind == 'load':
                self.explicit = True
                self.render()
            elif kind == 'back':
                self.go_back()
            elif kind == 'insert':
                ek.insert(item[1])
            elif kind == 'param':
                ek.insert(item[1] + '=')
            elif kind == 'jump':
                self.jump(item[1])
            elif kind == 'open':
                self.open_file(item[1], item[2])
            elif kind == 'find':
                from . import hub
                hub.open_find(item[1])
        except Exception as problem:
            traceback.print_exc()
            self.cards.say('Could not do that: %s' % problem)

    def jump(self, index):
        ek.select(index)
        try:
            ek.reveal(index)
        except Exception:
            pass

    def open_file(self, path, line):
        opener = ek.Opener(self.window)
        try:
            opener.go(path, line)
        except TypeError:
            opener.go(path)

    def stop(self):
        self.assistant.stop()


def open_explain():
    """Open Explain over the code (or bring it back)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = ExplainTool(window)
    window.explain_tool = tool
    window.on('open', lambda _window: tool.look_again())
    window.on('close', lambda _window: tool.stop())
    window.show()
    return tool
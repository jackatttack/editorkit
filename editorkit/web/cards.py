"""Cards: dense, reflowing pages of chips and cards, shown in a WebView.

The look Snippets set: chips that wrap, cards in a grid that reflows to the
width, each card's content as its face (coloured code, fields as pills),
colour carrying meaning (a chip's colour on its cards' edges), every part
either content or an action. Shrinking a window reflows the page; pinching
zooms it (a dense overview, or bigger targets).

    from editorkit import cards, tiles

    board = tiles.Cards(window, on_pick=picked)    # a Code tile with this look

    page = cards.Page()
    page.chips([cards.Chip('Python', item=('group', 1), count=7,
                           colour='#27AE60', on=True),
                cards.Chip('＋ Group', item=('new_group', None), dashed=True)])
    page.grid([cards.Card('Main guard', item=('insert', 1), colour='#27AE60',
                          body=cards.code(text),
                          actions=[cards.Action('✏️', ('edit', 1)),
                                   cards.Action('🗑', ('delete', 1))]),
               cards.Card('＋ Snippet', item=('new', None), dashed=True)])
    board.show(page)

    def picked(item):          # the tapped chip's, card's or action's item
        ...

Card pages are as wide as the window, so rows wrap and grids choose their
columns from the width: wide windows lay out across, narrow ones stack.
Items are any values (tuples are handy); None leaves a thing untappable. A
tap on an action never also taps its card. Bodies are HTML: build them with
code() (coloured, ${fields} as pills, cut to a few lines), text() (plain
words) or escape(). Pure Python (no ui): tests/smoke_cards.py checks it.
"""
import re
from collections import namedtuple

from . import codeview, prose


# --- Settings -------------------------------------------------------------

CODE_LINES = 8                   # lines a code() body shows before "… n more"
GRID_MIN_WIDTH = 160             # narrowest a card gets before the grid drops a column
FIELD = re.compile(r'\$\{[a-z]+\}')


# --- The parts --------------------------------------------------------------

Chip = namedtuple('Chip', 'label item count colour on dashed')
Chip.__new__.__defaults__ = (None, None, None, False, False)
Chip.__doc__ = """A rounded tag in a wrapping row: label, its item, an optional
count, a colour (outline, filled when on), dashed for an 'add' chip."""

Card = namedtuple('Card', 'title item body colour actions dashed')
Card.__new__.__defaults__ = (None, '', None, (), False)
Card.__doc__ = """A grid cell: a title row (with action buttons), then body
HTML. colour edges it. dashed makes an 'add' card showing only its title."""

Action = namedtuple('Action', 'label item armed look')
Action.__new__.__defaults__ = (False, None)
Action.__doc__ = """A button: in a card's title row, or in a Page.buttons row.
armed paints it as waiting for a confirming second tap (pair it with a label
like 'Sure?'). look (buttons rows): None, 'go' (accent), 'warn', 'field' (a
value to tap and change) or 'quiet' (an untappable separator)."""

escape = codeview.escape


# --- Bodies -------------------------------------------------------------------

def code(text, lines=CODE_LINES, python=True):
    """A code body: the first lines, syntax-coloured, with ${fields} as
    pills. Fields are swapped for plain names before colouring, so the
    colouring never splits them, then put back as pills."""
    fields = []

    def hold(match):
        fields.append(match.group(0))
        return 'EKFIELD%dX' % (len(fields) - 1)

    held = FIELD.sub(hold, text)
    all_lines = held.split('\n')
    shown = all_lines[:lines]
    classes = codeview.syntax_classes('\n'.join(shown)) if python else {}
    html = '\n'.join(codeview.line_html(line, classes.get(number, []), []) or ' '
                     for number, line in enumerate(shown, 1))
    for index, field in enumerate(fields):
        html = html.replace('EKFIELD%dX' % index,
                            '<span class="ek-field">%s</span>' % escape(field))
    hidden = len(all_lines) - len(shown)
    if hidden > 0:
        html += '\n<span class="ek-more">… %d more line%s</span>' % (
            hidden, '' if hidden == 1 else 's')
    return '<div class="ek-code">%s</div>' % html


def text(words):
    """A body of plain words (wrapped, escaped)."""
    return '<div class="ek-text">%s</div>' % escape(words)


def face(emoji, caption='', dim=False):
    """A tool card's body: a big emoji beside a short caption (Toolbox's
    hub, Quick). dim greys it (a tool not ready yet)."""
    return ('<div class="ek-face%s"><span class="ek-face-emoji">%s</span>'
            '<span class="ek-face-caption">%s</span></div>'
            % (' ek-dim' if dim else '', escape(emoji), escape(caption)))


# --- The page -------------------------------------------------------------

class Page:
    """Collects headings, notes, chips and grids for one section."""

    def __init__(self, section=0):
        self.ids = codeview.SectionIds(section)
        self.parts = []

    def go(self, item):
        return codeview.go_attribute(self.ids.go(item))

    @staticmethod
    def tint(colour):
        return ' style="--c:%s"' % escape(colour) if colour else ''

    def heading(self, words):
        self.parts.append('<div class="ek-heading">%s</div>' % escape(words))

    def note(self, words):
        self.parts.append('<div class="ek-note">%s</div>' % escape(words))

    def prose(self, *blocks):
        """A full-width article in the docs' look: blocks from editorkit.web.prose
        (heading, text, code, signature, note, terms, member)."""
        self.parts.append(prose.article(*blocks))

    def chips(self, chips):
        out = ['<div class="ek-chips">']
        for chip in chips:
            classes = 'ek-chip%s%s' % (' on' if chip.on else '', ' dashed' if chip.dashed else '')
            count = '' if chip.count is None else '<small>%s</small>' % escape(str(chip.count))
            out.append('<div class="%s"%s%s>%s%s</div>' % (
                classes, self.tint(chip.colour), self.go(chip.item), escape(chip.label), count))
        out.append('</div>')
        self.parts.append(''.join(out))

    def grid(self, cards, min_width=GRID_MIN_WIDTH):
        out = ['<div class="ek-grid" style="grid-template-columns: repeat(auto-fill, '
               'minmax(%dpx, 1fr))">' % min_width]
        for card in cards:
            if card.dashed:
                out.append('<div class="ek-card dashed"%s%s>%s</div>' % (
                    self.tint(card.colour), self.go(card.item), escape(card.title or '')))
                continue
            title_row = ''
            if card.title or card.actions:
                actions = ''.join('<b class="ek-act%s"%s>%s</b>' % (
                    ' armed' if action.armed else '', self.go(action.item), escape(action.label))
                    for action in card.actions)
                title_row = '<div class="ek-title"><span>%s</span>%s</div>' % (
                    escape(card.title or ''), actions)
            out.append('<div class="ek-card"%s%s>%s%s</div>' % (
                self.tint(card.colour), self.go(card.item), title_row, card.body or ''))
        out.append('</div>')
        self.parts.append(''.join(out))

    def buttons(self, actions):
        """A wrapping row of buttons (a toolbar): they share the row's width
        and wrap onto more lines when it gets narrow, never cut to '…'. A
        list inside the list is a group kept on one line (a stepper)."""
        out = ['<div class="ek-buttons">']
        for action in actions:
            if isinstance(action, (list, tuple)) and not isinstance(action, Action):
                out.append('<div class="ek-group">%s</div>'
                           % ''.join(self.button_html(part) for part in action))
            else:
                out.append(self.button_html(action))
        out.append('</div>')
        self.parts.append(''.join(out))

    def button_html(self, action):
        classes = 'ek-button%s%s' % (' ' + action.look if action.look else '',
                                     ' armed' if action.armed else '')
        return '<div class="%s"%s>%s</div>' % (classes, self.go(action.item),
                                               escape(action.label))

    def choices(self, options, chosen=None, colour=None):
        """A one-of-many chip row (a segmented control): options are
        (label, item) pairs, and the chip whose item is chosen is on. Taps
        hand the item back like any chip."""
        self.chips([Chip(label, item=item, colour=colour, on=item == chosen) for label, item in options])

    def sheet(self, title, body, open=False):
        """A panel that folds open and shut in the page with no trip to
        Python: title on a tappable bar, body HTML under it. The browser's
        own <details>, so no script. A redraw shows it shut unless open."""
        self.parts.append(
            '<details class="ek-sheet"%s style="background:var(--wash);border-radius:12px;'
            'margin:8px 0;padding:0 12px"><summary style="cursor:pointer;padding:10px 0;'
            'font:600 15px -apple-system,sans-serif">%s</summary>'
            '<div style="padding:0 0 12px">%s</div></details>'
            % (' open' if open else '', escape(title), body))

    def section(self):
        """(html, items) for tiles.Code.set_section (tiles.Cards.show calls it)."""
        return ''.join(self.parts), self.ids.items


# --- The look -------------------------------------------------------------

CSS = """
#results { width: auto; min-width: 0; }
.ek-heading { font: 600 17px/1.25 -apple-system, sans-serif; padding: 14px 2px 6px 2px; }
.ek-note { font: 13px -apple-system, sans-serif; opacity: 0.6; padding: 6px 2px; }
.ek-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 2px 10px 2px; }
.ek-chip { padding: 4px 12px; border-radius: 999px;
    border: 1.5px solid var(--c, var(--line));
    font: 14px/1.4 -apple-system, sans-serif; cursor: pointer; }
.ek-chip.on { background: var(--c, var(--line)); color: #111111; font-weight: 600; }
.ek-chip small { opacity: 0.7; margin-left: 3px; }
.ek-chip.dashed { border-style: dashed; border-color: var(--line); }
.ek-grid { display: grid; gap: 8px; padding: 0 2px 12px 2px; }
.ek-card { background: var(--wash); border-radius: 12px; border: 0.5px solid var(--rule);
    box-shadow: inset 3px 0 0 var(--c, transparent); padding: 10px 12px 10px 14px;
    cursor: pointer; overflow: hidden; min-width: 0; }
.ek-title { display: flex; align-items: flex-start; gap: 6px;
    font: 600 15px/1.3 -apple-system, sans-serif; margin-bottom: 6px; }
.ek-title span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.ek-act { font: 13px/1.3 -apple-system, sans-serif; padding: 3px 9px; border-radius: 8px;
    background: var(--wash-strong); cursor: pointer; }
.ek-act.armed { background: #FF5A5F; color: #111111; }
.ek-code { font: 12.5px/1.45 Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere;
    background: var(--card); border-radius: 8px; padding: 6px 9px; margin: 2px 0 6px; }
.ek-text { font: 14px/1.45 -apple-system, sans-serif; opacity: 0.85; }
.ek-field { background: rgba(255, 200, 80, 0.28); border-radius: 4px; padding: 0 2px; }
.ek-more { opacity: 0.55; font-size: 11px; }
.ek-buttons { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 2px 10px 2px; }
.ek-group { display: flex; gap: 6px; flex: 0 0 auto; }
.ek-button { flex: 0 0 auto; min-width: 36px; text-align: center; padding: 7px 14px;
    border-radius: 10px; background: var(--wash-strong); border: 0.5px solid var(--rule);
    white-space: nowrap; font: 500 14px/1.3 -apple-system, sans-serif; cursor: pointer; }
.ek-button.go { background: var(--accent, #ff2d55); color: #111111; font-weight: 600; }
.ek-button.warn { color: #FF9F43; }
.ek-button.field { background: var(--card); box-shadow: inset 0 0 0 1px var(--rule);
    font-weight: 700; min-width: 56px; }
.ek-button.quiet { flex: 0 0 auto; min-width: 0; background: none; opacity: 0.5;
    cursor: default; padding-left: 2px; padding-right: 2px; }
.ek-button.armed { background: #FF5A5F; color: #111111; }
.ek-card.dashed { display: flex; align-items: center; justify-content: center; min-height: 64px;
    background: none; border: 1.5px dashed var(--line);
    font: 15px -apple-system, sans-serif; }
.ek-face { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ek-face-emoji { font-size: 24px; line-height: 28px; }
.ek-face-caption { font: 13px/1.3 -apple-system, sans-serif; opacity: 0.65; min-width: 0; }
.ek-dim { opacity: 0.45; }
"""

# Prose (the docs' look) shows on every card page, as a page or a card body.
CSS += prose.CSS
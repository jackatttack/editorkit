"""🎨 Gallery: every piece editorkit draws, in one window, to see the look whole.

One tab per family, each piece shown with real content:

    Prose   the docs' look: headings, text, code with ⧉ Copy, signatures,
            members, rows, terms, notes and callouts
    Cards   the card kit: chips, cards, tool faces, buttons
    Code    the code view: hits as Find shows them, every row kind, a preview

Pinch any tab to see how it scales. After a change to the look, open the
Gallery and check every piece still belongs with the others.

    from editorkit_toolbox import gallery
    gallery.open_gallery()
"""
import editorkit as ek
from editorkit.web import cards as card_kit
from editorkit.web import codeview, prose
from editorkit.web import tiles as web_tiles


# --- Settings -------------------------------------------------------------

TITLE = 'Gallery'
EMOJI = '🎨'
WINDOW_KEY = 'deck-gallery'
CARD_WIDTH = 200
KIND_COLOURS = (('class', '#8E6CEF'), ('function', '#27AE60'), ('module', '#2D9CDB'),
                ('value', '#F2994A'), ('docs', '#EB5757'), ('example', '#F2C94C'),
                ('file', '#56CCF2'), ('other', '#8A8A96'))

SAMPLE = '''import editorkit as ek


def greet(name, loud=False):
    """Say hello to name; loud shouts it."""
    words = 'Hello, %s' % name
    if loud:
        words = words.upper() + '!'
    ek.show(words, title='Greeting')
    return words


greet('Pythonista', loud=True)
'''


# --- The pages ------------------------------------------------------------

def prose_page():
    """Every prose builder, as a page about one function."""
    page = card_kit.Page()
    page.prose(
        prose.heading('Prose', 1),
        prose.meta('the docs\' look · editorkit.web.prose'),
        prose.text('Pages that read like Pythonista\'s own documentation. Words wrap, '
                   '`inline code` sits in faint chips, and **bold** stands out.\n\n'
                   'A list:\n\n'
                   '- headings at weight 600\n'
                   '- code blocks that wrap to the width\n'
                   '- notes as rounded callouts'),
        prose.heading('A code block', 2),
        prose.code(SAMPLE),
        prose.heading('Signatures and members', 2),
        prose.member(prose.signature('greet', 'name, loud=False', prefix='ek.', kind='function'),
                     prose.text('Say hello to `name`; `loud` shouts it.')),
        prose.member(prose.signature('Window', 'title, emoji=None, key=None', prefix='ek.',
                                     kind='class'),
                     prose.text('A themed panel over the editor.')),
        prose.heading('Rows', 2),
        prose.row(prose.signature('show', 'thing, title=None', prefix='ek.'),
                  'Put a window over your code in one line.'),
        prose.row(prose.signature('select', 'start, end', prefix='ek.'),
                  'Select characters in the open script.'),
        prose.heading('Terms', 2),
        prose.terms([('pin', 'a folded window, resting at the edge'),
                     ('dock', 'the keyboard\'s place'),
                     ('home', 'where a window opens and goes back to')]),
        prose.heading('Notes and callouts', 2),
        prose.note('Showing again swaps the content in place.', 'Note', 'note'),
        prose.note('`ek.run_tool(main)` keeps a tool\'s names alive.', 'Tip', 'tip'),
        prose.note('Private Pythonista hooks can change in an update.', 'Warning', 'warning'),
        prose.callout('Danger', prose.text('An error shows here with its traceback:'),
                      prose.code('Traceback (most recent call last):\n  ...\nNameError: name '
                                 "'greet' is not defined", python=False, copy=False),
                      kind='danger'))
    return page


def cards_page():
    """Every card-kit piece: headings, notes, chips, cards, faces, buttons."""
    page = card_kit.Page()
    page.heading('Cards')
    page.note('CHIPS · one per kind colour')
    page.chips([card_kit.Chip(kind, item=('chip', kind), colour=colour)
                for kind, colour in KIND_COLOURS])
    page.note('CARDS · code, text and actions')
    page.grid([
        card_kit.Card('def greet', item=('card', 'greet'), colour='#27AE60',
                      body=card_kit.code("def greet(name, loud=False):", lines=2)
                      + card_kit.text('Say hello to name; loud shouts it.'),
                      actions=[card_kit.Action('⤵', ('insert', 'greet'))]),
        card_kit.Card('class Window', item=('card', 'Window'), colour='#8E6CEF',
                      body=card_kit.text('A themed panel over the editor.')),
        card_kit.Card('line 9', item=('card', 'line'), colour='#56CCF2',
                      body=card_kit.code("ek.show(words, title='Greeting')", lines=1)),
        card_kit.Card('A long title that has to wrap onto a second line', item=('card', 'long'),
                      body=card_kit.text('Cards grow with their words.')),
    ], min_width=CARD_WIDTH)
    page.note('TOOL FACES · as the hub shows them')
    page.grid([card_kit.Card('Files', item=('face', 1), body=card_kit.face('📁', 'files')),
               card_kit.Card('Find', item=('face', 2), body=card_kit.face('🔎', 'search')),
               card_kit.Card('Soon', item=('face', 3), body=card_kit.face('🧪', 'not ready', dim=True))],
              min_width=120)
    page.note('BUTTONS')
    page.buttons([card_kit.Action('Plain', ('button', 1)),
                  card_kit.Action('▶ Go', ('button', 2), look='go'),
                  card_kit.Action('Used here · 3 ▸', ('button', 3))])
    return page


def code_section():
    """The code view as Find shows it, every row kind, and a preview: one
    section of HTML with its items."""
    marks = {6: [(4, 9)], 9: [(4, 11)]}
    found = codeview.file_section(1, 'gallery_sample.py · as Find shows hits', SAMPLE, marks,
                                  context_lines=1, line_item=lambda number, _: ('line', number),
                                  mark_item=lambda number, mark: ('mark', number, mark),
                                  row_button=('📜', lambda number, _: ('view', number)))
    Row = codeview.Row
    kinds = codeview.rows_section(2, 'Every row kind', [
        Row('print("a code row")', 'code', number=1),
        Row('A plain row: words, not code', 'plain'),
        Row('+ an added line', 'add'),
        Row('- a removed line', 'remove'),
        Row('NameError: an error row', 'error'),
        Row('a quiet note row', 'note'),
        Row('A heading row', 'heading')])
    preview = codeview.preview_section(3, 'gallery_sample.py · a preview', SAMPLE)
    html = found[0] + kinds[0] + preview[0]
    items = {}
    for part in (found, kinds, preview):
        items.update(part[1])
    return html, items


# --- The window -----------------------------------------------------------

def open_gallery():
    """Open the Gallery over the code (or bring it back)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    prose_tile = web_tiles.Cards(window, zoom_key='gallery-prose')
    cards_tile = web_tiles.Cards(window, zoom_key='gallery-cards')
    code_tile = web_tiles.Cards(window, zoom_key='gallery-code')
    window.add_page('Prose', prose_tile)
    window.add_page('Cards', cards_tile)
    window.add_page('Code', code_tile)
    prose_tile.show(prose_page())
    cards_tile.show(cards_page())
    code_tile.set_section(code_section())
    window.show()
    return window
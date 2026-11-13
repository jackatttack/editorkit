"""Lesson 2: Cards.

The card kit draws a tool's surface: pages of chips, buttons and cards that
reflow to the window. Run this script and step through.
"""
import editorkit as ek
from editorkit.web import cards, tiles
from editorkit.lessons import Lesson

lesson = Lesson('Cards', __file__)
SIZE = (340, 340)


@lesson.step('A page of cards')
def first_page():
    """A tiles.Cards board is a page in a window. Build a cards.Page with a
    heading and a grid, then board.show(page) draws it.

    Cards reflow to the window's width: make the window wider and they lay
    out across, narrower and they stack. Pinch to zoom."""
    window = ek.Window('Fruit', emoji='🍎', key='lesson-cards', size=SIZE)
    board = tiles.Cards(window, zoom_key='lesson-cards')
    window.add_page('Cards', board)
    page = cards.Page()
    page.heading('Fruit')
    page.grid([cards.Card('Apple', body=cards.face('🍎', 'crisp')),
               cards.Card('Pear', body=cards.face('🍐', 'soft')),
               cards.Card('Lemon', body=cards.face('🍋', 'sharp'))])
    board.show(page)
    window.show()


@lesson.step('Taps hand back your own items')
def taps():
    """Give each card an item: any value you like. A tap hands that item to
    on_pick, with no ids or strings to parse.

    Here a tap names the fruit in a note. Drawing the page again is cheap:
    an unchanged page is skipped."""
    window = ek.Window('Fruit', emoji='🍎', key='lesson-cards', size=SIZE)
    fruit = [('Apple', '🍎'), ('Pear', '🍐'), ('Lemon', '🍋')]

    def draw(note):
        page = cards.Page()
        page.heading('Tap a fruit')
        page.note(note)
        page.grid([cards.Card(name, item=name, body=cards.face(emoji, ''))
                   for name, emoji in fruit])
        board.show(page)

    board = tiles.Cards(window, on_pick=lambda item: draw('You tapped %s.' % item),
                        zoom_key='lesson-cards')
    window.add_page('Cards', board)
    draw('Nothing tapped yet.')
    window.show()


@lesson.step('Chips that filter')
def chips():
    """Chips are a wrapping row of tags. A lit chip (on=True) fills with its
    colour, and a card can carry the same colour on its edge, so colour
    means the same thing everywhere.

    Tap a chip to show only that colour; the counts come free."""
    window = ek.Window('Fruit', emoji='🍎', key='lesson-cards', size=SIZE)
    fruit = [('Apple', '🍎', 'red'), ('Cherry', '🍒', 'red'), ('Lemon', '🍋', 'yellow'),
             ('Banana', '🍌', 'yellow'), ('Pear', '🍐', 'green'), ('Kiwi', '🥝', 'green')]
    colours = {'red': '#FF5A5F', 'yellow': '#F5C26B', 'green': '#62D26F'}
    chosen = ['all']

    def draw():
        page = cards.Page()
        page.chips([cards.Chip('All', item='all', on=chosen[0] == 'all')] +
                   [cards.Chip(name.title(), item=name, colour=colour, on=chosen[0] == name,
                               count=sum(1 for item in fruit if item[2] == name))
                    for name, colour in colours.items()])
        page.grid([cards.Card(name, body=cards.face(emoji, ''), colour=colours[kind])
                   for name, emoji, kind in fruit if chosen[0] in ('all', kind)])
        board.show(page)

    def picked(item):
        chosen[0] = item
        draw()

    board = tiles.Cards(window, on_pick=picked, zoom_key='lesson-cards')
    window.add_page('Cards', board)
    draw()
    window.show()


@lesson.step('Buttons, and a stepper')
def buttons():
    """page.buttons takes Actions: a label and an item. Looks are 'go',
    'warn', 'field' and 'quiet'.

    A list inside buttons stays on one line: here −, the value and + make a
    stepper. The value is an Action with no item, so it does nothing when
    tapped."""
    window = ek.Window('Order', emoji='🍽', key='lesson-cards', size=SIZE)
    count = [3]
    note = ['']

    def draw():
        page = cards.Page()
        page.heading('Servings')
        page.buttons([[cards.Action('−', 'less'),
                       cards.Action(str(count[0]), None, look='field'),
                       cards.Action('+', 'more')],
                      cards.Action('Order', 'order', look='go'),
                      cards.Action('Reset', 'reset', look='warn')])
        if note[0]:
            page.note(note[0])
        board.show(page)

    def picked(item):
        if item == 'less':
            count[0] = max(1, count[0] - 1)
        elif item == 'more':
            count[0] += 1
        elif item == 'order':
            note[0] = 'Ordered %d servings.' % count[0]
        elif item == 'reset':
            count[0], note[0] = 3, ''
        draw()

    board = tiles.Cards(window, on_pick=picked, zoom_key='lesson-cards')
    window.add_page('Cards', board)
    draw()
    window.show()


@lesson.step('Code on a card')
def code_card():
    """cards.code(text) colours code and cuts it to a few lines. A card can
    carry actions: small buttons in its title row, whose taps never also
    tap the card.

    Here every function in this lesson becomes a card, and its 📜 opens this
    file at that function (ek.Opener)."""
    import ast
    window = ek.Window('This lesson', emoji='📜', key='lesson-cards', size=SIZE)
    opener = ek.Opener(window)
    with open(lesson.path, encoding='utf-8') as handle:
        source = handle.read()
    lines = source.split('\n')
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]

    def picked(item):
        if isinstance(item, tuple) and item[0] == 'open':
            opener.go(lesson.path, item[1])

    board = tiles.Cards(window, on_pick=picked, zoom_key='lesson-cards')
    window.add_page('Cards', board)
    page = cards.Page()
    page.heading('%d functions' % len(functions))
    page.grid([cards.Card(node.name + '()', body=cards.code('\n'.join(
                   lines[node.lineno - 1:node.end_lineno])),
                   actions=[cards.Action('📜', ('open', node.lineno))])
               for node in functions])
    board.show(page)
    window.show()


lesson.run()
"""Lesson 9: Part of Pythonista.

Run this script. A tool feels at home when it wears the editor's colours,
can switch themes, and sits in the wrench menu. The last step puts back
your theme and the wrench menu as they were.
"""
import editorkit as ek
from editorkit.web import cards, tiles
from editorkit.lessons import Lesson

lesson = Lesson('Part of Pythonista', __file__)
SIZE = (340, 400)
state = {}


@lesson.step("Your theme's colours")
def colours():
    """ek.theme_colours() is the theme showing now as a plain dict, such as
    {'background': '#1e1e24'}. Windows already wear these colours; read
    them when your own drawing should match.

    Try it: a card per colour, edged in that colour."""
    window = ek.Window('Colours', emoji='🎨', key='lesson-colours', size=SIZE, owner=lesson.window)
    board = tiles.Cards(window, zoom_key='lesson-colours')
    window.add_page('Colours', board)
    page = cards.Page()
    page.note('Theme: %s' % ek.current_theme())
    page.grid([cards.Card(name, body=cards.text(value), colour=value)
               for name, value in sorted(ek.theme_colours().items())
               if isinstance(value, str) and value.startswith('#')], min_width=120)
    board.show(page)
    window.show()


@lesson.step('Every theme, live')
def themes():
    """ek.theme_names() lists every theme, your own as 'User:...', and
    ek.use_theme(name) switches the whole app to one, live: windows
    restyle with it.

    Try it, then tap a chip. Put it back returns to your own theme."""
    state.setdefault('theme', ek.current_theme())
    window = ek.Window('Themes', emoji='🌈', key='lesson-themes', size=SIZE, owner=lesson.window)
    board = tiles.Cards(window, on_pick=ek.use_theme, zoom_key='lesson-themes')
    window.add_page('Themes', board)
    page = cards.Page()
    page.note('Tap a theme to switch to it.')
    page.chips([cards.Chip(name, item=name) for name in ek.theme_names()])
    board.show(page)
    window.show()


@lesson.step('A place in the wrench menu')
def wrench():
    """ek.add_wrench_action(script, title, icon, colour) puts a script in
    the editor's wrench menu, the way the installer adds Toolbox. Adding
    it again updates the entry, so an installer can run any number of times.

    Try it, then tap the wrench at the top of the editor."""
    ek.add_wrench_action(__file__, 'Lesson 9', icon='Primaries_Home', colour='#F5C26B')
    titles = [action['title'] for action in ek.wrench_actions()]
    return 'The wrench menu has %d entries: %s.' % (len(titles), ', '.join(titles))


@lesson.step('Put it back')
def put_back():
    """Take the lesson out of the wrench menu, and switch back to the
    theme you had before. A tool's own installer would keep its entry.

    Try it, then Done ✓."""
    ek.remove_wrench_action(__file__)
    if 'theme' in state:
        ek.use_theme(state.pop('theme'))
    return 'Your theme and wrench menu are as they were.'


lesson.run()

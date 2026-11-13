"""Lesson 1: Windows.

Run this script. A lesson window opens over the code, and the editor shows
the step it is explaining. Tap ▶ Try it to run a step, Next ▶ to move on.
"""
import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('Windows', __file__)


@lesson.step('A window over your code')
def hello():
    """Pythonista has never had this: a window of your own, floating over
    the editor while you work.

    Tap ▶ Try it. Then drag the new window by any empty part, or resize it
    from its ◢ corner. owner=lesson.window makes it part of this lesson
    (more on that in Folding away)."""
    window = ek.Window('Hello', emoji='👋', key='lesson-hello', owner=lesson.window)
    window.add_page('Hi', 'Hello! I am a window over your code.')
    window.show()


@lesson.step('Pages become tabs')
def pages():
    """Each add_page adds a page; with two or more the window grows tabs.

    A page can be text, HTML, an image, a figure or any ui.View. HTML takes
    your theme's colours."""
    window = ek.Window('Notes', emoji='📝', key='lesson-notes', owner=lesson.window)
    window.add_page('Today', 'Finish the lesson.')
    window.add_page('HTML', '<h2>Hello</h2><p>This page is <b>HTML</b>.</p>')
    window.show()


@lesson.step('Buttons in the header')
def buttons():
    """The header is the window's toolbar: add_button(icon, action, name)
    puts a button there, and its action gets the window.

    Here + counts taps, and set_page_content swaps the page in place."""
    window = ek.Window('Counter', emoji='🔢', key='lesson-counter', owner=lesson.window)
    taps = [0]
    window.add_page('Count', 'Tap + in the header')

    def add_one(window):
        taps[0] += 1
        window.set_page_content('Count', str(taps[0]))

    window.add_button('+', add_one, 'add')
    window.show()


@lesson.step('Folding away')
def folding():
    """– folds a window away. Window(owner=app) makes a window one of an
    app's pieces: it folds into the app's box, a row of chips under the
    app's header. With no owner it goes to the Toolbox's tray when that is
    running, else to its own pin, so nothing is ever lost.

    Try it, then fold the two pieces with –: they gather in a box at the top
    of this lesson. Tap a chip to bring one back; hold one to close it. Fold
    the lesson itself and its pieces go with it."""
    for number, emoji in ((1, '🍎'), (2, '🍐')):
        window = ek.Window('Piece %d' % number, emoji=emoji, key='lesson-piece-%d' % number,
                           owner=lesson.window)
        window.add_page('Piece', 'Fold me with –')
        window.show()


@lesson.step('A window can show anything')
def anything():
    """ek.show(thing) is the one-line window: text, HTML, a PIL image or a
    matplotlib figure.

    Showing the same key again swaps the content in place, so a loop can
    keep one window up to date."""
    from PIL import Image, ImageDraw
    picture = Image.new('RGB', (240, 120), (40, 44, 52))
    ImageDraw.Draw(picture).ellipse((20, 20, 100, 100), fill=(255, 45, 85))
    ek.show(picture, title='Picture', key='lesson-picture', owner=lesson.window)


@lesson.step('Tidy up')
def tidy():
    """With a few windows open, ek.tidy() lays them out evenly. Run it again
    within 30 seconds and they go back where they were.

    Done ✓ closes the lesson, and with it every window it owns."""
    ek.tidy()
    return 'Tidied. Tap ▶ Try it again within 30 seconds to put them back.'


lesson.run()

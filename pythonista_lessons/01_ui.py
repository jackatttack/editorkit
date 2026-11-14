"""Pythonista 1: ui.

Run this script. You build a small app with Pythonista's ui module, one
piece at a time, each shown in a window beside its code: a view and a
label, a button that does something, layout that follows the size, your own
view class, and finally the whole thing full screen, as real scripts do.
"""
import ui

import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('ui', __file__, emoji='🐍')


@lesson.step('A view and a label', docs='ui.View')
def view_and_label():
    """Everything on screen in a ui app is a view. A view holds other
    views: add_subview puts a label inside it, placed by its frame, which is
    (x, y, width, height) from the top left.

    Try it: the view opens in a window beside this code."""
    view = ui.View(background_color='#20252b')
    label = ui.Label(text='Hello from ui', text_color='white', frame=(20, 20, 240, 32))
    view.add_subview(label)
    lesson.show_view(view, 'ui', key='lesson-ui')


@lesson.step('A button and its action', docs='ui.Button')
def button_action():
    """A button calls its action when tapped, handing over the button
    itself (sender). The action here changes the label, so a tap shows.

    Try it, then tap the button a few times."""
    view = ui.View(background_color='#20252b')
    label = ui.Label(text='Tapped 0 times', text_color='white', frame=(20, 20, 240, 32))
    button = ui.Button(title='Tap me', frame=(20, 70, 140, 44), corner_radius=10,
                       background_color='#ff5a5f', tint_color='white')
    taps = [0]

    def tapped(sender):
        taps[0] += 1
        label.text = 'Tapped %d times' % taps[0]

    button.action = tapped
    view.add_subview(label)
    view.add_subview(button)
    lesson.show_view(view, 'ui', key='lesson-ui')


@lesson.step('Layout that follows the size', docs='ui.View.flex')
def flexible():
    """Screens and windows change size. flex says what stretches: W the
    width, H the height, and L R T B the margins on that side. The bar
    stretches with the width; the button keeps to the bottom right.

    Try it, then resize the window from its ◢ corner."""
    view = ui.View(background_color='#20252b', frame=(0, 0, 300, 300))
    bar = ui.View(background_color='#ff5a5f', frame=(10, 10, 280, 40), flex='W')
    button = ui.Button(title='OK', frame=(210, 250, 80, 40), flex='LT', corner_radius=10,
                       background_color='#3a424c', tint_color='white')
    view.add_subview(bar)
    view.add_subview(button)
    lesson.show_view(view, 'ui', key='lesson-ui')


@lesson.step('Your own view class', docs='ui.View.layout')
def own_class():
    """A real app is a class of its own: make its pieces in __init__ and
    place them in layout(), which runs whenever the size changes. Here
    layout() keeps four squares square at any size.

    Try it, then resize the window again."""
    class Squares(ui.View):

        def __init__(self):
            self.background_color = '#20252b'
            self.squares = [ui.View(background_color=colour, corner_radius=8)
                            for colour in ('#ff5a5f', '#62d26f', '#4aa3ff', '#ffb347')]
            for square in self.squares:
                self.add_subview(square)

        def layout(self):
            size = min(self.width, self.height) / 2 - 15
            for number, square in enumerate(self.squares):
                square.frame = (10 + (number % 2) * (size + 10),
                                10 + (number // 2) * (size + 10), size, size)

    lesson.show_view(Squares(), 'ui', key='lesson-ui')


@lesson.step('Present it, as real scripts do', docs='ui.View.present')
def present():
    """A finished script ends with view.present(). 'fullscreen' covers the
    screen with a title bar and a close button; 'sheet' slides up as a
    card. Everything before this step works the same in a script of your own.

    Try it: the app fills the screen. ✕ at its top left closes it, and the
    lesson is still here."""
    view = ui.View(background_color='#20252b', name='My app')
    label = ui.Label(text='A whole app', text_color='white', alignment=ui.ALIGN_CENTER,
                     font=('<system-bold>', 28), frame=(0, 0, 320, 320), flex='WH')
    view.add_subview(label)
    view.present('fullscreen')
    return 'Close it with ✕ at the top left.'


lesson.run()

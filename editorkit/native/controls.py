"""Controls: a second header row of buttons, with help built in.

    controls = tiles.Controls(window, intro='Tap a control to see what it does.')
    controls.add('regex', '.*', switched, about='Treat the query as a regex.')
    controls.set_on('regex', True)      # lit
    controls.set_icon('context', '±2')

A tap calls action(name). The ? at the end is standard: it opens a help
card (the intro) over the page, and while help is on a tap on any control
explains it instead of running it. ? again, or a tap on the card, ends help.
"""
from .base import PADDING, ROW_HEIGHT, Tile, make_button, paint_button
from .card import Card


# --- Settings -------------------------------------------------------------

HELP_ICON = '?'
BUTTON_WIDTH = 44            # six controls and ? fit a phone's width
SPACING = 4
DEFAULT_INTRO = 'Tap a control to see what it does.'
NO_HELP = 'No help written for this yet.'


class Controls(Tile):
    HEIGHT = ROW_HEIGHT + PADDING      # what a layout gives it

    def __init__(self, window, intro=''):
        Tile.__init__(self, window)
        self.intro = intro or DEFAULT_INTRO
        self.entries = []              # [{'name', 'button', 'action', 'about'}]
        self.helping = False
        self.card = None
        self.help_button = make_button(HELP_ICON, lambda sender: self.toggle_help(),
                                       self.palette)
        self.add_subview(self.help_button)

    # --- Building ---------------------------------------------------------

    def add(self, name, icon, action, about=''):
        button = make_button(icon, lambda sender, name=name: self.tapped(name), self.palette)
        self.add_subview(button)
        self.entries.append({'name': name, 'button': button, 'action': action,
                             'about': about})
        self.layout()
        return button

    def entry(self, name):
        for entry in self.entries:
            if entry['name'] == name:
                return entry
        raise KeyError('no control named %r' % name)

    def set_on(self, name, on=True):
        self.paint(self.entry(name)['button'], on)

    def set_icon(self, name, icon):
        self.entry(name)['button'].title = icon

    def paint(self, button, on):
        paint_button(button, self.palette, on)

    # --- Taps and help ----------------------------------------------------

    def tapped(self, name):
        entry = self.entry(name)
        if self.helping:
            self.explain('%s   %s' % (entry['button'].title, entry['about'] or NO_HELP))
        else:
            entry['action'](name)

    def toggle_help(self):
        if self.helping:
            self.end_help()
        else:
            self.helping = True
            self.paint(self.help_button, True)
            self.explain(self.intro)

    def explain(self, text):
        if self.card is None:
            self.card = Card(self.window, on_close=self.end_help)
        self.card.set_text(text)
        self.window.show_sheet(self.card)

    def end_help(self):
        self.helping = False
        self.paint(self.help_button, False)
        self.window.close_sheet()

    # --- Drawing ----------------------------------------------------------

    def layout(self):
        x = PADDING
        for entry in self.entries:
            entry['button'].frame = (x, 0, BUTTON_WIDTH, ROW_HEIGHT)
            x += BUTTON_WIDTH + SPACING
        self.help_button.frame = (self.width - PADDING - BUTTON_WIDTH, 0,
                                  BUTTON_WIDTH, ROW_HEIGHT)
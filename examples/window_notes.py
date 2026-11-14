"""A notes window you can type in over your code. It remembers what you wrote.

The notes are saved to windows_notes.txt beside this script whenever you
fold the window into its pin or close it.
Shows: a page you build yourself (a builder function), two pages (tabs),
and the 'minimise' and 'close' events.

Pythonista clears this script's globals when it ends, but the window keeps
running. So everything a later callback needs is bound now, as a default
argument or an attribute on the window.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


import ui

import editorkit as ek

NOTES_PATH = os.path.join(HERE, 'window_notes.txt')


def notes_page(window, path=NOTES_PATH):
    """The page: a text view filled from the notes file. Runs on first open."""
    view = ui.TextView(font=('Menlo', 14))
    try:
        with open(path, encoding='utf-8') as handle:
            view.text = handle.read()
    except OSError:
        view.text = ''
    view.background_color = window.palette.background
    view.text_color = window.palette.text
    window.notes_view = view          # kept on the window for save_notes
    return view


def save_notes(window, path=NOTES_PATH):
    view = getattr(window, 'notes_view', None)
    if view is not None:
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(view.text)


notes = ek.Window('Notes', emoji='📝', size=(340, 300), min_size=(160, 120),
                  on_close=save_notes)
notes.on('minimise', save_notes)
notes.add_page('Notes', notes_page)
notes.add_page('Help', 'Type on the Notes page.\n'
                       'Your notes are saved when you fold\n'
                       'the window into its pin or close it.')
notes.show()

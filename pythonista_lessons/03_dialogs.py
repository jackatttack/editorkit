"""Pythonista 3: dialogs.

Run this script. The dialogs module asks the person using your script
something: an alert with buttons, a line of text, a whole form, a choice
from a list, and quick messages that fade by themselves. Dialogs wait for
an answer, so they must not run on the main thread: every step here is a
background step, and a script of your own calls them from the script itself
(which Pythonista runs off the main thread) or from @ui.in_background.
"""
import time

import console
import dialogs

import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('dialogs', __file__, emoji='🐍')


@lesson.step('An alert with buttons', background=True, docs='dialogs.alert')
def alert():
    """alert(title, message, button1, button2...) shows the buttons and
    returns the number of the one tapped, from 1. Cancel is always there
    unless hide_cancel_button=True; tapping it raises KeyboardInterrupt.

    Try it, then tap a button (or Cancel)."""
    choice = dialogs.alert('Save changes?', 'Your edits are not saved yet.',
                           'Save', "Don't save")
    return 'You tapped button %d.' % choice


@lesson.step('Ask for a line of text', background=True, docs='dialogs.input_alert')
def text():
    """input_alert(title, message, input) asks for one line and returns it.
    The third argument is what the field starts with.

    Try it: type a name, then OK."""
    name = dialogs.input_alert('Your name', 'What should I call you?', '')
    return 'Hello, %s!' % (name or 'whoever you are')


@lesson.step('A whole form', background=True, docs='dialogs.form_dialog')
def form():
    """form_dialog(title, fields) asks several things at once. Each field is
    a dict: its type (text, number, switch, check, date, url, email...), a
    key and a title. It returns {key: answer}, or None for Cancel.

    Try it: fill it in, then Done."""
    answers = dialogs.form_dialog('About you', fields=[
        {'type': 'text', 'key': 'name', 'title': 'Name', 'value': ''},
        {'type': 'number', 'key': 'age', 'title': 'Age'},
        {'type': 'switch', 'key': 'reminders', 'title': 'Reminders', 'value': True},
    ])
    if answers is None:
        return 'Cancelled: form_dialog returns None.'
    return answers


@lesson.step('Pick from a list', background=True, docs='dialogs.list_dialog')
def pick():
    """list_dialog(title, items) returns the item tapped, or None for
    Cancel. multiple=True lets the person tick several and returns a list.

    Try it: pick one."""
    fruit = dialogs.list_dialog('Pick a fruit', ['apple', 'pear', 'plum', 'quince'])
    return 'You picked %s.' % fruit if fruit else 'Nothing picked.'


@lesson.step('Messages that fade', background=True, docs='dialogs.hud_alert')
def messages():
    """hud_alert(message, icon) shows a message for a moment and carries on
    without waiting: icon is 'success' or 'error'. console.hud_alert is the
    same thing. Good for "Saved" or "Copied".

    Try it: two messages, one after the other."""
    dialogs.hud_alert('Saved', 'success')
    time.sleep(2)
    console.hud_alert('Could not reach the server', 'error')
    return 'Both shown.'


lesson.run()
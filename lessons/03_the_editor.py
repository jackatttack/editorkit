"""Lesson 3: Talking to the editor.

editorkit can mark up the code, add buttons and keys, and notice what you
do. Run this script: each step works on this very file.
"""
import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('The editor', __file__)
state = {}                       # what later steps need to undo


@lesson.step('Notes beside your code')
def notes():
    """ek.annotate(line, text, style) puts Pythonista's own banner beside a
    line. Styles are 'ok', 'warning', 'error' and 'note'. They only change
    what you see, never the file.

    Try it, then look at the code: every step in this lesson gets a note.
    (Moving to another step clears them: the lesson uses a note itself.)"""
    styles = ['ok', 'warning', 'error', 'note']
    count = 0
    for number, line in enumerate(ek.text().split('\n'), 1):
        if line.startswith('@lesson.step('):
            ek.annotate(number, line.split("'")[1], style=styles[count % len(styles)])
            count += 1
    return 'Noted %d steps.' % count


@lesson.step('Highlight words')
def words():
    """ek.highlight(term) marks every match in the open script, as
    Pythonista's own search does. ek.clear_highlights() takes them away.

    Try it: every ek. in this file lights up."""
    ek.highlight('ek.')
    return 'Every "ek." is highlighted.'


@lesson.step('A button in the toolbar')
def toolbar():
    """ek.toolbar_button(icon, action, key) adds a button to the top bar,
    just left of Run. Using the same key again replaces it, so running a
    script twice never adds two.

    Try it, then tap 🎓 at the top of the screen."""
    def tapped(sender):
        ek.show('The 🎓 toolbar button was tapped.', title='Toolbar', key='lesson-toolbar')

    ek.toolbar_button('🎓', tapped, key='lesson')
    return 'Look up: 🎓 is in the toolbar.'


@lesson.step('A window that follows your cursor')
def watch():
    """ek.on_change(callback, kinds) calls back as you work. Kinds are
    'selection', 'text', 'file', 'console' and 'keyboard'.

    Try it, then tap around the code: the window shows the line under your
    cursor. ek.show with the same key swaps its content in place."""
    def moved(event):
        chosen = ek.selection()
        if chosen is None:
            return
        line = ek.text().count('\n', 0, chosen[0]) + 1
        ek.show('Line %d' % line, title='Cursor', key='lesson-cursor')

    state['watch'] = ek.on_change(moved, kinds=['selection'], key='lesson-watch')
    moved(None)


@lesson.step('Keys of your own')
def keys():
    """ek.keyboard(keys, second_row) changes the row of keys above the
    keyboard, and can add a second row. A key types its word; in a tuple,
    the first item is the key and the rest are its long-press options.

    Try it, then tap into the code."""
    ek.keyboard(second_row=['def ', 'self', 'return ', ('True', 'False', 'None')])
    return 'Tap into the code: there is a second row of keys.'


@lesson.step('Put it all back')
def clean_up():
    """Everything editorkit changes lasts until Pythonista quits, so a good
    tool tidies up after itself: notes, highlights, toolbar buttons, keys
    and listeners all have a way back.

    Try it, then Done ✓ closes the lesson and its windows."""
    ek.clear_annotations()
    ek.clear_highlights()
    ek.remove_toolbar_button('lesson')
    ek.reset_keyboard()
    if 'watch' in state:
        ek.remove_listener(state.pop('watch'))
    return 'Everything is back to normal.'


lesson.run()
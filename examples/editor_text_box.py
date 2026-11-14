"""TextBox: a multi-line editor riding the keyboard (ek.edit_text).

Type, try ⇥ ⇤ on a line and on a selection, ↶ ↷, and the chips. ✓ prints
what you wrote to the console; ✕ cancels and keeps a draft: run this again
and ↺ Restore brings it back.
"""
import editorkit as ek

SAMPLE = 'def greet(name):\n    return "hi " + name\n'


def saved(text, name):
    print('TextBox saved %r (%d chars):\n%s' % (name, len(text), text))


ek.edit_text(SAMPLE, title='TextBox', name='greet', name_placeholder='Snippet name',
             chips=('${cursor}', '${date}', '${clipboard}'),
             on_done=saved, on_cancel=lambda: print('TextBox cancelled'),
             draft_key='lab')

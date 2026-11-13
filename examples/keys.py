"""Your own key row plus a second row of Python words."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import editorkit as ek

ek.keyboard(
    keys=[('\t', '⇤'), ('_', '__init__', '#'), ('(', '[', '{'), (')', ']', '}'),
          ("'", '"', '"""'), (',', ';'), ('.', 'self.', '->'),
          ('+', '-', '*', '/', '%'), ('=', '==', '!=', '>', '<'),
          (':', '%special:undo', '%special:redo')],
    second_row=['def ', 'self', 'return ', 'if ', 'for ', ' in ', 'None',
                ('True', 'False'), 'print(', 'import '],
)
print('Tap into a script: two rows. ek.reset_keyboard() puts it back.')

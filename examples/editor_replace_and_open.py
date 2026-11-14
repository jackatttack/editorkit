"""Replace and open: a practice file, opened in a tab, then one word swapped
for another everywhere in it.

ek.open_file(path) opens a file in a tab. ek.replace_all(term, new_text)
replaces every match in the script showing in the editor and returns how
many it replaced; Pythonista's undo puts them back. It waits a moment
after opening, so the new tab is the one showing when it replaces.
"""
import os

import ui

import editorkit as ek

# --- Settings ------------------------------------------------------------------

PRACTICE = os.path.expanduser('~/Documents/replace_practice.py')
TERM, NEW_TEXT = 'colour', 'color'
OPEN_DELAY = 0.8             # seconds for the new tab to show its text

PRACTICE_TEXT = '''"""Practice for editor_replace_and_open.py: safe to change or delete."""
colour = 'teal'
background_colour = 'black'
print('The colour is', colour)
'''


def replace_now():
    count = ek.replace_all(TERM, NEW_TEXT)
    print('Replaced %d × %s with %s. Undo puts them back.' % (count, TERM, NEW_TEXT))


def main():
    with open(PRACTICE, 'w', encoding='utf-8') as handle:
        handle.write(PRACTICE_TEXT)
    ek.open_file(PRACTICE)
    ui.delay(replace_now, OPEN_DELAY)


ek.run_tool(main)

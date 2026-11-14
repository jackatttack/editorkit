"""Clean slate: put the editor back the way Pythonista has it.

Everything editorkit adds lasts until Pythonista quits. Run this to take it
all away at once: every editorkit window closes, and notes, highlights,
toolbar buttons, views beside the code, custom keys and change listeners
are cleared. The rule behind the names: remove_X takes one thing away,
clear_X takes every one of its kind.
"""
import editorkit as ek

ek.close_windows()          # every window, Toolbox's too (they shrink away)
ek.clear_annotations()      # notes beside lines
ek.clear_highlights()       # marked words
ek.clear_toolbar()          # buttons added to the editor's toolbar
ek.clear_views()            # views pinned to lines or floating over the code
ek.clear_keyboard()         # Pythonista's own key row comes back
ek.clear_listeners()        # nothing is watching the editor any more
print('The editor is back to how Pythonista has it.')

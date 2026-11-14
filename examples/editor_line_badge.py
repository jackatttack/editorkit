"""Line badge: a button pinned beside a line of code; tap it to take it away.

ek.pin_view(view, line) keeps a view of yours beside a line as you scroll
and edit. ek.remove_view(view) takes that one view away again
(ek.clear_views() takes every one). Change LINE and run it again.
"""
import ui

import editorkit as ek

# --- Settings ------------------------------------------------------------------

LINE = 3
WORDS = '◀ tap to remove'
COLOUR = '#3b82f6'


def make_badge():
    badge = ui.Button(title=WORDS, frame=(0, 0, 130, 24))
    badge.background_color = COLOUR
    badge.tint_color = 'white'
    badge.corner_radius = 12
    badge.font = ('<system-bold>', 12)
    badge.action = lambda sender: ek.remove_view(sender)
    return badge


def main():
    ek.pin_view(make_badge(), line=LINE)
    print('Look beside line %d, then tap the badge.' % LINE)


ek.run_tool(main)

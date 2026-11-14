"""A toolbar button that marks your line, a floating panel and a pinned badge."""
import editor
import ui


import editorkit as ek


def mark_line(sender, ek=ek, editor=editor):
    # ek and editor are bound as defaults: this script's globals are cleared
    # when it ends, but the button keeps working.
    start = editor.get_selection()[0]
    line = editor.get_text()[:start].count('\n') + 1
    ek.annotate(line, 'You were here', style='note')


def badge(text, colour, width):
    view = ui.Label()
    view.text = text
    view.font = ('<System-Bold>', 12)
    view.text_color = 'white'
    view.alignment = ui.ALIGN_CENTER
    view.background_color = colour
    view.corner_radius = 9
    view.frame = (0, 0, width, 18)
    return view


ek.toolbar_button('⚡', mark_line)
ek.float_view(badge('editorkit', '#e8335a', 90))
ek.pin_view(badge('◀ line 5', '#3b82f6', 80), line=5)

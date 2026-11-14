"""A context-aware pin: drag the 👀 pin over your code and it names the line
beneath it. Scroll the code under it and the name follows. Open it to see
the whole line.

Shows: the 'under' event, set_pin_text, and a window that starts as a pin.
The callbacks only use the window they are given: this script's globals are
cleared when it ends, but the window keeps running.
"""


import ui

import editorkit as ek


def line_page(window):
    label = ui.Label(number_of_lines=0, alignment=ui.ALIGN_CENTER,
                     font=('Menlo', 13), text_color=window.palette.text)
    label.touch_enabled = False            # the window still drags through it
    window.line_label = label
    label.text = 'Rest my pin over some code.'
    return label


def pin_moved(window, under):
    """under: (line number, line text) beneath the pin, or None."""
    window.set_pin_text('line %d' % under[0] if under else None)
    label = getattr(window, 'line_label', None)
    if label is not None:
        if under is None:
            label.text = 'Rest my pin over some code.'
        else:
            label.text = 'line %d\n\n%s' % (under[0], under[1].strip()[:80] or '(blank)')


watcher = ek.Window('Under the pin', emoji='👀', size=(320, 170))
watcher.add_page('Line', line_page)
watcher.on('under', pin_moved)
watcher.minimise()                         # starts as a pin: drag it over the code

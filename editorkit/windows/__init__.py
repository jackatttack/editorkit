"""editorkit windows: themed windows over Pythonista's editor.

    import editorkit as ek

    ek.show('Hello')                         # one line: a window with one page

    win = ek.Window('Notes', emoji='📝')
    win.add_page('Today', 'Nothing yet')     # a ui.View, text, HTML, or builder(window)
    win.show()                               # also minimise(), to_dock(), to_panel(), close()
    win.on('under', lambda window, under: ...)   # the code line under its pin
    win.to_console(); win.send_pin('console')    # across by code; by hand, hold
                                                 # a pin or panel poking off the edge

A window rests as a pin, opens over the code, moves and resizes, docks in
the keyboard's place and comes back. Design: docs/WINDOWS.txt.
"""
from .window import Window, close_all, live_windows, show, stop
from .tidy import tidy
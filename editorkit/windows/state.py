"""Settings shared by the window parts, and the per-key memory that
outlives reruns (until Pythonista quits)."""
from .. import _app

# The editor's changes a window can listen to (through ek.on_change).
EDITOR_EVENTS = ('text', 'selection', 'file')
EVENTS = ('open', 'minimise', 'tray', 'dock', 'console', 'close', 'page', 'under',
          'place') + EDITOR_EVENTS


# How often the clock checks for a tab switch (each tab has its own editor
# view, and windows over the code must move into the one showing).
EDITOR_CHECK_SECONDS = 0.25


# How often every page, the sheet and the accessory get tick(now).
PAGE_TICK_SECONDS = 0.1


# Homes that are a frame over the code (Window(home=...), move_to); see
# Window._frame_for. 'dock' is the other home.
FRAME_HOMES = ('top_bar', 'above_dock')



# While a move is running, how often to check before raising the keyboard.
KEYBOARD_RETRY_SECONDS = 0.1


def _store():
    return _app.store('editorkit_windows')


def _remembered(name):
    """Per-key memory that outlives reruns until Pythonista quits: 'frames'
    (where each window was left) and 'pins' (where each pin rests)."""
    return _store().setdefault(name, {})

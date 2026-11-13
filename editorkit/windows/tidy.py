"""Tidy: lay every window open over the code out evenly, in one call.

    ek.tidy()          # again within look.TIDY_UNDO_SECONDS: puts them back

Only windows open over the code (place 'panel') move, in reading order (top
to bottom, then left to right), so tidying never shuffles them. Left alone,
and kept clear of: windows with a fixed home over the code (top_bar, as the
Find bar; above_dock), windows riding the keyboard (a Pair's view above its
keys), windows in the middle of a move, and the keyboard. tidy_frames is
pure maths, checked by tests/smoke_tidy.py.
"""
import math
import time

from .. import _app
from . import look, places
from .window import live_windows


# --- Settings -------------------------------------------------------------

FIXED_HOMES = ('top_bar', 'above_dock')
ROW_SNAP = 40                    # windows whose tops are this close count as one row


# --- The layout (pure) ------------------------------------------------------

def tidy_frames(count, area, gap=look.EDGE, min_width=look.TIDY_MIN_WIDTH,
                min_height=look.TIDY_MIN_HEIGHT, aspect=look.TIDY_ASPECT):
    """count frames filling area=(x, y, width, height), row by row. The
    number of columns is the one whose cells come nearest aspect (width /
    height) while staying at least min_width by min_height; if no count
    can, the one whose cells are least squeezed. A short last row stretches
    across. [] when count is 0 or the area has no room."""
    if count <= 0:
        return []
    x, y, width, height = area
    best = None
    for columns in range(1, count + 1):
        rows = int(math.ceil(count / float(columns)))
        cell_width = (width - gap * (columns - 1)) / float(columns)
        cell_height = (height - gap * (rows - 1)) / float(rows)
        if cell_width <= 0 or cell_height <= 0:
            continue
        fits = cell_width >= min_width and cell_height >= min_height
        squeeze = min(cell_width / min_width, cell_height / min_height)
        shape = abs(math.log((cell_width / cell_height) / aspect))
        key = (0, shape) if fits else (1, -squeeze)
        if best is None or key < best[0]:
            best = (key, columns, rows, cell_height)
    if best is None:
        return []
    _key, columns, rows, cell_height = best
    frames = []
    for row in range(rows):
        in_row = min(columns, count - row * columns)
        cell_width = (width - gap * (in_row - 1)) / float(in_row)
        top = y + row * (cell_height + gap)
        for column in range(in_row):
            frames.append((x + column * (cell_width + gap), top, cell_width, cell_height))
    return frames


def reading_order(frames):
    """Indexes of frames top to bottom, then left to right (tops within
    ROW_SNAP count as one row)."""
    return sorted(range(len(frames)),
                  key=lambda index: (round(frames[index][1] / ROW_SNAP), frames[index][0]))


# --- Tidying ----------------------------------------------------------------

def tidy_area(fixed):
    """The space over the code tidy may use: below the status bar, above the
    keyboard, clear of the windows it leaves alone."""
    width, height = places.editor_size()
    top = look.EDGE
    try:
        host = places.editor()
        if host is not None:
            top = places.safe_top(host)
    except Exception:
        pass
    bottom = height - look.EDGE
    keyboard = places.keyboard_top()
    if keyboard is not None:
        bottom = min(bottom, keyboard - look.EDGE)
    for window in fixed:
        x, y, w, h = tuple(window.panel.frame)
        if window.home == 'top_bar' or y + h / 2.0 < height / 2.0:
            top = max(top, y + h + look.EDGE)
        else:
            bottom = min(bottom, y - look.EDGE)
    return (look.EDGE, top, width - 2 * look.EDGE, max(0, bottom - top))


@_app.on_main
def tidy():
    """Lay every window open over the code out evenly; a second call within
    look.TIDY_UNDO_SECONDS (same windows) puts them back. Returns how many
    windows moved."""
    memory = _app.store('tidy')
    panels = [window for window in live_windows()
              if window.place == 'panel' and not window.is_busy()]
    fixed = [window for window in panels
             if window.home in FIXED_HOMES or getattr(window, 'riding', False)]
    movers = [window for window in panels if window not in fixed]
    keys = sorted(window.key for window in movers)
    last = memory.get('last')
    if (last and time.time() - last['time'] < look.TIDY_UNDO_SECONDS
            and last['keys'] == keys):
        memory['last'] = None
        for window in movers:
            frame = last['frames'].get(window.key)
            if frame:
                window.move_to(frame, keyboard=False)
        return len(movers)
    if not movers:
        return 0
    frames_now = [tuple(window.panel.frame) for window in movers]
    movers = [movers[index] for index in reading_order(frames_now)]
    frames = tidy_frames(len(movers), tidy_area(fixed))
    if not frames:
        return 0
    memory['last'] = {'time': time.time(), 'keys': keys,
                      'frames': dict((window.key, tuple(window.panel.frame))
                                     for window in movers)}
    for window, frame in zip(movers, frames):
        window.move_to(frame, keyboard=False)
    return len(movers)
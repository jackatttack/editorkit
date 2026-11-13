"""Tab pull: hold an editor tab and drag it down, out of the tab bar.

Pythonista's own long press on each tab drags it to reorder. editorkit adds
a second target to that same recogniser (addTarget:action:), so reordering
is untouched, and a hold that ends well below where it began is a pull:

    from editorkit import tabpull
    tabpull.on_pull(lambda path: ...)     # the pulled tab's file
    window.every(tabpull.tick)            # any long-lived window's clock: picks
                                          # up new tabs and delivers pulls

A light haptic tap marks the moment the finger crosses the line. The
callback runs on the next clock beat, not inside Pythonista's drop.

Numbers from labs/tab_hold_lab.py (2026-11-11): sideways reorders drifted
at most about 40pt down; pulls went 110 to 570pt; a still hold moves 0.
Like windows/holdmove.py: one ObjC target class per app run, calling back
through a hook on builtins that every import sets again; state on builtins.
"""
import builtins
import os
import time
import traceback

import ui
from objc_util import ObjCClass, ObjCInstance, create_objc_class, sel

from . import _app, tabs


# --- Settings -------------------------------------------------------------

PULL_DISTANCE = 80               # points below the start that make a pull
ATTACH_SECONDS = 1.5             # how often tick() looks for new tabs

# The hint while pulling: a pill with the tab's name above the finger, and a
# line across the screen at the pull distance.
PILL_HEIGHT = 28
PILL_LIFT = 48                   # the pill's centre sits this far above the finger
PILL_FONT = ('<system-bold>', 13)
PILL_MAX_WIDTH = 240
PILL_COLOUR = '#2a2e37'
PILL_TEXT_COLOUR = '#ffffff'
LINE_COLOUR = '#8a909c'
LIVE_COLOUR = '#ff2d55'          # pill and line once past the line
NOTE_FONT = ('<system>', 12)
NOTE_BEFORE = 'Pull below the line'
NOTE_PAST = 'Release: 📜 script window'

CLASS_NAME = 'EKTabPullTarget'
HANDLER_NAME = '_editorkit_tab_pull_handler'
STORE_NAME = '_editorkit_tab_pull'
TAB_CLASS = 'PA2TabView'
STRIP_CLASS = 'PA2TabScrollView'
BEGAN, CHANGED, ENDED = 1, 2, 3


# --- Pure rules (tests/smoke_tabpull.py) ------------------------------------

def is_pull(side, down, distance=PULL_DISTANCE):
    """A pull goes down past distance, and further down than sideways."""
    return down > distance and down > abs(side)


def past_line(y, line_y):
    """A pull is a finger below the pull line. Sideways reorders drift at
    most about 40pt down, so they never reach a line PULL_DISTANCE below the
    tab strip."""
    return y > line_y


def match_path(name, index_among_same, paths):
    """The open tab's path for a tab labelled name: by file name, and among
    tabs sharing that name by their order. None when nothing matches."""
    same = [path for path in paths if os.path.basename(path) == name]
    if not same:
        return None
    return same[min(index_among_same, len(same) - 1)]


# --- State ----------------------------------------------------------------

def store():
    found = getattr(builtins, STORE_NAME, None)
    if found is None:
        found = {'target': None, 'holds': {}, 'callback': None, 'strip': None,
                 'next_attach': 0.0, 'pending': None}
        setattr(builtins, STORE_NAME, found)
    return found


def on_pull(callback, window=None):
    """callback(path) when a tab is pulled down. One callback: a later call
    replaces it, so rerunning a script never adds a second. window: any
    long-lived window, whose clock then keeps new tabs attached and delivers
    pulls (otherwise call tick() from a clock yourself)."""
    store()['callback'] = callback
    if window is not None:
        window.every(tick)


def handle_(_self, _cmd, recogniser):
    handler = getattr(builtins, HANDLER_NAME, None)
    if handler is not None:
        handler(ObjCInstance(recogniser))


def target_class():
    try:
        return ObjCClass(CLASS_NAME)
    except Exception:
        return create_objc_class(CLASS_NAME, methods=[handle_])


# --- The tab bar ------------------------------------------------------------

def tab_strip():
    """Pythonista's tab strip (found once, while it stays on screen)."""
    state = store()
    strip = state['strip']
    if strip is not None and strip.window() is not None:
        return strip
    strip = None
    views = [_app.root().detailViewController().view()]
    while views:
        view = views.pop()
        if str(view.className()) == STRIP_CLASS:
            strip = view
            break
        views.extend(view.subviews())
    state['strip'] = strip
    return strip


def tab_views():
    strip = tab_strip()
    if strip is None:
        return []
    found = [view for view in strip.subviews() if str(view.className()) == TAB_CLASS]
    found.sort(key=lambda view: view.frame().origin.x)
    return found


def tab_label(view):
    label_class = ObjCClass('UILabel')
    for child in view.subviews():
        if child.isKindOfClass_(label_class):
            text = child.text()
            return str(text) if text else ''
    return ''


def path_for(view):
    name = tab_label(view)
    x = view.frame().origin.x
    earlier = [other for other in tab_views()
               if tab_label(other) == name and other.frame().origin.x < x]
    return match_path(name, len(earlier), tabs.open_tabs())


def pull_line(start_y):
    """Where a pull counts, in window points: PULL_DISTANCE below the tab
    strip's bottom edge. (Measured from where the hold began, the line landed
    near the bottom of an iPad's screen: that start point cannot be trusted
    there.) Falls back to below the start when the strip is not found."""
    strip = tab_strip()
    try:
        frame = strip.convertRect_toView_(strip.bounds(), None)
        return frame.origin.y + frame.size.height + PULL_DISTANCE
    except Exception:
        return start_y + PULL_DISTANCE


def last_trace():
    """The last hold's phases as (phase, x, y), for debugging a device:
    from editorkit import tabpull; print(tabpull.last_trace())"""
    return list(store().get('trace', []))


# --- Attaching and the clock ------------------------------------------------

def attach():
    """Add our target to every open tab's long press (new ones only), and
    forget tabs that have closed."""
    state = store()
    if state['target'] is None:
        state['target'] = target_class().alloc().init()   # kept: UIKit holds targets weakly
    current = {}
    for view in tab_views():
        for recogniser in (view.gestureRecognizers() or []):
            if str(recogniser.className()) != 'UILongPressGestureRecognizer':
                continue
            hold = state['holds'].get(recogniser.ptr)
            if hold is None:
                recogniser.addTarget_action_(state['target'], sel('handle:'))
                hold = {'start': None, 'path': None, 'crossed': False}
            current[recogniser.ptr] = hold
    state['holds'] = current


def tick(now=None):
    """On a window's clock: deliver a pull, and look for new tabs."""
    state = store()
    pending, state['pending'] = state['pending'], None
    if pending and state['callback'] is not None:
        try:
            state['callback'](pending)
        except Exception:
            traceback.print_exc()
    if time.time() >= state['next_attach']:
        state['next_attach'] = time.time() + ATTACH_SECONDS
        try:
            attach()
        except Exception:
            traceback.print_exc()


# --- Listening --------------------------------------------------------------

def tap():
    try:
        ObjCClass('UIImpactFeedbackGenerator').alloc().initWithStyle_(1).impactOccurred()
    except Exception:
        pass


class PullHint:
    """While a tab is held: a pill with its name above the finger and a
    line at the pull distance, both laid over the whole window and deaf to
    touches. live() colours them once the finger is past the line."""

    def __init__(self, name, line_y, window):
        width = window.bounds().size.width
        self.line = ui.View(frame=(0, line_y, width, 2), background_color=LINE_COLOUR)
        self.note = ui.Label(frame=(0, line_y + 6, width - 16, 18), font=NOTE_FONT,
                             alignment=ui.ALIGN_RIGHT, text=NOTE_BEFORE)
        self.note.text_color = LINE_COLOUR
        words = name or 'tab'
        pill_width = min(PILL_MAX_WIDTH, ui.measure_string(words, font=PILL_FONT)[0] + 28)
        self.pill = ui.View(frame=(0, 0, pill_width, PILL_HEIGHT), background_color=PILL_COLOUR)
        self.pill.corner_radius = PILL_HEIGHT / 2.0
        label = ui.Label(frame=(10, 0, pill_width - 20, PILL_HEIGHT), font=PILL_FONT,
                         alignment=ui.ALIGN_CENTER, text=words)
        label.text_color = PILL_TEXT_COLOUR
        self.pill.add_subview(label)
        self.past = False
        for view in (self.line, self.note, self.pill):
            view.touch_enabled = False
            window.addSubview_(view.objc_instance)

    def follow(self, x, y):
        self.pill.center = (x, y - PILL_LIFT)

    def live(self, past):
        if past == self.past:
            return
        self.past = past
        colour = LIVE_COLOUR if past else LINE_COLOUR
        self.line.background_color = colour
        self.note.text_color = colour
        self.note.text = NOTE_PAST if past else NOTE_BEFORE
        self.pill.background_color = LIVE_COLOUR if past else PILL_COLOUR

    def remove(self):
        for view in (self.line, self.note, self.pill):
            try:
                view.objc_instance.removeFromSuperview()
            except Exception:
                pass


def handle(recogniser):
    state = store()
    hold = state['holds'].get(recogniser.ptr)
    if hold is None:
        return
    phase = recogniser.state()
    point = recogniser.locationInView_(None)          # the tab's window coordinates
    trace = state.setdefault('trace', [])
    if phase == BEGAN:
        del trace[:]
    if len(trace) < 60:
        trace.append((int(phase), round(point.x), round(point.y)))
    if phase == BEGAN:
        # The path now: once the drag starts, the tab leaves the strip.
        view = recogniser.view()
        if hold.get('hint') is not None:
            hold['hint'].remove()
        line_y = pull_line(point.y)
        hold.update(start=(point.x, point.y), path=path_for(view), crossed=False,
                    hint=None, line=line_y)
        try:
            window = view.window() or ObjCClass('UIApplication').sharedApplication().keyWindow()
            hold['hint'] = PullHint(tab_label(view), line_y, window)
            hold['hint'].follow(point.x, point.y)
        except Exception:
            traceback.print_exc()
        return
    if hold['start'] is None:
        return
    pulling = past_line(point.y, hold['line'])
    hint = hold.get('hint')
    if phase == CHANGED:
        if pulling and not hold['crossed']:
            tap()
        hold['crossed'] = pulling
        if hint is not None:
            hint.follow(point.x, point.y)
            hint.live(pulling)
        return
    if hint is not None:
        hint.remove()
        hold['hint'] = None
    path, hold['start'] = hold['path'], None
    if phase == ENDED and path and pulling:
        state['pending'] = path                         # delivered on the next tick                         # delivered on the next tick                         # delivered on the next tick


setattr(builtins, HANDLER_NAME, handle)
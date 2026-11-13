"""Hold anywhere on a panel to move it.

A long press (look.HOLD_MOVE_SECONDS) anywhere on a panel lifts the window
as holding its header does; dragging then moves it and letting go lands it,
through the same Gestures._grab / _pull / _release with job 'move', so the
dock line, docking, a pull up out of the dock, flings and remembered frames
all work the same. A light haptic tap says it has been picked up.

Left alone:
- holds that start on a text view or text field (the cursor magnifier and
  text selection need them);
- views a tool marks with win.no_hold_move(view) (views with their own hold);
- any hold while a grip is already held (the header's own hold is quicker,
  and resizing is the corner grip's).

The UIKit target class is made once per app run. It calls back into Python
through builtins.<HANDLER_NAME>, which every import of this module sets
again, so a reinstalled editorkit never leaves a stale handler behind.
"""
import builtins
import time

from objc_util import ObjCClass, ObjCInstance, create_objc_class, sel

from . import look


# --- Internals ------------------------------------------------------------

CLASS_NAME = 'EKHoldMoveTarget'
HANDLER_NAME = '_editorkit_hold_move_handler'
REGISTRY_NAME = '_editorkit_hold_move_registry'
SKIPPED_CLASSES = ('UITextView', 'UITextField')

BEGAN, CHANGED, ENDED, CANCELLED, FAILED = 1, 2, 3, 4, 5


class Hold:
    """One panel's recogniser and the drag it is running."""

    def __init__(self, window, target, recogniser):
        self.window = window
        self.target = target         # kept alive: UIKit holds targets weakly
        self.recogniser = recogniser
        self.active = False
        self.last = (0.0, 0.0)
        self.last_time = 0.0
        self.speed_x = 0.0
        self.skipped = set()         # pointers of views whose holds are their own


def registry():
    """recogniser pointer -> Hold, kept on builtins so reloads share it."""
    found = getattr(builtins, REGISTRY_NAME, None)
    if found is None:
        found = {}
        setattr(builtins, REGISTRY_NAME, found)
    return found


def handle_(_self, _cmd, recogniser):
    """The UIKit action: hand over to the current Python handler."""
    handler = getattr(builtins, HANDLER_NAME, None)
    if handler is not None:
        handler(ObjCInstance(recogniser))


def target_class():
    try:
        return ObjCClass(CLASS_NAME)
    except Exception:
        return create_objc_class(CLASS_NAME, methods=[handle_])


# --- Attaching ------------------------------------------------------------

def attach(window):
    """Give window's panel hold-to-move. Called once the panel is built."""
    holds = registry()
    for pointer in [pointer for pointer, hold in holds.items()
                    if getattr(hold.window, 'place', 'closed') == 'closed']:
        del holds[pointer]                         # windows long gone
    target = target_class().alloc().init()
    recogniser = ObjCClass('UILongPressGestureRecognizer').alloc() \
        .initWithTarget_action_(target, sel('handle:'))
    recogniser.setMinimumPressDuration_(look.HOLD_MOVE_SECONDS)
    recogniser.setAllowableMovement_(look.HOLD_MOVE_SLOP)
    window.panel.objc_instance.addGestureRecognizer_(recogniser)
    holds[recogniser.ptr] = Hold(window, target, recogniser)


def skip(window, view):
    """Holds that start on view (or inside it) are left to view."""
    for hold in registry().values():
        if hold.window is window:
            hold.skipped.add(view.objc_instance.ptr)


# --- Handling -------------------------------------------------------------

def starts_on_skipped(hold, recogniser):
    panel = recogniser.view()
    point = recogniser.locationInView_(panel)
    view = panel.hitTest_withEvent_(point, None)
    while view is not None and not view.isEqual_(panel):
        if view.ptr in hold.skipped:
            return True
        for name in SKIPPED_CLASSES:
            if view.isKindOfClass_(ObjCClass(name)):
                return True
        view = view.superview()
    return False


def let_go(recogniser):
    """End this hold without moving anything (the touches go on as usual)."""
    recogniser.setEnabled_(False)
    recogniser.setEnabled_(True)


def tap():
    try:
        generator = ObjCClass('UIImpactFeedbackGenerator').alloc().initWithStyle_(1)
        generator.impactOccurred()
    except Exception:
        pass


def handle(recogniser):
    hold = registry().get(recogniser.ptr)
    if hold is None:
        return
    window = hold.window
    host = window.panel.objc_instance.superview() if window.panel is not None else None
    if host is None:
        return
    phase = recogniser.state()
    point = recogniser.locationInView_(host)
    now = time.time()
    if phase == BEGAN:
        hold.active = False
        if window.grabbing is not None or starts_on_skipped(hold, recogniser):
            let_go(recogniser)
            return
        window._grab('move')
        if window.grabbing != 'move':
            let_go(recogniser)
            return
        hold.active = True
        hold.last = (point.x, point.y)
        hold.last_time = now
        hold.speed_x = 0.0
        tap()
    elif phase == CHANGED and hold.active:
        step_x, step_y = point.x - hold.last[0], point.y - hold.last[1]
        hold.last = (point.x, point.y)
        elapsed = max(0.001, now - hold.last_time)
        hold.last_time = now
        # Smoothed like the header grip, so one jittery step does not decide a throw.
        hold.speed_x = 0.6 * (step_x / elapsed) + 0.4 * hold.speed_x
        window._pull('move', step_x, step_y)
    elif phase in (ENDED, CANCELLED, FAILED) and hold.active:
        hold.active = False
        window._release('move', hold.speed_x)


setattr(builtins, HANDLER_NAME, handle)
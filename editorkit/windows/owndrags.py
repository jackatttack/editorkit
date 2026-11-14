"""A view that owns its drags.

Pythonista slides between the editor, the console and the file browser with
pan recognisers that sit above everything a window shows, and they cancel
the touches of the views under them once a finger moves. Web pages never
notice (their scroll view takes the drag first), but a native view that
wants a swipe or a drag, a game board, has its touch cancelled. Hold
anywhere to move does the same to a slow drag.

own(view) gives view a quiet pan recogniser of its own that has no action
and cancels nothing, then tells every pan and long press above view to wait
for ours to fail. A drag that starts on view makes ours succeed, so theirs
fail and view keeps its touches. A drag that starts anywhere else never
reaches ours, so everything else behaves as before.

Safe to call again and again (from a page's tick): the work is redone only
when the views above have changed, as they do when a window moves between
the code, the console and the dock.

Found when a swipe game in a window could not be swiped.
"""
import builtins

from objc_util import ObjCClass, on_main_thread


# --- Internals ------------------------------------------------------------

REGISTRY_NAME = '_editorkit_own_drags_registry'

# Recognisers above an owned view that must wait for its drag to fail.
WAITING_CLASSES = ('UIPanGestureRecognizer', 'UILongPressGestureRecognizer')


class Claim:
    """One owned view's recogniser, and the views it was last applied under."""

    def __init__(self, recogniser):
        self.recogniser = recogniser
        self.above = None            # pointers of the views above, when applied


def registry():
    """view pointer -> Claim, kept on builtins so reloads share it."""
    found = getattr(builtins, REGISTRY_NAME, None)
    if found is None:
        found = {}
        setattr(builtins, REGISTRY_NAME, found)
    return found


def views_above(view):
    """Every view above view, nearest first, up to the screen's window."""
    above = []
    view = view.superview()
    while view is not None:
        above.append(view)
        view = view.superview()
    return above


def must_wait(recogniser, claims):
    """True for a pan or long press that is not one of our own claims."""
    if any(claim.recogniser.ptr == recogniser.ptr for claim in claims.values()):
        return False
    return any(recogniser.isKindOfClass_(ObjCClass(name)) for name in WAITING_CLASSES)


def claim_for(target, claims):
    """The Claim on this UIKit view, made the first time it is asked for."""
    claim = claims.get(target.ptr)
    if claim is not None:
        holder = claim.recogniser.view()
        if holder is not None and holder.ptr == target.ptr:
            return claim
        # A pointer reused by a new view: the old claim is not on it.
    recogniser = ObjCClass('UIPanGestureRecognizer').alloc().init()
    recogniser.setCancelsTouchesInView_(False)
    recogniser.setDelaysTouchesEnded_(False)
    target.addGestureRecognizer_(recogniser)
    claim = claims[target.ptr] = Claim(recogniser)
    return claim


# --- The one public function ------------------------------------------------

@on_main_thread
def own(view):
    """Let view (a ui.View) keep the swipes and drags that start on it.

    Returns how many recognisers were told to wait this time: 0 when nothing
    above view has changed since the last call.
    """
    target = view.objc_instance
    claims = registry()
    claim = claim_for(target, claims)

    above = views_above(target)
    pointers = tuple(each.ptr for each in above)
    if pointers == claim.above:
        return 0
    claim.above = pointers

    told = 0
    for each in above:
        for recogniser in each.gestureRecognizers() or []:
            if must_wait(recogniser, claims):
                recogniser.requireGestureRecognizerToFail_(claim.recogniser)
                told += 1
    return told
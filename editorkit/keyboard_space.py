"""The keyboard's space: low-level pieces for putting our own views in the
keyboard's place or above it. Which mode to be in, and when, is Coil's job
(coil/modes.py); this module only knows how.

Rules and history: library/guides/pythonista-keyboard-space.md.
Call from the main thread (Coil's clock and button actions already are).
"""
from objc_util import ObjCClass

from . import _app


def key_row():
    """Pythonista's own key row (OMKeyboardAccessoryView) for the open script."""
    editor = _app.editor_view()
    return None if editor is None else editor.keyboardAccessoryView()


def same(first, second):
    """True when two ObjC objects are the same object."""
    if first is None or second is None:
        return False
    return getattr(first.ptr, 'value', first.ptr) == getattr(second.ptr, 'value', second.ptr)


def refocus(text_view, become=True):
    """Show the text view's current input views. Reloads when it has focus;
    otherwise takes focus (become=True) or leaves it for the next tap."""
    if text_view.isFirstResponder():
        text_view.reloadInputViews()
        return 'reloaded'
    if become:
        text_view.becomeFirstResponder()
        return 'became first responder'
    return 'waiting for a tap in the code'


def native_text_field(text_field):
    """The UITextField inside a ui.TextField (Pythonista may wrap it)."""
    wanted = ObjCClass('UITextField')
    queue = [text_field.objc_instance]
    while queue:
        view = queue.pop(0)
        if view.isKindOfClass_(wanted):
            return view
        queue.extend(view.subviews() or [])
    return None


def ready_to_move(native_view):
    """A view that has been the keyboard view can come back unable to draw
    where you put it: switch it back to frame layout and show it."""
    native_view.setTranslatesAutoresizingMaskIntoConstraints_(True)
    native_view.setHidden_(False)
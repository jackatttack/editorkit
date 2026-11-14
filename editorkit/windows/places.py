"""Where windows live, and the editor-side pieces they need: the editor view
as the floor, pictures for hand-offs, the keyboard's place (one owner), the
code line under a point, and switching the side swipes off for a drag.

Rules: library/guides/pythonista-keyboard-space.md (Coil surface lessons).
"""
from ctypes import Structure

import ui

from objc_util import CGFloat, CGPoint, CGRect, CGSize, ObjCClass, sel

from .. import _app, keyboard_space
from . import look


def frame_of(view):
    frame = view.frame
    return (frame.x, frame.y, frame.w, frame.h)


def cg_rect(frame):
    return CGRect(CGPoint(frame[0], frame[1]), CGSize(frame[2], frame[3]))


def editor():
    return _app.editor_view()


_last_editor_size = [(0.0, 0.0)]


def editor_size():
    """(width, height) of the editor view. During a tab switch there can be
    a moment with no editor view: the last size seen stands in for it."""
    view = editor()
    if view is None:
        return _last_editor_size[0]
    size = view.frame().size
    _last_editor_size[0] = (float(size.width), float(size.height))
    return _last_editor_size[0]


def over_editor(view):
    """Add view over the code; adding it again brings it to the front. With
    no editor view (mid tab switch) this does nothing: the next follow
    puts it in place."""
    host = editor()
    if host is not None:
        host.addSubview_(view.objc_instance)


def take_away(view):
    view.objc_instance.removeFromSuperview()


def ready_to_move(view):
    keyboard_space.ready_to_move(view.objc_instance)


def picture_of(view, frame):
    """A snapshot of view, sized to frame and stretching with it, or None."""
    picture = view.objc_instance.snapshotViewAfterScreenUpdates_(False)
    if picture is not None:
        picture.setFrame_(cg_rect((0, 0, frame[2], frame[3])))
        picture.setAutoresizingMask_(look.FLEXIBLE_SIZE)
    return picture


def text_view():
    return _app.text_view()


def put_keyboard_away():
    view = text_view()
    if view is not None and view.isFirstResponder():
        view.resignFirstResponder()


def put_every_keyboard_away():
    """Put the keyboard away wherever it is: the editor, the console's
    prompt, or a field in a window (put_keyboard_away covers the editor only)."""
    put_keyboard_away()
    from objc_util import ObjCClass
    window = ObjCClass('UIApplication').sharedApplication().keyWindow()
    if window is not None:
        window.endEditing_(True)


def text_inputs(view):
    """Every UITextView and UITextField inside view (a ui view or an ObjC
    view), itself included."""
    root = view.objc_instance if hasattr(view, 'objc_instance') else view
    kinds = (ObjCClass('UITextView'), ObjCClass('UITextField'))
    found = []

    def walk(node):
        if any(node.isKindOfClass_(kind) for kind in kinds):
            found.append(node)
        for child in node.subviews():
            walk(child)
    walk(root)
    return found


def plain_keyboard(view):
    """Take the key row (input accessory) off every text input in view, so
    its keyboard is the plain system one. Pythonista attaches its own key
    row to ui text inputs too."""
    for node in text_inputs(view):
        node.setInputAccessoryView_(None)
        if node.isFirstResponder():
            node.reloadInputViews()


def keyboard_top(host=None):
    """The top of the on-screen keyboard, including any key row above its
    keys, in host's coordinates (default: the editor view); None when no
    keyboard shows."""
    x, y, width, height = ui.get_keyboard_frame()
    if height <= 0:
        return None
    view = host if host is not None else editor()
    if view is None:
        return None
    return float(view.convertPoint_fromView_(CGPoint(x, y), None).y)


def console_prompt():
    """The console's prompt line, or None. The console holds two text views,
    its output and the prompt; the prompt is the shorter one (probe
    2026-11-09: labs/console_keyboard_probe.py)."""
    container = console_container()
    if container is None:
        return None
    kind = ObjCClass('OMTextView')
    found = []

    def walk(node):
        if node.isKindOfClass_(kind):
            found.append(node)
        for child in node.subviews():
            walk(child)
    walk(container)
    if not found:
        return None
    return min(found, key=lambda view: view.bounds().size.height)


def safe_top(host):
    """Where a window can start below the status bar (and notch), in host's
    coordinates, an EDGE below it. Measured on the screen's window and
    converted: a host's own safe area can read 0 (the console's container
    does)."""
    screen = host.window()
    if screen is None:
        return look.EDGE
    top = float(screen.safeAreaInsets(restype=UIEdgeInsets, argtypes=[]).top)
    return max(look.EDGE, float(host.convertPoint_fromView_(CGPoint(0, top), None).y)
               + look.EDGE)


def bring_keyboard_up():
    """Focus the open script so the editor's own keyboard comes up."""
    view = text_view()
    if view is not None and not view.isFirstResponder():
        keyboard_space.refocus(view, become=True)


class UIEdgeInsets(Structure):
    _fields_ = [('top', CGFloat), ('left', CGFloat), ('bottom', CGFloat), ('right', CGFloat)]


def code_inset_top(view):
    """The text view's top content inset (how far the code starts down)."""
    return float(view.contentInset(restype=UIEdgeInsets, argtypes=[]).top)


def set_code_inset_top(view, top):
    """Set the text view's top content inset, leaving the other sides."""
    insets = view.contentInset(restype=UIEdgeInsets, argtypes=[])
    insets.top = top
    view.setContentInset_(insets, restype=None, argtypes=[UIEdgeInsets])


def root_view():
    """The root controller's view: above both editor and console, where
    pictures travel between them."""
    return _app.root().view()


def console_container():
    """The view Pythonista slides the console in with (its 'accessory'), or None.
    Its coordinates are where console windows live."""
    root = _app.root()
    if root is None or not root.respondsToSelector_(sel('accessoryContainerView')):
        return None
    return root.accessoryContainerView()


def console_size():
    size = console_container().bounds().size
    return float(size.width), float(size.height)


def over_console(view):
    console_container().addSubview_(view.objc_instance)


def slide_console(show, seconds):
    """Slide the console in (show) or away over seconds; it comes from the
    right. A console docked beside the editor (iPad) stays where it is.
    Its final frame is readable as soon as the slide starts (canvas throw lab)."""
    root = _app.root()
    if root.accessoryDocked():
        return
    if show:
        root.showAccessoryWithAnimationDuration_(seconds)
    else:
        root.hideAccessoryWithAnimationDuration_(seconds)


def in_root(native_view, frame):
    """frame, given in native_view's coordinates, in the root view's."""
    rect = native_view.convertRect_toView_(cg_rect(frame), root_view())
    return (float(rect.origin.x), float(rect.origin.y),
            float(rect.size.width), float(rect.size.height))


def convert(frame, from_native, to_native):
    """frame, given in from_native's coordinates, in to_native's."""
    rect = from_native.convertRect_toView_(cg_rect(frame), to_native)
    return (float(rect.origin.x), float(rect.origin.y),
            float(rect.size.width), float(rect.size.height))


def scroll_key():
    view = text_view()
    return None if view is None else round(float(view.contentOffset().y))


def line_under(view):
    """(line number, line text) of the code under view's centre, or None."""
    text_view_now = text_view()
    if text_view_now is None:
        return None
    x, y, width, height = frame_of(view)
    point = editor().convertPoint_toView_(CGPoint(x + width / 2.0, y + height / 2.0),
                                          text_view_now)
    position = text_view_now.closestPositionToPoint_(point)
    if position is None:
        return None
    offset = int(text_view_now.offsetFromPosition_toPosition_(
        text_view_now.beginningOfDocument(), position))
    text = str(text_view_now.text())
    # The text view counts in UTF-16 units; Python counts characters.
    before = text.encode('utf-16-le')[:offset * 2].decode('utf-16-le', 'ignore')
    number = before.count('\n') + 1
    lines = text.split('\n')
    return (number, lines[number - 1] if number <= len(lines) else '')


class DockPlace:
    """The one owner of the text view's input view while a window sits in the
    keyboard's place, and of Pythonista's key row while a window above the
    keyboard hides it. Gives the key row back when either ends."""

    def __init__(self):
        self.window = None
        self.text_view = None
        self.key_row = None
        self.hidden_for = None        # the window that hid the key row, if any
        self.hidden_row = None        # Pythonista's row, kept while hidden

    def take(self, window, view, host='editor'):
        """Hang view on the host's text view as its keyboard: the script's
        text view ('editor') or the console's prompt line ('console')."""
        text_view_now = console_prompt() if host == 'console' else text_view()
        if text_view_now is None:
            return False
        if self.window is None:
            if host == 'console':
                self.key_row = text_view_now.inputAccessoryView()
            else:
                # While a window hides the row, the accessory is empty: keep
                # the real row to give back, never the empty one.
                self.key_row = (self.hidden_row if self.hidden_for is not None
                                else keyboard_space.key_row())
        self.window = window
        self.text_view = text_view_now
        ready_to_move(view)
        text_view_now.setInputView_(view.objc_instance)
        text_view_now.setInputAccessoryView_(None)
        keyboard_space.refocus(text_view_now, become=True)
        return True

    def give_back(self, window):
        if self.window is not window:
            return
        self.window = None
        text_view_then = self.text_view
        if text_view_then is None:
            return
        if text_view_then.isFirstResponder():
            text_view_then.resignFirstResponder()
        text_view_then.setInputView_(None)
        text_view_then.setInputAccessoryView_(self.key_row)

    def lost(self):
        """True when the keyboard was put away while a window sat there."""
        return (self.window is not None and self.text_view is not None
                and not self.text_view.isFirstResponder())

    def keep_row_off(self):
        """While a window holds the keyboard's place, keep the host's key row
        off: Pythonista puts its row back on a focused text view now and
        then, which stacks it above our keys. Run from the Manager's clock."""
        view = self.text_view
        if self.window is None or view is None or not view.isFirstResponder():
            return
        if view.inputAccessoryView() is not None:
            view.setInputAccessoryView_(None)
            view.reloadInputViews()

    def hide_key_row(self, window):
        """Take Pythonista's key row off the keyboard while window sits above
        it. The Manager's clock gives it back (restore_key_row)."""
        view = text_view()
        if view is None:
            return False
        if self.hidden_for is None:
            self.hidden_row = keyboard_space.key_row()
        self.hidden_for = window
        view.setInputAccessoryView_(None)
        if view.isFirstResponder():
            view.reloadInputViews()
        return True

    def restore_key_row(self, window):
        if self.hidden_for is not window:
            return
        self.hidden_for = None
        row, self.hidden_row = self.hidden_row, None
        view = text_view()
        # While a window holds the keyboard's place, give_back restores it.
        if view is None or row is None or self.window is not None:
            return
        view.setInputAccessoryView_(row)
        if view.isFirstResponder():
            view.reloadInputViews()


class SwipeBlock:
    """Switches off the gesture recognisers above the editor (the side swipes
    for the file browser and console) while a drag is on. Only ones that were
    on are switched off, and exactly those come back."""

    def __init__(self):
        self.switched_off = []

    @property
    def active(self):
        return bool(self.switched_off)

    def block(self, start=None):
        """Switch off the recognisers on start (default: the editor view) and
        every view above it."""
        if self.switched_off or not look.BLOCK_SWIPES:
            return
        view = start if start is not None else editor()
        while view is not None:
            for recogniser in view.gestureRecognizers() or []:
                if recogniser.isEnabled():
                    recogniser.setEnabled_(False)
                    self.switched_off.append(recogniser)
            view = view.superview()

    def release(self):
        for recogniser in self.switched_off:
            recogniser.setEnabled_(True)
        self.switched_off = []
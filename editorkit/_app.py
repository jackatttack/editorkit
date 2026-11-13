"""Shared plumbing: finding Pythonista's parts, the main thread, keeping
things alive after a script ends."""
import builtins
import functools

from objc_util import ObjCClass, on_main_thread

PREFIX = '_editorkit_'
VIEW_TAG = 0x45444B54        # 'EDKT': marks every view editorkit adds
DARK_INTERFACE = 2


def on_main(function):
    """Run function on the main thread and hand back its result or error."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        box = {}

        @on_main_thread
        def call():
            try:
                box['result'] = function(*args, **kwargs)
            except Exception as error:
                box['error'] = error
        call()
        if 'error' in box:
            raise box['error']
        return box.get('result')
    return wrapper


def store(name, factory=dict):
    """A container that outlives the script (Pythonista clears script globals)."""
    key = PREFIX + name
    value = getattr(builtins, key, None)
    if value is None:
        value = factory()
        setattr(builtins, key, value)
    return value


def class_name(view):
    name = view._get_objc_classname()
    return name.decode() if isinstance(name, bytes) else str(name)


def find_first(view, wanted):
    if class_name(view) == wanted:
        return view
    for subview in view.subviews():
        found = find_first(subview, wanted)
        if found is not None:
            return found
    return None


def root():
    """PASlidingContainerViewController: library, editor tabs and console."""
    return ObjCClass('UIApplication').sharedApplication().keyWindow().rootViewController()


def editor_view():
    """The open script's OMTextEditorView (never the console's input line).
    Each tab has its own; with several, the one on screen."""
    found = []
    find_all(root().detailViewController().view(), 'OMTextEditorView', found)
    for view in found:
        if _showing(view):
            return view
    return found[0] if found else None


def find_all(view, wanted, found):
    """Every view of class wanted under view (not looking inside matches)."""
    if class_name(view) == wanted:
        found.append(view)
        return
    for subview in view.subviews():
        find_all(subview, wanted, found)


def _showing(view):
    """True when view is in a window and nothing above it is hidden."""
    if view.window() is None:
        return False
    while view is not None:
        if view.isHidden() or view.alpha() < 0.01:
            return False
        view = view.superview()
    return True


def text_view():
    editor = editor_view()
    return None if editor is None else editor.textView()


def toolbar():
    return find_first(root().detailViewController().view(), 'OMTabViewToolbar')


def prepare(view, dark=True):
    """Tag a ui.View for clean-up and, by default, force dark appearance."""
    native = view.objc_instance
    native.setTag_(VIEW_TAG)
    if dark:
        native.setOverrideUserInterfaceStyle_(DARK_INTERFACE)
    return native
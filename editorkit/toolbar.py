"""Buttons in the editor's top toolbar, just left of Pythonista's own."""
import ui

from . import _app

BUTTON_SIZE = 40


def _buttons():
    return _app.store('toolbar', dict)     # key -> ui.Button, in order


def _anchor(bar):
    """x of Pythonista's leftmost right-hand button (Run), and the row's y."""
    width = bar.frame().size.width
    xs, y = [], 51
    for subview in bar.subviews():
        if _app.class_name(subview) == 'OMBarButton':
            frame = subview.frame()
            y = frame.origin.y
            if frame.origin.x > width / 2:
                xs.append(frame.origin.x)
    return (min(xs) if xs else width - BUTTON_SIZE), y


def _layout(bar):
    left, y = _anchor(bar)
    for slot, button in enumerate(_buttons().values()):
        button.frame = (left - (slot + 1) * BUTTON_SIZE, y, BUTTON_SIZE, BUTTON_SIZE)


def _remove(key):
    button = _buttons().pop(key, None)
    if button is not None:
        button.objc_instance.removeFromSuperview()


@_app.on_main
def toolbar_button(title, action, key=None):
    """Add a button; action(sender) runs on tap. Same key replaces it."""
    bar = _app.toolbar()
    if bar is None:
        return None
    key = key or title
    _remove(key)
    button = ui.Button()
    button.title = title            # title before frame, or it shrink-wraps
    button.font = ('<System-Bold>', 20)
    button.action = action
    button.frame = (0, 0, BUTTON_SIZE, BUTTON_SIZE)
    bar.addSubview_(_app.prepare(button, dark=False))   # follows the theme's tint
    _buttons()[key] = button
    _layout(bar)
    return button


@_app.on_main
def remove_toolbar_button(key):
    _remove(key)
    bar = _app.toolbar()
    if bar is not None:
        _layout(bar)


@_app.on_main
def clear_toolbar():
    for key in list(_buttons()):
        _remove(key)
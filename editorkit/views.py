"""Your own views in the editor: floating over it, or pinned to a line.

A floating view stays put while the code scrolls. A pinned view lives inside
the text's scroll view, so it scrolls with the code; it stays on its line
number and is re-placed when the text changes.
"""
from . import _app, events


def _pins():
    return _app.store('pins', list)


def _floats():
    return _app.store('floats', list)


def line_top(text_view, line):
    """(top y, height) of line (1-based) in the text view, or None."""
    paragraphs = str(text_view.text()).split('\n')
    if line < 1 or line > len(paragraphs):
        return None
    index = sum(len(paragraph) + 1 for paragraph in paragraphs[:line - 1])
    rect = text_view.caretRectForIndex_(index)
    height = rect.size.height
    # The caret rect's height is negative: its origin is the line's bottom.
    top = rect.origin.y + height if height < 0 else rect.origin.y
    return top, abs(height)


def _place(entry):
    view, text_view = entry['view'], entry['text_view']
    found = line_top(text_view, entry['line'])
    if found is None:
        view.hidden = True
        return
    top, line_height = found
    view.hidden = False
    x = entry['x']
    if x is None:
        x = text_view.frame().size.width - view.width - 12
    view.frame = (x, top + (line_height - view.height) / 2, view.width, view.height)


def _repin(event=None):
    for entry in list(_pins()):
        try:
            _place(entry)
        except Exception:
            pass


@_app.on_main
def pin(view, line, x=None):
    """Pin a ui.View (sized by you) to line; x None keeps it at the right edge."""
    text_view = _app.text_view()
    if text_view is None:
        return None
    entry = {'view': view, 'line': line, 'x': x, 'text_view': text_view}
    text_view.addSubview_(_app.prepare(view))
    _place(entry)
    _pins().append(entry)
    objects = _app.store('objects')
    if 'pin_listener' not in objects:
        objects['pin_listener'] = events.on_change(_repin, kinds=('text',))
    return view


@_app.on_main
def float_view(view, x=None, y=12):
    """Float a ui.View (sized by you) over the editor; x None is the right edge."""
    editor = _app.editor_view()
    if editor is None:
        return None
    if x is None:
        x = editor.frame().size.width - view.width - 12
    view.frame = (x, y, view.width, view.height)
    editor.addSubview_(_app.prepare(view))
    _floats().append(view)
    return view


@_app.on_main
def remove_view(view):
    view.objc_instance.removeFromSuperview()
    _pins()[:] = [entry for entry in _pins() if entry['view'] is not view]
    if view in _floats():
        _floats().remove(view)


@_app.on_main
def clear_views():
    for entry in list(_pins()):
        entry['view'].objc_instance.removeFromSuperview()
    for view in list(_floats()):
        view.objc_instance.removeFromSuperview()
    del _pins()[:]
    del _floats()[:]
    listener = _app.store('objects').pop('pin_listener', None)
    if listener is not None:
        events.remove_listener(listener)
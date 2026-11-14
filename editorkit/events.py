"""Find out when the editor changes.

Pythonista has no public events, and subscribing to its notifications from
Python crashes it, so editorkit polls four times a second and compares.
Kinds: file (tab or file switched), text, selection, console (shown or
hidden), keyboard (up or down).
"""
import hashlib

import editor as pythonista_editor
import ui

from . import _app

TICK_SECONDS = 0.25
KINDS = ('file', 'text', 'selection', 'console', 'keyboard')


def snapshot():
    state = {}
    try:
        state['file'] = pythonista_editor.get_path() or ''
        text = pythonista_editor.get_text() or ''
        state['text'] = (len(text), hashlib.md5(text.encode('utf-8')).hexdigest())
        state['selection'] = tuple(pythonista_editor.get_selection() or ())
    except Exception:
        pass
    try:
        state['console'] = bool(_app.root().accessoryVisible())
    except Exception:
        pass
    try:
        text_view = _app.text_view()
        state['keyboard'] = bool(text_view is not None and text_view.isFirstResponder())
    except Exception:
        pass
    return state


def changes(old, new):
    """(kind, before, after) for every kind that changed."""
    return [(kind, old.get(kind), new[kind]) for kind in KINDS
            if kind in new and old.get(kind) != new[kind]]


def _listeners():
    return _app.store('listeners', list)


def _dispatch(kind, before, after):
    for entry in list(_listeners()):
        if entry['kinds'] and kind not in entry['kinds']:
            continue
        try:
            entry['callback']({'kind': kind, 'old': before, 'new': after})
        except Exception as error:
            if not entry.get('warned'):
                entry['warned'] = True
                print('editorkit: an on_change callback failed: %r' % error)


class Poller(ui.View):
    def __init__(self):
        self.last = None
        self.background_color = (0, 0, 0, 0)
        self.frame = (0, 0, 1, 1)
        self.update_interval = TICK_SECONDS

    def update(self):
        state = snapshot()
        if self.last is not None:
            for kind, before, after in changes(self.last, state):
                _dispatch(kind, before, after)
        self.last = state


@_app.on_main
def _ensure_poller():
    objects = _app.store('objects')
    poller = objects.get('poller')
    if poller is not None and poller.objc_instance.superview() is not None:
        return
    poller = Poller()
    _app.prepare(poller)
    _app.root().detailViewController().view().addSubview_(poller.objc_instance)
    objects['poller'] = poller


def on_change(callback, kinds=None, key=None):
    """callback({'kind', 'old', 'new'}) on every change, or only the given kinds.
    With a key, a listener of the same key is replaced, so a script that runs
    again never adds a second one. Returns a handle for remove_listener."""
    _ensure_poller()
    listeners = _listeners()
    if key is not None:
        listeners[:] = [entry for entry in listeners if entry.get('key') != key]
    entry = {'callback': callback, 'kinds': tuple(kinds or ()), 'key': key}
    listeners.append(entry)
    return entry


def remove_listener(handle):
    if handle in _listeners():
        _listeners().remove(handle)


@_app.on_main
def clear_listeners():
    del _listeners()[:]
    poller = _app.store('objects').pop('poller', None)
    if poller is not None:
        poller.update_interval = 0
        poller.objc_instance.removeFromSuperview()
"""Stores: small named state that survives quitting.

    deck = ek.store('deck')            # Documents/.editorkit/store/deck.json
    deck['recent'] = ['calc', 'files']
    deck.get('favourites', [])
    deck.save()                        # now; otherwise it saves itself shortly

A store is a dict of JSON values, one file per name. The same name gives the
same store for the whole Pythonista session (kept on builtins, so module
reloads share it). Changes are written SAVE_DELAY seconds after the last
one, on a background thread, through a temporary file and os.replace, so a
crash never leaves half a file. A value JSON cannot hold is refused when it
is set, not later. A file that cannot be read is set aside as
name.json.broken and the store starts empty.

Only top-level assignment is noticed: after changing a list in place,
assign it back (store['recent'] = recent) or call store.save().

Pure Python: no ui, no Pythonista imports (tests/smoke_store.py).
"""
import builtins
import json
import os
import threading


# --- Settings -------------------------------------------------------------

FOLDER = os.path.expanduser('~/Documents/.editorkit/store')
SAVE_DELAY = 0.5              # seconds of quiet before a change is written
CACHE_NAME = '_editorkit_stores'   # on builtins: path -> Store


def store(name, folder=None):
    """The store called name (a plain word: it becomes a file name)."""
    path = os.path.join(folder or FOLDER, name + '.json')
    cache = builtins.__dict__.setdefault(CACHE_NAME, {})
    found = cache.get(path)
    if found is None:
        found = cache[path] = Store(path)
    return found


class Store:
    """A dict of JSON values kept in one file. Use store(name) rather than
    making one directly, so a name always means one object."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()   # the data and the timer, across threads
        self.timer = None
        self.data = self._load()

    # --- Reading ----------------------------------------------------------

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)

    def keys(self):
        return list(self.data.keys())

    def items(self):
        return list(self.data.items())

    # --- Changing ---------------------------------------------------------

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError('store keys are strings, not %r' % (key,))
        json.dumps(value)              # TypeError now for what JSON cannot hold
        with self.lock:
            self.data[key] = value
        self._changed()

    def __delitem__(self, key):
        with self.lock:
            del self.data[key]
        self._changed()

    def pop(self, key, default=None):
        with self.lock:
            if key not in self.data:
                return default
            value = self.data.pop(key)
        self._changed()
        return value

    def update(self, other=(), **more):
        for key, value in dict(other, **more).items():
            self[key] = value

    # --- Saving -----------------------------------------------------------

    def save(self):
        """Write the store now (the timer also calls this)."""
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            text = json.dumps(self.data, indent=1, sort_keys=True, ensure_ascii=False)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.replace(temporary, self.path)

    def _changed(self):
        """Save SAVE_DELAY seconds after the last change."""
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(SAVE_DELAY, self.save)
            self.timer.daemon = True
            self.timer.start()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding='utf-8') as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError('not a JSON object')
            return data
        except (ValueError, OSError) as error:
            broken = self.path + '.broken'
            try:
                os.replace(self.path, broken)
            except OSError:
                pass
            print('editorkit store: could not read %s (%s); set aside as %s'
                  % (self.path, error, broken))
            return {}
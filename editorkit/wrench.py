"""The wrench menu: list, add and remove its entries (Pythonista keeps
them in its settings as EditorActionInfos: one small dict per entry).

    ek.wrench_actions()                   # [{'script', 'title', 'icon', 'colour'}]
    ek.add_wrench_action('projects/me/tool.py', 'My tool',
                         icon='Primaries_Home', colour='#F26EFF')
    ek.remove_wrench_action('projects/me/tool.py')

Scripts are paths relative to Documents (a full path is made relative).
Adding a script that is already there updates its entry instead, so an
installer can run again without duplicates. plan_add and plan_remove are
pure (tests/smoke_wrench.py). Found 2026-11-11 (RELEASE.txt 5.2).
"""
import os

SETTINGS_KEY = 'EditorActionInfos'
DOCUMENTS = os.path.expanduser('~/Documents')
DEFAULT_ICON = 'Primaries_Home'
DEFAULT_COLOUR = '#F26EFF'


# --- Pure ---------------------------------------------------------------------

def relative_script(path):
    """path relative to Documents, as the wrench menu stores it."""
    if os.path.isabs(path):
        path = os.path.relpath(os.path.realpath(path), os.path.realpath(DOCUMENTS))
    return path.replace(os.sep, '/')


def stored_colour(colour):
    """'#f26eff' -> 'F26EFF' (the settings keep hex without #, upper case)."""
    return (colour or DEFAULT_COLOUR).lstrip('#').upper()


def entry_for(script, title, icon=DEFAULT_ICON, colour=DEFAULT_COLOUR):
    return {'scriptName': relative_script(script), 'title': title,
            'iconName': icon or DEFAULT_ICON, 'iconColor': stored_colour(colour)}


def plan_add(entries, entry):
    """entries with entry added at the end, or put in place of the entry
    for the same script (so running an installer twice changes nothing)."""
    result, replaced = [], False
    for existing in entries:
        if existing.get('scriptName') == entry['scriptName']:
            result.append(dict(entry))
            replaced = True
        else:
            result.append(dict(existing))
    if not replaced:
        result.append(dict(entry))
    return result


def plan_remove(entries, script):
    wanted = relative_script(script)
    return [dict(entry) for entry in entries if entry.get('scriptName') != wanted]


def friendly(entry):
    return {'script': entry.get('scriptName', ''), 'title': entry.get('title', ''),
            'icon': entry.get('iconName', ''), 'colour': '#' + entry.get('iconColor', '')}


# --- Settings -------------------------------------------------------------------

def _defaults():
    from objc_util import ObjCClass
    return ObjCClass('NSUserDefaults').standardUserDefaults()


def _read():
    stored = _defaults().objectForKey_(SETTINGS_KEY)
    entries = []
    if stored is None:
        return entries
    for index in range(stored.count()):
        item = stored.objectAtIndex_(index)
        entries.append(dict((str(key), str(item.objectForKey_(key))) for key in item.allKeys()))
    return entries


def _write(entries):
    from objc_util import ns
    defaults = _defaults()
    defaults.setObject_forKey_(ns([dict(entry) for entry in entries]), SETTINGS_KEY)
    defaults.synchronize()


def wrench_actions():
    """The wrench menu's entries, in order, as plain dicts."""
    return [friendly(entry) for entry in _read()]


def add_wrench_action(script, title, icon=DEFAULT_ICON, colour=DEFAULT_COLOUR):
    """Add script to the wrench menu (or update its entry). Returns the entry."""
    entry = entry_for(script, title, icon, colour)
    _write(plan_add(_read(), entry))
    return friendly(entry)


def remove_wrench_action(script):
    """Take script's entry out of the wrench menu. True if one was there."""
    entries = _read()
    kept = plan_remove(entries, script)
    if len(kept) == len(entries):
        return False
    _write(kept)
    return True
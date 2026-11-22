"""Scratch pads: throwaway Python in one folder, never beside your code.

    path = scratch_pads.new_pad()               # scratch/pads/pad_20261122_1035.py
    for pad in scratch_pads.pads():             # newest first
        pad.path, pad.name, pad.modified, pad.pinned
    scratch_pads.set_pinned(pad.name, True)     # 📌: kept by Clean
    pads_to_go, strays = scratch_pads.clean_plan()
    deleted, failed = scratch_pads.delete_files(pads_to_go + strays)

Every pad lives in PADS_FOLDER. Clean deletes the pads that are not pinned,
plus strays: the scratch_pad.py files the old scratch buttons left beside
scripts anywhere in Documents (STRAY_NAME). Deleting is for real, no
_to_delete. Pins and the auto-clean setting live in SETTINGS_FILE inside
the pads folder.

Pure Python (no ui, no editorkit): the Scratch tool (scratch_tool.py) draws
it, tests/smoke_scratch_pads.py checks it in a temporary folder.
"""
import json
import os
import re
import time
from collections import namedtuple


# --- Settings ---------------------------------------------------------------

DOCUMENTS = os.path.expanduser('~/Documents')
PADS_FOLDER = os.path.join(DOCUMENTS, 'scratch', 'pads')
PAD_STEM = 'pad'
PAD_TIME_FORMAT = '%Y%m%d_%H%M'          # pad_20261122_1035.py
PAD_TEXT = '# Scratch pad: throwaway code. Scratch\'s 🧹 Clean deletes it unless it is 📌 kept.\n\n'
SETTINGS_FILE = '.scratch.json'          # in the pads folder: pins and auto-clean
DEFAULT_SETTINGS = {'pinned': [], 'auto_clean_days': 0}    # 0: auto-clean off
AUTO_CLEAN_CHOICES = (0, 1, 3, 7, 30)    # days the settings page offers

# The old scratch buttons' files: scratch_pad.py, scratch_pad_2.py ...
STRAY_NAME = re.compile(r'^scratch_pad(_\d+)?\.py$')
# Folders the stray search never walks into: installed packages and any
# hidden folder (Pythonista's own, .forge, .git).
SKIP_FOLDERS = ('site-packages', 'site-packages-2', 'site-packages-3')


# --- Machinery ----------------------------------------------------------------

Pad = namedtuple('Pad', 'path name modified pinned')
Pad.__doc__ = """One pad: its path, file name, modified time (seconds) and
whether it is pinned (kept by Clean)."""


# --- Pads ---------------------------------------------------------------------

def pads(folder=PADS_FOLDER):
    """Every pad in folder, newest first. No folder yet: []."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    pinned = set(load_settings(folder)['pinned'])
    found = []
    for name in names:
        path = os.path.join(folder, name)
        if name.endswith('.py') and os.path.isfile(path):
            found.append(Pad(path, name, os.path.getmtime(path), name in pinned))
    return sorted(found, key=lambda pad: pad.modified, reverse=True)


def new_pad(folder=PADS_FOLDER, now=None, text=PAD_TEXT):
    """Make a pad named for the time (pad_2.py style suffix if that minute
    is taken) and return its path. Makes the folder the first time."""
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime(PAD_TIME_FORMAT, time.localtime(now))
    stem = '%s_%s' % (PAD_STEM, stamp)
    path = os.path.join(folder, stem + '.py')
    number = 2
    while os.path.exists(path):
        path = os.path.join(folder, '%s_%d.py' % (stem, number))
        number += 1
    with open(path, 'x', encoding='utf-8') as handle:
        handle.write(text)
    return path


def set_pinned(name, pinned, folder=PADS_FOLDER):
    """📌 a pad by file name (kept by Clean), or let it go."""
    settings = load_settings(folder)
    names = [kept for kept in settings['pinned'] if kept != name]
    if pinned:
        names.append(name)
    settings['pinned'] = names
    save_settings(settings, folder)


# --- Cleaning -------------------------------------------------------------------

def clean_plan(folder=PADS_FOLDER, root=DOCUMENTS):
    """(pads to delete, strays to delete): the unpinned pads, and every
    stray scratch_pad file under root outside the pads folder."""
    return [pad.path for pad in pads(folder) if not pad.pinned], strays(root, folder)


def stale_pads(days, folder=PADS_FOLDER, now=None):
    """Unpinned pads not changed for days (auto-clean). days 0: none."""
    if not days:
        return []
    cutoff = (time.time() if now is None else now) - days * 86400
    return [pad.path for pad in pads(folder) if not pad.pinned and pad.modified < cutoff]


def strays(root=DOCUMENTS, folder=PADS_FOLDER):
    """Paths of old scratch_pad files under root, skipping installed
    packages, hidden folders and the pads folder itself."""
    found = []
    pads_folder = os.path.abspath(folder)
    for current, folders, names in os.walk(root):
        folders[:] = [name for name in folders
                      if not name.startswith('.') and name not in SKIP_FOLDERS
                      and os.path.abspath(os.path.join(current, name)) != pads_folder]
        found.extend(os.path.join(current, name) for name in names if STRAY_NAME.match(name))
    return sorted(found)


def delete_files(paths):
    """Delete each path for real. Returns (deleted, failed) counts; a file
    already gone counts as deleted."""
    deleted = failed = 0
    for path in paths:
        try:
            os.remove(path)
            deleted += 1
        except FileNotFoundError:
            deleted += 1
        except OSError:
            failed += 1
    return deleted, failed


# --- Settings file ------------------------------------------------------------------

def load_settings(folder=PADS_FOLDER):
    """The pads folder's settings, with defaults for anything missing. A file
    that will not read gives the defaults (and is replaced on the next save)."""
    settings = dict(DEFAULT_SETTINGS, pinned=[])
    try:
        with open(os.path.join(folder, SETTINGS_FILE), encoding='utf-8') as handle:
            stored = json.load(handle)
        if isinstance(stored, dict):
            settings.update({key: stored[key] for key in DEFAULT_SETTINGS if key in stored})
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings, folder=PADS_FOLDER):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, SETTINGS_FILE), 'w', encoding='utf-8') as handle:
        json.dump(settings, handle, indent=1)


def set_auto_clean_days(days, folder=PADS_FOLDER):
    settings = load_settings(folder)
    settings['auto_clean_days'] = int(days)
    save_settings(settings, folder)
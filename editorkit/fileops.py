"""File actions for tools: rename, duplicate, move, and a delete that only
moves things aside.

Pure Python (os, shutil; no ui), so tests/smoke_fileops.py checks it
headless. Every action refuses rather than overwrites: a name already
taken raises FileExistsError, an unusable name or move raises ValueError.
trash() never deletes: it moves the item into TRASH_FOLDER at the top of
Documents, stamped with the time, to be emptied by hand.

    from editorkit import fileops
    new_path = fileops.rename(path, 'better_name.py')
"""
import os
import shutil
import time


# --- Settings -------------------------------------------------------------

TRASH_FOLDER = '_to_delete'
COPY_WORD = 'copy'


def check_name(name):
    name = (name or '').strip()
    if not name or name in ('.', '..') or '/' in name:
        raise ValueError('Not a usable name: %r' % name)
    return name


def rename(path, new_name):
    """Rename path in its own folder; returns the new path."""
    new_name = check_name(new_name)
    target = os.path.join(os.path.dirname(path), new_name)
    if os.path.exists(target):
        raise FileExistsError('%s already exists here.' % new_name)
    os.rename(path, target)
    return target


def copy_name(path):
    """'name copy.ext', or 'name copy 2.ext' and so on, whichever is free."""
    folder, name = os.path.split(os.path.normpath(path))
    stem, extension = (name, '') if os.path.isdir(path) else os.path.splitext(name)
    number = 1
    while True:
        suffix = ' %s' % COPY_WORD if number == 1 else ' %s %d' % (COPY_WORD, number)
        candidate = os.path.join(folder, stem + suffix + extension)
        if not os.path.exists(candidate):
            return candidate
        number += 1


def duplicate(path):
    """Copy a file or folder beside itself; returns the copy's path."""
    target = copy_name(path)
    if os.path.isdir(path):
        shutil.copytree(path, target)
    else:
        shutil.copy2(path, target)
    return target


def move(path, folder):
    """Move a file or folder into folder; returns its new path."""
    path, folder = os.path.normpath(path), os.path.normpath(folder)
    if not os.path.isdir(folder):
        raise ValueError('Not a folder: %s' % folder)
    if folder == path or folder.startswith(path + os.sep):
        raise ValueError('A folder cannot move into itself.')
    target = os.path.join(folder, os.path.basename(path))
    if os.path.exists(target):
        raise FileExistsError('%s is already there.' % os.path.basename(path))
    shutil.move(path, target)
    return target


def trash(path, documents):
    """Move a file or folder into documents/TRASH_FOLDER, its name stamped
    with the time; returns where it went."""
    folder = os.path.join(documents, TRASH_FOLDER)
    os.makedirs(folder, exist_ok=True)
    stamped = '%s_%s' % (time.strftime('%Y%m%d_%H%M%S'), os.path.basename(os.path.normpath(path)))
    target = os.path.join(folder, stamped)
    number = 2
    while os.path.exists(target):
        target = os.path.join(folder, '%s_%d' % (stamped, number))
        number += 1
    shutil.move(path, target)
    return target
"""Stand-in tabs: a window resting in Pythonista's tab row (the 'tab' place).

A window sent to the tab row (Window.to_tab, a drag up into the row, or
minimise_to='tab') is shown there by a stand-in file opened as a tab. The
file is named with the window's emoji and title, with no extension, so the
tab reads like the window ("🔎 Find"). Each window's file sits in a folder
named from its key, so two windows with one title never share a tab.

Selecting the tab brings the window out over the code; choosing another tab
puts it back; closing the tab closes the window (Manager.follow_tabs). The
file is rewritten each time a window goes in, so stray typing never lasts.
"""
import os
import re


# --- Settings -------------------------------------------------------------

FOLDER = os.path.expanduser('~/Documents/.editorkit/tab_windows')
EXTENSION = ''               # '' reads cleanest; '.txt' if a file with none will not open as a tab
OPEN_GRACE_SECONDS = 2.0     # a new stand-in tab may not be listed yet: do not read that as closed
TEXT = ('This tab holds an editorkit window ({title}).\n'
        'Select the tab to show it; close the tab to close it.\n')


def safe_name(text):
    """text as one file or folder name (no slashes, colons or nulls)."""
    return re.sub(r'[\\/:\x00]', '-', text).strip() or 'window'


def stand_in_path(key, emoji, title):
    name = '%s %s' % (emoji, title) if title else emoji
    return os.path.join(FOLDER, safe_name(str(key)), safe_name(name) + EXTENSION)


def write_stand_in(path, title):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(TEXT.format(title=title or 'window'))


def same_path(first, second):
    return bool(first) and bool(second) and os.path.realpath(first) == os.path.realpath(second)


def is_stand_in(path):
    return bool(path) and os.path.realpath(path).startswith(os.path.realpath(FOLDER) + os.sep)
"""Browsing folders: what is in a folder, in a stable order, with icons.

Pure Python (no ui), so tests/smoke_browse.py checks it headless. The
Folders tile draws what list_folder returns; the full browser (planned)
adds details and previews on top.

    from editorkit import browse
    for entry in browse.list_folder(folder):
        print(browse.icon(entry), entry.name)
"""
import collections
import os


# --- Settings -------------------------------------------------------------

HIDDEN_NAMES = ('__pycache__',)          # never shown
FOLDER_ICON = '📁'
FILE_ICON = '📄'
ICONS = {                                # by extension, lower case
    '.py': '🐍',
    '.pyui': '🧩',
    '.md': '📝',
    '.txt': '📄',
    '.json': '🔧',
    '.html': '🌐',
    '.js': '🌐',
    '.css': '🎨',
    '.png': '🖼️',
    '.jpg': '🖼️',
    '.jpeg': '🖼️',
    '.gif': '🖼️',
    '.zip': '📦',
}


Entry = collections.namedtuple('Entry', 'name path is_folder extension')
Entry.__doc__ = """One thing in a folder: name, full path, is_folder, and
extension (lower case, '' for a folder)."""


def entry_for(path):
    """The Entry for a path (a folder or a file)."""
    path = os.path.normpath(path)
    is_folder = os.path.isdir(path)
    extension = '' if is_folder else os.path.splitext(path)[1].lower()
    return Entry(os.path.basename(path) or path, path, is_folder, extension)


def hidden(name, show_hidden=False):
    if name in HIDDEN_NAMES:
        return True
    return name.startswith('.') and not show_hidden


def list_folder(folder, folders_only=False, show_hidden=False):
    """What is in folder: folders first, then files, each by name ignoring
    case. [] when the folder cannot be read."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    entries = [entry_for(os.path.join(folder, name)) for name in names
               if not hidden(name, show_hidden)]
    if folders_only:
        entries = [entry for entry in entries if entry.is_folder]
    entries.sort(key=lambda entry: (not entry.is_folder, entry.name.casefold()))
    return entries


def icon(entry):
    if entry.is_folder:
        return FOLDER_ICON
    return ICONS.get(entry.extension, FILE_ICON)
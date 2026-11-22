"""Files on cards: a folder as a page of file tiles. Pure: no ui.

    page = files_page.folder_page(folder, DOCUMENTS, entries, facts_for,
                                  selected=path, target=path)
    board.show(page)        # a tiles.Cards made with extra_css=files_page.CSS

The page is the path as chips (tap one to go there), the actions row for
the target (the previewed file, or the folder shown), then a grid of tiles:
icon, name, and what can be told without opening the file (a Python file's
first docstring line and def count, a folder's item count, size, age). The
previewed tile is edged white and carries ↗ to open it.

facts_for(entry) gives each tile's Facts, so the tool can cache them;
facts_for_entry is the uncached version. Items handed back:
('folder', path), ('file', path), ('open', path), ('act', action name).
tests/smoke_files_page.py checks it headless.
"""
import os
import re
import time
from collections import namedtuple

from editorkit import browse, files
from editorkit.web import cards


# --- Settings -------------------------------------------------------------

TILE_MIN_WIDTH = 130             # narrowest tile before the grid drops a column
MAX_TILES = 240                  # a huge folder shows this many, then says how many more
DOC_CHARACTERS = 90              # a docstring line is cut to this
READ_EXTENSIONS = ('.py', '.md', '.txt')   # files opened for their first line
SELECTED_COLOUR = '#FFFFFF'
FOLDER_COLOUR = '#F5B041'
COLOURS = {                      # tile edges, by extension
    '.py': '#27AE60',
    '.pyui': '#27AE60',
    '.md': '#5DADE2',
    '.txt': '#5DADE2',
    '.json': '#AF7AC5',
    '.html': '#E67E22',
    '.js': '#E67E22',
    '.css': '#E67E22',
    '.png': '#EC7063',
    '.jpg': '#EC7063',
    '.jpeg': '#EC7063',
    '.gif': '#EC7063',
}
HINT = 'Tap a file to preview it; tap it again (or ↗) to open it.'

# The actions row: (action, label), in order. The tool runs do_<action>.
ACTIONS = (
    ('rename', '✏️ Rename'),
    ('copy', '⧉ Copy'),
    ('move', '➜ Move'),
    ('delete', '🗑 Delete'),
    ('window', '📜 Window'),
    ('console', '📟 Console'),
)
FILE_ONLY_ACTIONS = ('window', 'console')
ARMED_LABEL = '🗑 Sure?'

CSS = """
.fx-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.fx-icon { font-size: 26px; line-height: 30px; }
.fx-meta { font: 11px -apple-system, sans-serif; opacity: 0.65; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fx-doc { font: 12px -apple-system, sans-serif; opacity: 0.85; margin-top: 4px;
    line-height: 1.3em; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden; }
"""


# --- Facts about a file -----------------------------------------------------

Facts = namedtuple('Facts', 'doc defs items size modified')
Facts.__new__.__defaults__ = ('', None, None, None, None)
Facts.__doc__ = """What a tile shows: doc (a first line), defs (Python files),
items (folders), size in bytes and modified time. None means unknown."""

DOCSTRING = re.compile(r'^[rRuU]{0,2}("""|\'\'\')(.*?)(?:\1|$)', re.S)
DEF_LINE = re.compile(r'^[ \t]*(?:async[ \t]+)?def[ \t]', re.M)


def first_docstring_line(text):
    """The first line of a module's docstring, or ''. Leading blank lines,
    comments and the shebang are skipped; anything else first means none."""
    lines = text.split('\n')
    start = 0
    while start < len(lines):
        stripped = lines[start].strip()
        if stripped and not stripped.startswith('#'):
            break
        start += 1
    match = DOCSTRING.match('\n'.join(lines[start:]).lstrip())
    if not match:
        return ''
    for line in match.group(2).split('\n'):
        if line.strip():
            return line.strip()
    return ''


def first_line(text):
    """The first line with words in it, without a Markdown heading's #s."""
    for line in text.split('\n'):
        words = line.strip().lstrip('#').strip()
        if words:
            return words
    return ''


def shorten(words, limit=DOC_CHARACTERS):
    return words if len(words) <= limit else words[:limit - 1].rstrip() + '…'


def facts_for_entry(entry):
    """The Facts for one browse.Entry, read from disk now (uncached)."""
    try:
        status = os.stat(entry.path)
    except OSError:
        return Facts()
    if entry.is_folder:
        return Facts(items=len(browse.list_folder(entry.path)), modified=status.st_mtime)
    doc, defs = '', None
    if entry.extension in READ_EXTENSIONS:
        text = files.read_text(entry.path)
        if text is not None:
            if entry.extension == '.py':
                doc = first_docstring_line(text)
                defs = len(DEF_LINE.findall(text))
            else:
                doc = first_line(text)
    return Facts(doc=shorten(doc), defs=defs, size=status.st_size, modified=status.st_mtime)


def size_words(size):
    if size < 1024:
        return '%d B' % size
    if size < 1024 * 1024:
        return '%.1f KB' % (size / 1024.0)
    return '%.1f MB' % (size / 1048576.0)


def age_words(seconds):
    """How long ago, shortest form: now, 5m, 3h, 2d, 6w, 1y."""
    seconds = max(0, seconds)
    if seconds < 60:
        return 'now'
    if seconds < 3600:
        return '%dm' % (seconds // 60)
    if seconds < 86400:
        return '%dh' % (seconds // 3600)
    if seconds < 86400 * 14:
        return '%dd' % (seconds // 86400)
    if seconds < 86400 * 365:
        return '%dw' % (seconds // (86400 * 7))
    return '%dy' % (seconds // (86400 * 365))


def meta_words(entry, facts, now):
    parts = []
    if entry.is_folder:
        if facts.items is not None:
            parts.append('%d item%s' % (facts.items, '' if facts.items == 1 else 's'))
    else:
        if facts.defs:
            parts.append('%d def%s' % (facts.defs, '' if facts.defs == 1 else 's'))
        if facts.size is not None:
            parts.append(size_words(facts.size))
    if facts.modified is not None:
        parts.append(age_words(now - facts.modified))
    return ' · '.join(parts)


# --- The page -------------------------------------------------------------

def same_path(first, second):
    return bool(first) and bool(second) and os.path.normpath(first) == os.path.normpath(second)


def crumbs(folder, root):
    """[(label, path)] from root down to folder. A folder outside root gets
    its parent (marked ⬆) and itself."""
    folder = os.path.normpath(folder)
    root = os.path.normpath(root)
    relative = os.path.relpath(folder, root)
    if relative.startswith('..'):
        parent = os.path.dirname(folder)
        return [('⬆ ' + (os.path.basename(parent) or parent), parent),
                (os.path.basename(folder) or folder, folder)]
    trail = [(os.path.basename(root) or root, root)]
    if relative == '.':
        return trail
    path = root
    for part in relative.split(os.sep):
        path = os.path.join(path, part)
        trail.append((part, path))
    return trail


def colour_for(entry):
    return FOLDER_COLOUR if entry.is_folder else COLOURS.get(entry.extension)


def tile_body(entry, facts, now):
    html = '<div class="fx-head"><span class="fx-icon">%s</span><span class="fx-meta">%s</span></div>' % (
        cards.escape(browse.icon(entry)), cards.escape(meta_words(entry, facts, now)))
    if facts.doc:
        html += '<div class="fx-doc">%s</div>' % cards.escape(facts.doc)
    return html


def tile(entry, facts, selected, now):
    chosen = same_path(selected, entry.path)
    kind = 'folder' if entry.is_folder else 'file'
    actions = [cards.Action('↗', ('open', entry.path))] if chosen else []
    return cards.Card(entry.name, item=(kind, entry.path), body=tile_body(entry, facts, now),
                      colour=SELECTED_COLOUR if chosen else colour_for(entry),
                      actions=actions)


def action_buttons(target_is_file, armed):
    buttons = []
    for name, label in ACTIONS:
        if name in FILE_ONLY_ACTIONS and not target_is_file:
            continue
        if name == 'delete':
            buttons.append(cards.Action(ARMED_LABEL if armed else label, ('act', name),
                                        armed=armed, look=None if armed else 'warn'))
        else:
            buttons.append(cards.Action(label, ('act', name)))
    return buttons


def folder_page(folder, root, entries, facts_for, selected=None, target=None,
                armed=False, now=None, message=None):
    """The whole Files page for folder. entries: browse.list_folder(folder).
    message: what the last action did (shown under the path).
    selected: the previewed file. target: what the actions work on (None
    hides them). armed: delete is waiting for its second tap."""
    now = time.time() if now is None else now
    page = cards.Page()
    trail = crumbs(folder, root)
    page.chips([cards.Chip(label, item=('folder', path), colour=FOLDER_COLOUR,
                           on=index == len(trail) - 1)
                for index, (label, path) in enumerate(trail)])
    if message:
        page.note(message)
    if target:
        page.note('Acting on: %s' % (os.path.basename(target) or target))
        page.buttons(action_buttons(os.path.isfile(target), armed))
    else:
        page.note(HINT)
    shown = entries[:MAX_TILES]
    if shown:
        page.grid([tile(entry, facts_for(entry), selected, now) for entry in shown],
                  min_width=TILE_MIN_WIDTH)
    else:
        page.note('Empty folder.')
    if len(entries) > MAX_TILES:
        page.note('… %d more not shown' % (len(entries) - MAX_TILES))
    return page


def folder_picker_page(folder, root, entries, facts_for, now=None, extra=()):
    """Choosing a folder (Search's scope): the path as chips (tap to go
    there), 'Search in' and Cancel, then the folders here as tiles (tap to
    go in). Files are left out. Items: ('folder', path), ('pick', folder),
    ('cancel', None). extra: actions put before 'Search in' (the hub's ⌂)."""
    now = time.time() if now is None else now
    page = cards.Page()
    trail = crumbs(folder, root)
    page.chips([cards.Chip(label, item=('folder', path), colour=FOLDER_COLOUR,
                           on=index == len(trail) - 1)
                for index, (label, path) in enumerate(trail)])
    name = os.path.basename(folder) or folder
    page.buttons(list(extra) + [cards.Action('🔎 Search in %s' % name, ('pick', folder), look='go'),
                  cards.Action('Cancel', ('cancel', None))])
    folders = [entry for entry in entries if entry.is_folder][:MAX_TILES]
    if folders:
        page.grid([tile(entry, facts_for(entry), None, now) for entry in folders],
                  min_width=TILE_MIN_WIDTH)
    else:
        page.note('No folders inside.')
    return page

"""Files: browse folders as a grid of tiles, preview files as script
windows, and rename, copy, move or delete.

A Pair: the folder's page of tiles (editorkit's card kit, built by
files_page) fills the space over the code, and the previewed file rides in
the dock as its keys: a script window (deck.scriptview), the deck's one
code viewer, with ▶ ✂️ ⚡ and line taps. Tapping another file swaps the
file in that same window. If the preview asks for its own keys (✂️) it
leaves Files and stays as a window of its own; the next file tapped gets a
new preview. The path shows as chips: tap one to go there. Tap a folder
tile to go in; tap a file tile to preview it; tap it again, or ↗, to open
it. ⌨ in the header brings the preview back. Pinch the tiles for more or
fewer columns (remembered).

The actions row works on the previewed file, or on the folder shown when
none is previewed; what an action did shows under the path. Delete takes
two taps and only moves things into Documents/_to_delete
(editorkit.fileops).

    from editorkit_toolbox import filebrowser
    filebrowser.open_files()
"""
import os
import time

import editorkit as ek
from editorkit import browse, fileops, layouts, tiles
from editorkit.web import tiles as web_tiles

from . import files_page


# --- Settings -------------------------------------------------------------

TITLE = 'Files'
EMOJI = '📁'
WINDOW_KEY = 'deck-files'
PREVIEW_KEY = 'deck-files-preview'   # gets -2, -3 … while an earlier preview lives on
FILL_ABOVE_PREVIEW = True    # the tiles fill the space above the preview
OPEN_ICON = '↗'
SEARCH_ICON = '🔎'           # opens Search, which is 🔎
CONFIRM_SECONDS = 3.0        # how long an armed delete waits for its second tap
START_ZOOM = 0.8             # the first size; a pinch is remembered after that
ZOOM_KEY = 'files'
DOCUMENTS = os.path.expanduser('~/Documents')
DONE = {
    'rename': 'Renamed to %s.',
    'copy': 'Copied as %s.',
    'move': 'Moved to %s.',
    'delete': 'Moved to %s. Empty it by hand.',
}

same_path = files_page.same_path


def shown_path(path):
    relative = os.path.relpath(path, DOCUMENTS)
    return os.path.basename(path) if relative.startswith('..') else relative


def is_up(window):
    return window is not None and window.is_up()


class FilesTool:

    def __init__(self, window):
        self.window = window
        self.opened = False
        self.folder = None           # the folder whose tiles show
        self.previewing = None       # path of the file in the preview
        self.preview = None          # the script window previewing, while it is Files' keys
        self.message = None          # what the last action did, under the path
        self.moving = None           # path waiting for Move's folder pick
        self.armed_until = 0.0       # an armed delete lasts until then
        self.facts_cache = {}        # path -> (modified time, Facts)
        self.opener = ek.Opener(window)

        # Paired with the preview's keys, so scrolling must not hide the keyboard.
        self.board = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                 zoom_key=ZOOM_KEY, dismiss_keyboard=False,
                                 extra_css=files_page.CSS)
        window.add_page(TITLE, self.board)
        self.prompt = layouts.prompt(window)
        self.mover = layouts.folder_picker(window, on_pick=self.move_into)

        self.pair = ek.Pair(window, self.make_preview, fill=FILL_ABOVE_PREVIEW)
        window.every(self.tick)
        window.add_button(OPEN_ICON, lambda _window: self.open_previewed(), name='open')
        window.add_button(SEARCH_ICON, lambda _window: self.open_search(), name='search')
        window.on('open', lambda _window: self.window_opened())

    def begin(self):
        if self.opened:
            return
        self.opened = True
        path = ek.current_file()
        self.show_folder(os.path.dirname(path) if path else DOCUMENTS)

    def window_opened(self):
        """First open: the open file's folder. Every open (back from the
        tray, too): the tiles are refreshed, and a preview comes back if a
        file was being previewed."""
        if self.opened:
            self.refresh()
        else:
            self.begin()
        if self.previewing and not is_up(self.pair.keys):
            self.window.when_still(lambda window: self.pair.summon_keys())

    # --- The page of tiles --------------------------------------------------

    def show_folder(self, folder):
        """Show folder's tiles. The preview stays chosen only if it is in there."""
        if self.previewing and not same_path(os.path.dirname(self.previewing), folder):
            self.previewing = None
        self.folder = folder
        self.refresh()

    def refresh(self):
        if self.folder is None:
            return
        self.board.show(files_page.folder_page(
            self.folder, DOCUMENTS, browse.list_folder(self.folder), self.facts,
            selected=self.previewing, target=self.target(), armed=self.armed(),
            now=time.time(), message=self.message))

    def facts(self, entry):
        """A tile's Facts, reread only when the file's modified time changes."""
        try:
            modified = os.stat(entry.path).st_mtime
        except OSError:
            return files_page.Facts()
        cached = self.facts_cache.get(entry.path)
        if cached is not None and cached[0] == modified:
            return cached[1]
        found = files_page.facts_for_entry(entry)
        self.facts_cache[entry.path] = (modified, found)
        return found

    def say(self, words):
        self.message = words
        self.refresh()

    def picked(self, item):
        kind, value = item
        if kind != 'act':
            self.message = None
        if item != ('act', 'delete'):
            self.disarm()
        if kind == 'folder':
            self.show_folder(value)
        elif kind == 'file':
            self.file_tapped(value)
        elif kind == 'open':
            self.opener.go(value)
        elif kind == 'act':
            self.act(value)

    # --- The preview: a script window in the dock ---------------------------

    def make_preview(self):
        """Pair's make_keys: a script window, home in the dock, showing the
        previewed file (scriptview imported here: it is a deck tool too)."""
        from . import scriptview
        preview = scriptview.preview_window(
            self.previewing or ek.current_file(), self.free_preview_key(),
            on_own_keys=self.preview_left)
        self.preview = preview
        return preview

    def free_preview_key(self):
        """PREVIEW_KEY, or the next numbered one if a preview that left Files
        still holds it (the same key would replace that window)."""
        from . import scriptview
        key, number = PREVIEW_KEY, 1
        while scriptview.live_window(key) is not None:
            number += 1
            key = '%s-%d' % (PREVIEW_KEY, number)
        return key

    def preview_left(self, window):
        """The preview asked for its own keys (✂️): it leaves Files as a
        window of its own; the next file tapped gets a new preview."""
        if window is self.pair.keys:
            self.pair.release_keys()
        if window is self.preview:
            self.preview = None

    def file_tapped(self, path):
        """First tap previews; a second tap on the same file opens it."""
        if same_path(self.previewing, path):
            self.opener.go(path)
        else:
            self.show_preview(path)

    def show_preview(self, path):
        """Preview path: swapped into the preview if it is up, else a
        preview comes up (when the tiles are open)."""
        self.previewing = path
        self.refresh()
        preview = self.preview
        if preview is not None and preview is self.pair.keys and preview.is_up():
            preview.script_tool.set_path(path)
        elif self.window.is_up():
            self.pair.summon_keys()

    def open_previewed(self):
        if self.previewing:
            self.opener.go(self.previewing)

    def open_search(self):
        """🔍: Search over the folder shown, field focused. The preview goes
        first, so the keyboard can come up for typing."""
        self.pair.put_keys_away()
        from . import hub
        hub.open_find(scope=self.folder or DOCUMENTS)

    # --- Actions ----------------------------------------------------------

    def target(self):
        """The previewed file, else the folder shown (never Documents itself)."""
        if self.previewing and os.path.exists(self.previewing):
            return self.previewing
        folder = self.folder
        if folder and not same_path(folder, DOCUMENTS):
            return folder
        return None

    def act(self, name):
        path = self.target()
        if path is None:
            self.say('Preview a file first, or open the folder to act on.')
            return
        getattr(self, 'do_' + name)(path)

    def do_window(self, path):
        if not os.path.isfile(path):
            self.say('Preview a file to open it as a window.')
            return
        from . import scriptview
        scriptview.open_script_window(path)

    def do_console(self, path):
        """📟 Console: the file as a preview card in the Console."""
        if not os.path.isfile(path):
            self.say('Preview a file to send it to the Console.')
            return
        from . import console
        console.show(path, title=os.path.basename(path))

    def do_rename(self, path):
        name = os.path.basename(path)
        self.prompt.ask('Rename %s' % name, name, on_answer=lambda answer: self.attempt(
            'rename', path, lambda: fileops.rename(path, answer)))

    def do_copy(self, path):
        self.attempt('copy', path, lambda: fileops.duplicate(path))

    def do_move(self, path):
        self.moving = path
        self.mover.open(DOCUMENTS, drill=True, root=DOCUMENTS,
                        lead=lambda folder: '➜  Move here (%s)' % shown_path(folder),
                        title='Move %s to…' % os.path.basename(path))

    def move_into(self, entry):
        path, self.moving = self.moving, None
        if path:
            self.attempt('move', path, lambda: fileops.move(path, entry.path))

    def armed(self):
        return time.time() < self.armed_until

    def do_delete(self, path):
        if self.armed():
            self.disarm()
            self.attempt('delete', path, lambda: fileops.trash(path, DOCUMENTS))
            return
        self.armed_until = time.time() + CONFIRM_SECONDS
        self.refresh()

    def disarm(self):
        if self.armed_until:
            self.armed_until = 0.0
            self.refresh()

    def tick(self, now):
        if self.armed_until and time.time() > self.armed_until:
            self.disarm()

    def attempt(self, kind, old, action):
        """Run one action; on success show where things are now and say
        what happened under the path."""
        try:
            new = action()
        except (OSError, ValueError) as error:
            self.say(str(error))
            return
        if kind in ('rename', 'move') and same_path(ek.current_file(), old):
            ek.open_file(new)
        if kind in ('delete', 'move') and same_path(self.previewing, old):
            self.pair.put_keys_away()
        self.message = DONE[kind] % shown_path(new)
        folder = self.folder
        if same_path(old, folder):
            # The action was on the folder being shown.
            self.previewing = None
            self.show_folder(os.path.dirname(old) if kind == 'delete'
                             else new if kind in ('rename', 'move') else folder)
        elif kind in ('rename', 'copy'):
            self.show_preview(new)
        else:
            self.previewing = None
            self.refresh()


def open_files():
    """Open Files over the code; the preview comes with the first file
    tapped. Returns the tool (its window is tool.window)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = FilesTool(window)
    window.show()
    return tool
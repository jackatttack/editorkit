"""folder_picker: a folder's subfolders, laid over the page as a sheet.

    +----------------------------+
    | header                     |
    | accessory (query, path)    |
    +----------------------------+
    | deck                  ⬆ ✕  |   sheet: title, up (drill mode), close
    | 🔎  Search in deck          |   lead row: the folder itself
    | 📁  deck                    |   Folders (compact): its subfolders
    | 📁  tools                   |
    +----------------------------+

Plain: a pick closes the sheet and calls on_pick(entry) with a
browse.Entry (the lead row gives the folder itself). Drill mode: a
subfolder opens in place, ⬆ goes back up (not above root), and only the
lead row picks. ✕ closes with no pick. lead is text, or a function of the
folder shown (drill mode's lead changes as you go).

Used by: Search (path taps), Files (Move).

    picker = layouts.folder_picker(window, on_pick=lambda entry: ...)
    picker.open(folder, lead='🔎  Search in deck')
    picker.open(documents, lead=lambda folder: 'Move here', drill=True, root=documents)
"""
import os

import ui

from .. import tiles
from ..tiles.base import PADDING, ROW_HEIGHT, make_button


# --- Settings -------------------------------------------------------------

TITLE_FONT = ('<system-bold>', 15)
CLOSE_ICON = '✕'
UP_ICON = '⬆'


def same_folder(first, second):
    return os.path.normpath(first) == os.path.normpath(second)


class FolderPicker(tiles.Tile):

    def __init__(self, window, on_pick=None):
        tiles.Tile.__init__(self, window)
        self.background_color = self.palette.panel        # opaque: a sheet
        self.on_pick = on_pick
        self.folder = None
        self.lead = None
        self.drill = False
        self.root = None

        self.title = ui.Label(font=TITLE_FONT)
        self.title.text_color = self.palette.text
        self.title.touch_enabled = False
        self.add_subview(self.title)

        self.close_button = make_button(CLOSE_ICON, lambda sender: self.close(),
                                        self.palette)
        self.add_subview(self.close_button)
        self.up_button = make_button(UP_ICON, lambda sender: self.go_up(), self.palette)
        self.up_button.hidden = True
        self.add_subview(self.up_button)

        self.folders = tiles.Folders(window, on_pick=self.picked)
        self.add_subview(self.folders)

    def open(self, folder, lead=None, title=None, drill=False, root=None):
        self.lead = lead
        self.drill = drill
        self.root = root
        self.show_folder(folder, title)
        self.window.show_sheet(self)

    def show_folder(self, folder, title=None):
        self.folder = folder
        lead = self.lead(folder) if callable(self.lead) else self.lead
        self.title.text = title or os.path.basename(folder) or folder
        self.folders.show(folder, lead=lead, folders_only=True)
        self.up_button.hidden = not (self.drill and self.root
                                     and not same_folder(folder, self.root))
        self.layout()

    def go_up(self):
        self.show_folder(os.path.dirname(os.path.normpath(self.folder)))

    def close(self):
        self.window.close_sheet()

    def picked(self, entry):
        if self.drill and not same_folder(entry.path, self.folder):
            self.show_folder(entry.path)
            return
        self.close()
        if self.on_pick:
            self.on_pick(entry)

    def layout(self):
        top = PADDING
        self.close_button.frame = (self.width - PADDING - ROW_HEIGHT, top,
                                   ROW_HEIGHT, ROW_HEIGHT)
        self.up_button.frame = (self.close_button.x - PADDING - ROW_HEIGHT, top,
                                ROW_HEIGHT, ROW_HEIGHT)
        title_end = self.close_button.x if self.up_button.hidden else self.up_button.x
        self.title.frame = (PADDING * 2, top, max(0, title_end - PADDING * 3), ROW_HEIGHT)
        below = top + ROW_HEIGHT + PADDING
        self.folders.frame = (0, below, self.width, max(0, self.height - below))


def folder_picker(window, on_pick=None):
    """A FolderPicker for window: open(folder, lead=...) lays it over the page."""
    return FolderPicker(window, on_pick)
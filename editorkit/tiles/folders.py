"""Folders: what is in a folder, as rows; a tap picks one.

    folders = tiles.Folders(window, on_pick=picked)     # picked(entry)
    folders.show(folder, lead='🔎  Search here', folders_only=True)

Compact for now: an icon and a name per row, in browse.list_folder's order
(folders first). A lead row, when given, stands for the folder itself, so
'this one' sits above what is inside it. Planned: a full size with details
and a preview (docs/TILES.txt).
"""
import ui

from .. import browse
from ..windows import look
from .base import Tile


# --- Settings -------------------------------------------------------------

ROW_HEIGHT = 40
ROW_FONT = ('<system>', 15)
LEAD_FONT = ('<system-bold>', 15)
MESSAGE_FONT = ('<system>', 14)
EMPTY_TEXT = 'Nothing inside.'
NO_FOLDERS_TEXT = 'No folders inside.'


class Folders(Tile):

    def __init__(self, window, on_pick=None):
        Tile.__init__(self, window)
        self.on_pick = on_pick
        self.rows = []               # [(text, entry, is_lead)]

        self.table = ui.TableView()
        self.table.background_color = look.CLEAR
        self.table.separator_color = self.palette.edge
        self.table.row_height = ROW_HEIGHT
        self.table.data_source = self
        self.table.delegate = self
        self.add_subview(self.table)

        self.message = ui.Label(font=MESSAGE_FONT, alignment=ui.ALIGN_CENTER)
        self.message.text_color = self.palette.dim
        self.message.touch_enabled = False
        self.message.hidden = True
        self.add_subview(self.message)

    def show(self, folder, lead=None, folders_only=False):
        """List folder; lead (text) adds a first row that picks folder itself."""
        entries = browse.list_folder(folder, folders_only=folders_only)
        rows = []
        if lead:
            rows.append((lead, browse.entry_for(folder), True))
        for entry in entries:
            rows.append(('%s  %s' % (browse.icon(entry), entry.name), entry, False))
        self.rows = rows
        self.message.text = '' if entries else (NO_FOLDERS_TEXT if folders_only else EMPTY_TEXT)
        self.message.hidden = bool(entries)
        self.table.reload_data()
        self.layout()

    def layout(self):
        self.table.frame = (0, 0, self.width, self.height)
        leads = sum(1 for row in self.rows if row[2])
        self.message.frame = (12, leads * ROW_HEIGHT + 8, max(0, self.width - 24), ROW_HEIGHT)

    # --- Table data source and delegate -----------------------------------

    def tableview_number_of_sections(self, tableview):
        return 1

    def tableview_number_of_rows(self, tableview, section):
        return len(self.rows)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell()
        cell.background_color = look.CLEAR
        if row >= len(self.rows):
            return cell
        text, _entry, is_lead = self.rows[row]
        cell.text_label.text = text
        cell.text_label.font = LEAD_FONT if is_lead else ROW_FONT
        cell.text_label.text_color = self.palette.accent if is_lead else self.palette.text
        cell.selected_background_view = ui.View(background_color=self.palette.edge)
        return cell

    def tableview_did_select(self, tableview, section, row):
        if row < len(self.rows) and self.on_pick:
            self.on_pick(self.rows[row][1])
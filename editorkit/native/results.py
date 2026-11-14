"""Results: a scrolling list of headings and rows, filled as results arrive.

    results = tiles.Results(window, on_pick=opened)   # a tap: opened(item)
    results.clear()
    results.heading('deck/find.py')
    results.row(12, 'def search(self):', item=hit)
    results.row(13, 'return hits', item=near, dim=True)   # a quieter row
    results.say('No matches')                          # a centred message

A row with an item can be tapped; one without (a ⋯ gap) cannot. Add rows
on the main thread (a tile's clock is the place). The list reloads at most
once per tick, not once per row, so streaming stays cheap.
"""
import ui

from ..windows import look
from .base import Tile


# --- Settings -------------------------------------------------------------

ROW_HEIGHT = 30
TEXT_LIMIT = 160            # characters of a row's text kept
ROW_FONT = ('Menlo', 13)
HEADING_FONT = ('<system-bold>', 13)
MESSAGE_FONT = ('<system>', 14)


class Results(Tile):

    def __init__(self, window, on_pick=None):
        Tile.__init__(self, window)
        self.on_pick = on_pick
        self.rows = []              # [{'kind', 'label', 'text', 'item', 'dim'}]
        self.stale = False          # rows changed since the table last reloaded

        self.table = ui.TableView()
        self.table.background_color = look.CLEAR
        self.table.separator_color = self.palette.edge
        self.table.row_height = ROW_HEIGHT
        self.table.data_source = self
        self.table.delegate = self
        self.add_subview(self.table)

        self.message = ui.Label(font=MESSAGE_FONT, alignment=ui.ALIGN_CENTER)
        self.message.number_of_lines = 0
        self.message.text_color = self.palette.dim
        self.message.touch_enabled = False
        self.message.hidden = True
        self.add_subview(self.message)

    # --- Filling it -------------------------------------------------------

    def clear(self):
        """Empty the list now (not on the next tick), so the table never asks
        for a row that has gone."""
        self.rows = []
        self.say('')
        self.refresh()

    def heading(self, text):
        self.rows.append({'kind': 'heading', 'label': '', 'text': text,
                          'item': None, 'dim': False})
        self.stale = True

    def row(self, label, text, item=None, dim=False):
        self.rows.append({'kind': 'row', 'label': str(label),
                          'text': text.strip()[:TEXT_LIMIT], 'item': item, 'dim': dim})
        self.stale = True

    def say(self, words):
        self.message.text = words or ''
        self.message.hidden = not words

    def refresh(self):
        self.stale = False
        self.table.reload_data()

    def tick(self, now):
        Tile.tick(self, now)            # the clock first: it may add rows
        if self.stale:
            self.refresh()

    # --- Drawing ----------------------------------------------------------

    def layout(self):
        self.table.frame = (0, 0, self.width, self.height)
        self.message.frame = (12, 0, max(0, self.width - 24), self.height)

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
        entry = self.rows[row]
        label = cell.text_label
        if entry['kind'] == 'heading':
            label.text = entry['text']
            label.font = HEADING_FONT
            label.text_color = self.palette.accent
        else:
            label.text = '%5s  %s' % (entry['label'], entry['text'])
            label.font = ROW_FONT
            label.text_color = self.palette.dim if entry['dim'] else self.palette.text
        cell.selectable = entry['item'] is not None
        if cell.selectable:
            cell.selected_background_view = ui.View(background_color=self.palette.edge)
        return cell

    def tableview_did_select(self, tableview, section, row):
        if row >= len(self.rows):
            return
        entry = self.rows[row]
        if entry['item'] is not None and self.on_pick:
            self.on_pick(entry['item'])
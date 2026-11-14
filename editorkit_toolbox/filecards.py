"""File cards: one picture of a file wherever Toolbox shows one.

    card = filecards.file_card(path, item, view_item, where='projects/editorkit')
    page.grid([card, ...], min_width=filecards.CARD_WIDTH)

A card shows the file's name, edged in Files' colour for its type, the
folder it lives in, and its first lines, syntax-coloured. A tap on the card
gives item; 📜 gives view_item (leave it None for no 📜). Search's Files
named, the hub's Find (Recent, Files named) and the Tools tab's Recent
scripts all use it, so a file looks the same everywhere. Pages that show
cards need CSS (the Cards tile's card kit CSS plus this).

Pure (no ui), so it builds on a scan thread.
"""
import os

from editorkit import browse, files
from editorkit.web import cards, codeview

from . import files_page


# --- Settings -------------------------------------------------------------

PREVIEW_LINES = 6            # first lines shown on a card
CARD_WIDTH = 220             # narrowest a file card gets before the grid drops a column
PREVIEW_EXTENSIONS = ('.py', '.txt', '.md', '.json', '.pyui', '.js', '.html', '.css')
WINDOW_ICON = '📜'           # a card's action: the file in a script window
HERE = 'here'                # where, for a file in the folder being shown

CSS = files_page.CSS + """
.fx-where { font: 11px -apple-system, sans-serif; opacity: 0.6; margin-bottom: 4px; }
"""


def file_card(path, item, view_item=None, where=None, preview_lines=PREVIEW_LINES):
    """path as a card. where is the folder shown under the name ('.' or
    empty: HERE)."""
    folder = HERE if where in (None, '', '.') else where
    body = '<div class="fx-where">%s</div>' % codeview.escape('📁 ' + folder)
    text = files.read_text(path) if path.lower().endswith(PREVIEW_EXTENSIONS) else None
    if text and preview_lines:
        body += cards.code(text, lines=preview_lines, python=path.endswith('.py'))
    actions = [cards.Action(WINDOW_ICON, view_item)] if view_item is not None else []
    return cards.Card(os.path.basename(path), item=item, body=body,
                      colour=files_page.colour_for(browse.entry_for(path)), actions=actions)
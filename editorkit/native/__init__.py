"""editorkit.native: native ui pieces for tools over the editor.

Every piece is a ui.View that knows its window and takes its colours from
the editor's theme. For pages of cards, code and feeds, use the web tiles
(editorkit.web.tiles) instead: they are the default for new tool surfaces.
Keep native pieces for text entry and fast motion.

    from editorkit import native
    field = native.Field(window, 'Search', on_change=typed)
    path = native.Path(window, on_pick=go)       # Documents › projects › …
    controls = native.Controls(window)           # second header, ? built in

Catalogue (each piece, and the layouts that use it): docs/TILES.txt.
"""
from .bar import Bar
from .base import Tile, palette_for
from .card import Card
from .column import Column
from .controls import Controls
from .field import Field
from .folders import Folders
from .grid import Grid
from .keypad import Keypad
from .path import Path
from .results import Results
from .split import Split
from .textbox import TextBox
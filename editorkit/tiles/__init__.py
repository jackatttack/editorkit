"""editorkit tiles: reusable pieces for building tools over the editor.

Every tile is a ui.View that knows its window and takes its colours from
the editor's theme. Catalogue (each tile, and the layouts that use it):
docs/TILES.txt.

    from editorkit import tiles
    field = tiles.Field(window, 'Search', on_change=typed)
    path = tiles.Path(window, on_pick=go)       # Documents › projects › …
    controls = tiles.Controls(window)           # second header, ? built in

The web tiles (Code, Cards, Feed, Tape) live in editorkit.web.tiles since
2026-11-12. tiles.Code and the others still work: they are fetched from
there on first use, so loading the core never imports the web package.
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


# Moved to editorkit.web.tiles (the web fence, 2026-11-12).
WEB_TILES = ('Code', 'Cards', 'Feed', 'Tape')


def __getattr__(name):
    if name in WEB_TILES:
        from ..web import tiles as web_tiles
        return getattr(web_tiles, name)
    raise AttributeError("module 'editorkit.tiles' has no attribute %r" % name)
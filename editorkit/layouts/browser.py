"""browser: a folder's contents above, an optional preview below.

    +----------------------------+
    | header (⋯ with controls)   |
    | [✏️] [⧉] [➜] [🗑]      [?] |   accessory: Controls (optional, ⋯)
    | Documents › projects › …   |   accessory: Path (tap: go up)
    +----------------------------+
    | 📁  deck                    |   page: Split
    | 🐍  launch_deck.py          |     top: Folders (folders and files)
    |----------------------------|
    | launch_deck.py             |     bottom: preview (a view you pass in)
    |    1  import editorkit…    |
    +----------------------------+

Folders navigate by themselves: a folder row goes in, the path goes up.
A file row calls on_file(entry).

    preview = web.tiles.Code(window, on_go=opened)
    view = layouts.browser(window, on_file=tapped, preview=preview, controls=True)
    view.show(folder); view.controls.add(...)

preview is any view, usually a web tile. This core layout never builds web
pieces itself (the web fence, 2026-11-12). With no preview the page is the
Folders alone. Nothing in Toolbox uses this layout today (Files shows
folders and a Pair).
"""
from .. import tiles
from .accessory import Accessory


class Browser:

    def __init__(self, window, on_file, page, ratio, controls, help_intro, preview=None):
        self.window = window
        self.on_file = on_file
        self.folder = None
        self.path = tiles.Path(window, on_pick=self.show)
        self.folders = tiles.Folders(window, on_pick=self.picked)
        self.code = preview          # the name kept from when the layout built it
        self.split = (tiles.Split(window, self.folders, preview, ratio=ratio)
                      if preview is not None else None)
        self.controls = tiles.Controls(window, intro=help_intro) if controls else None
        self.accessory = Accessory(window, [self.path], self.controls)
        window.add_page(page, self.split if self.split is not None else self.folders)

    def show(self, folder):
        self.folder = folder
        self.path.show(folder)
        self.folders.show(folder)

    def picked(self, entry):
        if entry.is_folder:
            self.show(entry.path)
        elif self.on_file:
            self.on_file(entry)


def browser(window, on_file=None, on_go=None, page='Files', ratio=0.45,
            controls=False, help_intro='', preview=None):
    """Path (and Controls behind ⋯ when controls=True) in the accessory;
    Folders above preview (a view) as the page, or Folders alone when
    preview is None or False. on_go is unused now (the preview handles its
    own taps) and kept so older calls still work."""
    if preview is True:
        raise ValueError('browser() no longer builds its preview: pass the view, '
                         'for example web.tiles.Code(window, on_go=...)')
    if preview is False:
        preview = None
    return Browser(window, on_file, page, ratio, controls, help_intro, preview)
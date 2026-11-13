"""editorkit layouts: named arrangements of tiles in a window.

One file per layout, named by its shape, with a sketch in its docstring.
Catalogue: docs/TILES.txt.
"""
from .accessory import Accessory, controls
from .browser import Browser, browser
from .prompt import Prompt, prompt
from .folder_picker import FolderPicker, folder_picker
from .query_list import QueryList, query_list
"""editorkit.web.tiles: tiles that show a web page.

    Card     a message as the window's sheet (as tiles.Card); a tap closes it
    Code     a page shell showing sections; taps come back as your items
    Cards    Code with the card kit's look and the page-owned pinch
    Feed     a Code of entries as cards (the Console)
    Keypad   pages of keys (as tiles.Keypad), for the keyboard's place
    Tape     the calculator tape
"""
from .card import Card
from .cards import Cards
from .code import Code
from .feed import Feed
from .keypad import Keypad
from .tape import Tape
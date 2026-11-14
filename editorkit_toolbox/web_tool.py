"""🌐 Web: a browser over your code.

The field at the top takes an address (pypi.org, https://...) or words to
search; Return goes there, and the field follows the page as you browse.
The header has ◀ back (or swipe from the left edge), ↻ reload, ↗ Safari
and ⧉ copy link; the window's title is the page's. The page is
editorkit.web.tiles.Browser (WKWebView).

    from editorkit_toolbox import web_tool
    web_tool.open_web()                       # the start page
    web_tool.open_web('https://pypi.org')     # somewhere else
"""
import urllib.parse

import ui

import editorkit as ek
from editorkit.native.base import palette_for, style_field
from editorkit.native.field import tint_placeholder
from editorkit.web import tiles as web_tiles
from editorkit.web.tiles import browser as browser_tile


# --- Settings -------------------------------------------------------------------

TITLE = 'Web'
EMOJI = '🌐'
WINDOW_KEY = 'deck-web'
START_PAGE = 'https://docs.python.org/3/'
SEARCH_PAGE = 'https://duckduckgo.com/?q=%s'     # words that are not an address
PLACEHOLDER = 'Address or search'
BAR_HEIGHT = 46


# --- Pure -------------------------------------------------------------------------

def address_for(text):
    """Where the field's text goes: an address as it is (https:// added when
    missing), anything else as a search. None for nothing."""
    words = (text or '').strip()
    if not words:
        return None
    if '://' in words:
        return words
    if ' ' not in words and '.' in words.strip('.'):
        return 'https://' + words
    return SEARCH_PAGE % urllib.parse.quote_plus(words)


# --- The address bar ----------------------------------------------------------

class AddressBar(ui.View):
    """The window's accessory: one field. Return hands its text to on_go."""

    def __init__(self, window, on_go):
        self.window = window
        self.on_go = on_go
        self.editing = False
        self.field = ui.TextField(placeholder=PLACEHOLDER)
        self.field.keyboard_type = ui.KEYBOARD_URL
        self.field.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.field.clear_button_mode = 'while_editing'
        self.field.delegate = self
        self.add_subview(self.field)
        self.restyle()

    def restyle(self):
        palette = palette_for(self.window)
        style_field(self.field, palette, monospace=False)
        tint_placeholder(self.field, palette.dim)

    def layout(self):
        self.field.frame = (8, 5, self.width - 16, self.height - 10)

    def show_address(self, url):
        """Follow the page, but never while the person is typing."""
        if not self.editing and url:
            self.field.text = url

    # ui.TextField delegate
    def textfield_did_begin_editing(self, field):
        self.editing = True

    def textfield_did_end_editing(self, field):
        self.editing = False

    def textfield_should_return(self, field):
        field.end_editing()
        self.on_go(field.text)
        return True


# --- The tool ---------------------------------------------------------------------

class WebTool:

    def __init__(self, window, url):
        self.window = window
        self.bar = AddressBar(window, self.go)
        self.browser = web_tiles.Browser(window, url, on_change=self.changed)
        window.add_page(TITLE, self.browser)
        window.set_accessory(self.bar, BAR_HEIGHT)
        window.add_button(browser_tile.BACK_ICON, lambda *_args: self.browser.back(), 'back')
        window.add_button(browser_tile.RELOAD_ICON, lambda *_args: self.browser.reload(), 'reload')
        window.add_button(browser_tile.SAFARI_ICON, lambda *_args: self.browser.open_in_safari(),
                          'safari')
        window.add_button(browser_tile.COPY_ICON, lambda *_args: self.browser.copy_link(), 'copy')

    def go(self, text):
        url = address_for(text)
        if url:
            self.browser.load(url)

    def changed(self, browser):
        self.window.set_title(browser_tile.header_title(browser.title, browser.url,
                                                        browser.loading))
        self.bar.show_address(browser.url)


def open_web(url=None):
    """Open Web over the code (a new one replaces any other). Returns the tool."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = WebTool(window, url or START_PAGE)
    window.web_tool = tool
    window.show()
    return tool
"""Browser: a real web page in a window, on WKWebView (the modern engine).

    from editorkit.web import tiles
    window = tiles.browse('https://pypi.org/project/requests/', title='requests')
    browser = tiles.Browser(window, url)          # or the tile alone, as any page

browse() opens a window with ◀ back, ↻ reload, ↗ Safari and ⧉ copy link in
its header; the window's title follows the page's (⏳ while it loads). The
same key reuses the window. In the page: links stay in it, swipe from the
left edge goes back, pinch zooms (it is the site's page, not ours).

Why WKWebView rather than Pythonista's ui.WebView (an old UIWebView): in the
browser lab (labs/probe_browser.py, 2026-11-14) it loaded GitHub in 0.9 s
against 3.4 s, and it reports its title, address and progress, read here on
the window's clock. Every call to it runs on the main thread.
"""
import ctypes
import webbrowser

from objc_util import CGPoint, CGRect, CGSize, ObjCClass, ObjCInstance, nsurl, on_main_thread

from ... import clip
from ...native.base import Tile


# --- Settings -------------------------------------------------------------------

DEFAULT_TITLE = 'Web'
DEFAULT_KEY = 'editorkit-browser'
EMOJI = '🌐'
BACK_ICON = '◀'
RELOAD_ICON = '↻'
SAFARI_ICON = '↗'
COPY_ICON = '⧉'
LOADING_MARK = '⏳ '
TITLE_LIMIT = 40                 # characters of a page title in the window header
AUTORESIZE_WIDTH_HEIGHT = 18     # UIViewAutoresizingFlexibleWidth | FlexibleHeight


# --- Pure -------------------------------------------------------------------------

def host_of(url):
    """'https://pypi.org/project/x/' -> 'pypi.org'."""
    return (url or '').split('://', 1)[-1].split('/', 1)[0]


def header_title(title, url, loading):
    """What the window header says: the page's title (or its host before it
    has one), cut to TITLE_LIMIT, with ⏳ while loading."""
    words = (title or '').strip() or host_of(url) or DEFAULT_TITLE
    if len(words) > TITLE_LIMIT:
        words = words[:TITLE_LIMIT - 1].rstrip() + '…'
    return (LOADING_MARK if loading else '') + words


# --- The tile ---------------------------------------------------------------------

def web_view_class():
    try:
        return ObjCClass('WKWebView')
    except Exception:
        ctypes.cdll.LoadLibrary('/System/Library/Frameworks/WebKit.framework/WebKit')
        return ObjCClass('WKWebView')


class Browser(Tile):
    """A WKWebView as a window page. on_change(browser) runs whenever its
    address, title or loading state changes (browse() uses it for the title)."""

    def __init__(self, window, url=None, on_change=None):
        Tile.__init__(self, window)
        self.on_change = on_change
        self.wk = None
        self.state = None
        self.make()
        self.every(self.check)
        if url:
            self.load(url)

    @on_main_thread
    def make(self):
        config = ObjCClass('WKWebViewConfiguration').new()
        self.wk = web_view_class().alloc().initWithFrame_configuration_(
            CGRect(CGPoint(0, 0), CGSize(100, 100)), config)
        self.wk.setAllowsBackForwardNavigationGestures_(True)
        self.wk.setAutoresizingMask_(AUTORESIZE_WIDTH_HEIGHT)
        self.wk.setOpaque_(False)            # no black backing while it resizes
        self.wk.setBackgroundColor_(ObjCClass('UIColor').clearColor())
        ObjCInstance(self).addSubview_(self.wk)

    def layout(self):
        self.fit()

    @on_main_thread
    def fit(self):
        if self.wk is not None:
            self.wk.setFrame_(CGRect(CGPoint(0, 0), CGSize(self.width, self.height)))

    # --- Going places ---------------------------------------------------------

    @on_main_thread
    def load(self, url):
        self.wk.loadRequest_(ObjCClass('NSURLRequest').requestWithURL_(nsurl(url)))

    @on_main_thread
    def back(self):
        if self.wk.canGoBack():
            self.wk.goBack()

    @on_main_thread
    def reload(self):
        self.wk.reload()

    def open_in_safari(self):
        if self.url:
            webbrowser.open('safari-' + self.url)

    def copy_link(self):
        if self.url:
            clip.set_text(self.url)

    # --- What it shows ----------------------------------------------------------

    @property
    def url(self):
        address = self.wk.URL() if self.wk is not None else None
        return str(address.absoluteString()) if address is not None else ''

    @property
    def title(self):
        return str(self.wk.title() or '') if self.wk is not None else ''

    @property
    def loading(self):
        return bool(self.wk.isLoading()) if self.wk is not None else False

    def check(self, now):
        """On the window's clock: tell on_change when anything shown changed."""
        state = (self.url, self.title, self.loading)
        if state != self.state:
            self.state = state
            if self.on_change is not None:
                self.on_change(self)

    def restyle(self):
        """A site keeps its own colours when the theme changes."""


def browse(url, title=DEFAULT_TITLE, key=DEFAULT_KEY, owner=None, **options):
    """A window showing url: ◀ ↻ ↗ ⧉ in its header, the page's title as its
    own. owner makes it one of an app's pieces (Packages' PyPI pages). Takes
    everything ek.Window does. Returns the window (window.browser is the tile)."""
    import editorkit as ek
    window = ek.Window(title, emoji=EMOJI, key=key, owner=owner, **options)

    def changed(browser):
        window.set_title(header_title(browser.title, browser.url, browser.loading))

    browser = Browser(window, url, on_change=changed)
    window.browser = browser
    window.add_page('Page', browser)
    window.add_button(BACK_ICON, lambda *_args: browser.back(), 'back')
    window.add_button(RELOAD_ICON, lambda *_args: browser.reload(), 'reload')
    window.add_button(SAFARI_ICON, lambda *_args: browser.open_in_safari(), 'safari')
    window.add_button(COPY_ICON, lambda *_args: browser.copy_link(), 'copy')
    window.show()
    return window
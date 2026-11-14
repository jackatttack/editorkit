"""Code: code shown as HTML in a WebView, in editorkit.codeview's look.

    code = tiles.Code(window, on_go=opened, on_scroll=dragged)
    code.set_html(codeview.file_html('a.py', text, {12: [(4, 9)]}, 2))
    code.add_html(more)                # appended: for streaming sections
    code.say('No matches')

Sections (codeview.file_section, preview_section, rows_section) carry
items: code.set_section(section) or add_section(section), and on_pick(item)
gets the tapped row's or match's own object back; code.set_current(item)
rings it. Plain HTML still works:

on_go(payload) gets a tapped row's data-go string; on_scroll() runs once
per drag (Search puts the keyboard away with it). Both are called from the
window's clock, on the main thread, never from inside the WebView's own
callback. Scripts sent before the page has loaded wait for it.
"""
import json
import time
import traceback

import ui

from .. import codeview
from ... import trace
from ...native.base import Tile

KEYBOARD_DISMISS_ON_DRAG = 1     # UIScrollViewKeyboardDismissModeOnDrag

# Pythonista's ui.WebView is the old UIWebView (SUIWebView > UIWebView), not
# a WKWebView. A wrapping page (codeview.WRAP_CSS) drew clipped after the
# window was dragged small and back, worse after each drag, while every
# frame and the page's own width were right; no repaint, relayout, zoom or
# DOM rebuild fixed it, but a fresh web view always draws right (console,
# 2026-11-10). With fresh_on_grow, once a resize has been still for
# SETTLE_DELAY and the tile is bigger than its smallest size since the web
# view was built, a fresh one replaces it, showing the same sections, ring
# and scroll. Pages as wide as their content (Search) never clipped.
SETTLE_DELAY = 0.25
DOCK_REFOCUS_SECONDS = 1.0       # after a tap in the dock, keep handing focus back this long


# Building the web view and reaching into its UIKit views must happen on
# the main thread: a script run by hand (launch_deck.py building the hub's
# Cards page) is not, and raw objc view changes off it crash Pythonista
# with no traceback (2026-11-11). on_main_thread calls through when already
# there.
from objc_util import on_main_thread


# --- Pages that cannot take focus (in the keyboard's place) -----------------
# A UIWebView's tap hands first responder to its UIWebBrowserView a moment
# after the tap (it waits out a double tap). In the keyboard's place that
# swaps our window for the system keyboard. The browser view of a docked
# tile gets a subclass whose canBecomeFirstResponder says no: one view at a
# time (object_setClass), no global patch. Taps, links and scrolling come
# from WebKit's recognisers, not from focus, so they keep working.

NO_FOCUS_PREFIX = 'EKNoFocus'


def no_focus_class(base_name):
    """A subclass of base_name that refuses focus (made once per app run)."""
    import ctypes
    from objc_util import ObjCClass, create_objc_class
    name = NO_FOCUS_PREFIX + base_name
    try:
        return ObjCClass(name)
    except Exception:
        pass

    def canBecomeFirstResponder(_self, _cmd):
        return False
    canBecomeFirstResponder.restype = ctypes.c_bool
    canBecomeFirstResponder.argtypes = []
    return create_objc_class(name, ObjCClass(base_name), methods=[canBecomeFirstResponder])


def keep_from_focus(web):
    """Make web's browser view refuse focus. True once done (or already)."""
    import ctypes
    from objc_util import c
    views = [web.objc_instance]
    while views:
        view = views.pop()
        name = str(view.className())
        if name.startswith(NO_FOCUS_PREFIX):
            return True
        if 'BrowserView' in name:
            target = no_focus_class(name)
            c.object_setClass.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            c.object_setClass.restype = ctypes.c_void_p
            c.object_setClass(view.ptr, target.ptr)
            if view.isFirstResponder():
                view.resignFirstResponder()
            return True
        views.extend(view.subviews())
    return False
class Code(Tile):

    def __init__(self, window, on_go=None, on_scroll=None, extra_css='',
                 dismiss_keyboard=True, on_pick=None, fresh_on_grow=False):
        Tile.__init__(self, window)
        self.on_go = on_go
        self.on_pick = on_pick
        self.items = {}              # go id -> item, for the sections showing
        self.on_scroll = on_scroll
        # Dragging the page hides the keyboard (Search, Files). Off for views
        # paired with keys in the keyboard's place (Tape), where hiding it
        # would put the keys away.
        self.dismiss_keyboard = dismiss_keyboard
        self.extra_css = extra_css
        self.fresh_on_grow = fresh_on_grow
        self.wk = None               # the WKWebView, for scripts that never wait
        self.ready = False
        self.waiting = []            # scripts sent before the page loaded
        self.events = []             # ('go', payload) or ('scroll', None)
        self.shown_html = []         # what the page shows since set_html (for a rebuild)
        self.current_go = None       # the ringed row's go id (for a rebuild)
        self.smallest = None         # (w, h): smallest size since the web view was built
        self.settle_due = None       # when a resize counts as finished (time)
        self.old_web = None          # the web view being replaced, until the new one loads
        # Tap breadcrumbs, read by tools/probe_dead_taps.py (dead taps, 2026-11-11).
        self.link_count = 0          # links the page delivered to Python
        self.last_link = None        # (time, link) of the last one
        self.pick_count = 0          # handlers run for 'go' links
        self.rebuild_count = 0       # fresh web views built (fresh_on_grow)
        self.dock_refocus_until = 0.0   # after a tap in the dock: keep focus on the text view until then
        self.last_rebuild = None     # (time, window place) of the last one
        self.last_error = ''         # the last line of a handler's traceback
        self.web = self.make_web()
        self.drag_dismisses = self.dismiss_keyboard_on_drag()

    @on_main_thread
    def make_web(self):
        """A web view filling the tile, loading the page shell."""
        self.focus_locked = False    # its browser view refuses focus (set once docked)
        web = ui.WebView()
        web.background_color = self.palette.panel
        web.delegate = self
        web.frame = (0, 0, self.width, self.height)
        self.add_subview(web)
        web.load_html(codeview.page_html(self.palette, extra_css=self.extra_css))
        return web

    # --- Showing ----------------------------------------------------------

    def set_html(self, html):
        self.items = {}              # plain HTML: nothing left to pick
        self.shown_html = [html]
        self.current_go = None
        self.run('setResults(%s)' % json.dumps(html))

    def add_html(self, html):
        if html:
            self.shown_html.append(html)
            self.run('addResults(%s)' % json.dumps(html))

    # --- Sections with items ------------------------------------

    def set_section(self, section):
        """Show one (html, items) section, replacing everything."""
        html, items = section
        self.set_html(html)
        self.items = dict(items)

    def add_section(self, section):
        """Append an (html, items) section (streaming results)."""
        html, items = section
        self.items.update(items)
        self.add_html(html)

    def set_current(self, item):
        """Ring item (a match) or tint its row, and scroll it into view.
        False if no showing section holds it."""
        for go, known in self.items.items():
            if known == item:
                self.current_go = go
                self.run('setCurrentGo(%s)' % json.dumps(go))
                return True
        return False

    def say(self, words):
        self.set_html(codeview.message_html(words) if words else '')

    def run(self, script):
        if self.ready:
            self.run_now(script)
        else:
            self.waiting.append(script)

    def run_now(self, script):
        """Hand script to the page. With a WKWebView this does not wait
        (evaluateJavaScript with no completion). ui.WebView.eval_js waits for
        the page, and waiting on the main thread while the page asks the
        main thread about a link can freeze Pythonista."""
        trace.note('code run', script[:40])
        if self.wk is not None:
            from objc_util import ns
            self.wk.evaluateJavaScript_completionHandler_(ns(script), None)
        else:
            self.web.eval_js(script)
        trace.note('code ran')

    def layout(self):
        for web in (self.web, self.old_web):
            if web is not None:
                web.frame = (0, 0, self.width, self.height)
        if not self.fresh_on_grow or self.width < 1 or self.height < 1:
            return
        if self.smallest is None:
            self.smallest = (self.width, self.height)
        else:
            self.smallest = (min(self.smallest[0], self.width),
                             min(self.smallest[1], self.height))
        # Each layout moves this on, so it fires once the resize has settled.
        self.settle_due = time.time() + SETTLE_DELAY

    def rebuild(self):
        """Replace the web view with a fresh one at this size, showing the
        same sections, ring and scroll. The old one stays on top until the
        new one has loaded (webview_did_finish_load removes it)."""
        if self.old_web is not None:
            return                   # one replacement at a time
        self.rebuild_count += 1
        self.last_rebuild = (time.time(), getattr(self.window, 'place', None))
        try:
            scroll_y = float(self.web.eval_js('window.scrollY') or 0)
        except Exception:
            scroll_y = 0.0
        replay = ['setResults(%s)' % json.dumps(''.join(self.shown_html))]
        if self.current_go is not None:
            replay.append('setCurrentGo(%s)' % json.dumps(self.current_go))
        replay.append('window.scrollTo(0, %d)' % scroll_y)
        self.old_web = self.web
        self.ready = False
        self.wk = None
        self.waiting = replay + self.waiting
        self.web = self.make_web()
        self.old_web.bring_to_front()
        self.smallest = (self.width, self.height)
        self.drag_dismisses = self.dismiss_keyboard_on_drag()

    def restyle(self):
        """The theme changed: a fresh page in the palette's new colours,
        replaying the same sections, ring and scroll."""
        self.rebuild()

    @on_main_thread
    def dismiss_keyboard_on_drag(self):
        """Have the page's own scroll view put the keyboard away as soon as
        it is dragged (UIKit's keyboardDismissMode). Native, so it works
        mid-scroll, where the page's touch messages can be dropped. Returns
        False if the scroll view is not there yet (tried again on load)."""
        try:
            from objc_util import ObjCClass, sel
            views = [self.web.objc_instance]
            while views:
                view = views.pop()
                if view.respondsToSelector_(sel('scrollView')):
                    if view.respondsToSelector_(sel('evaluateJavaScript:completionHandler:')):
                        self.wk = view
                    if self.dismiss_keyboard:
                        view.scrollView().setKeyboardDismissMode_(KEYBOARD_DISMISS_ON_DRAG)
                    # The web view's own black backing shows while it resizes:
                    # make it clear so the tile's colour shows instead.
                    clear = ObjCClass('UIColor').clearColor()
                    view.setOpaque_(False)
                    view.setBackgroundColor_(clear)
                    view.scrollView().setBackgroundColor_(clear)
                    return True
                views.extend(view.subviews())
        except Exception:
            traceback.print_exc()
        return False

    # --- Clock: hand the page's events on ---------------------------------

    def keep_dock_focus(self):
        """A window in the keyboard's place is the editor text view's input
        view, shown only while that text view has focus. A tap on this page
        hands focus to the web view instead: iOS swaps in the system keyboard
        and the dock counts itself lost (Scissors' keypad, Snippets,
        2026-11-11). Hand focus straight back to the text view holding the
        dock. Does nothing outside the dock."""
        window = self.window
        if getattr(window, 'place', None) != 'dock':
            return
        dock = getattr(getattr(window, 'manager', None), 'dock', None)
        view = getattr(dock, 'text_view', None)
        if view is None or getattr(dock, 'window', None) is not window:
            return
        if not view.isFirstResponder():
            view.becomeFirstResponder()

    def tick(self, now):
        """Hand the page's events on. Each handler runs on its own, and a
        failure prints its traceback instead of stopping the clock."""
        if not self.focus_locked and getattr(self.window, 'place', None) == 'dock':
            try:
                self.focus_locked = keep_from_focus(self.web)
            except Exception:
                self.focus_locked = True     # never retry a failing lock every beat
                traceback.print_exc()
        if time.time() < self.dock_refocus_until:
            self.keep_dock_focus()   # before the window's lost-check in this beat
        events, self.events = self.events, []
        for kind, payload in events:
            try:
                if kind == 'go' and payload in self.items and self.on_pick:
                    self.pick_count += 1
                    self.on_pick(self.items[payload])
                elif kind == 'go' and self.on_go:
                    self.pick_count += 1
                    self.on_go(payload)
                elif kind == 'scroll' and self.on_scroll:
                    self.on_scroll()
            except Exception:
                self.last_error = traceback.format_exc().strip().splitlines()[-1]
                traceback.print_exc()
        if self.settle_due is not None and time.time() >= self.settle_due:
            self.settle_due = None
            small_width, small_height = self.smallest
            if self.width > small_width + 1 or self.height > small_height + 1:
                self.rebuild()
        Tile.tick(self, now)

    # --- WebView delegate -------------------------------------------------

    def webview_did_finish_load(self, webview):
        if webview is not self.web or self.ready:
            return                   # the replaced view, or a second load
        self.ready = True
        if not self.drag_dismisses:
            self.drag_dismisses = self.dismiss_keyboard_on_drag()
        waiting, self.waiting = self.waiting, []
        for script in waiting:
            self.run_now(script)
        if self.old_web is not None:
            self.old_web.delegate = None
            self.remove_subview(self.old_web)
            self.old_web = None

    def webview_should_start_load(self, webview, url, nav_type):
        if not url.startswith(codeview.LINK_SCHEME):
            return True
        rest = url[len(codeview.LINK_SCHEME):]
        trace.note('code link', rest)
        if rest.startswith(codeview.COPY_PATH):
            # ⧉ Copy on a code block: straight to the clipboard, through
            # UIPasteboard (editorkit.clip), never the clipboard module.
            from urllib.parse import unquote
            from ... import clip
            try:
                clip.set_text(unquote(rest[len(codeview.COPY_PATH):]))
            except Exception as error:
                print('editorkit: copy failed: %r' % (error,))
            return False
        # A tap in the keyboard's place: take focus back from the web view now
        # and on the clock for a moment after (see keep_dock_focus).
        self.dock_refocus_until = time.time() + DOCK_REFOCUS_SECONDS
        self.keep_dock_focus()
        self.link_count += 1
        self.last_link = (time.time(), rest)
        if rest.startswith('go/'):
            self.events.append(('go', rest[3:]))
        elif rest == 'scroll':
            self.events.append(('scroll', None))
        return False
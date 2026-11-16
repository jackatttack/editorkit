"""Cards: a Code tile with the card look (editorkit.cards).

    board = tiles.Cards(window, on_pick=picked, zoom=0.8, zoom_key='snippets')
    board.show(page)                 # an editorkit.cards.Page
    board.say('Nothing here yet')
    board.set_zoom(1.2)

    board = tiles.Cards(window, on_pick=picked, pinch='magnify',
                        pinch_target='.my-board', max_magnify=4.0)

The pinch. The page handles a pinch itself; UIWebView never zooms
natively. (2026-11-12: after a native pinch WebKit draws the page zoomed
while the scroll view's zoomScale reads 1, so nothing can bank it, and
WebKit's touch events then land on the wrong element. HANDOFF.txt and
labs/tap_probe.py have the evidence.) Native zoom is locked at 1 on the
tile's clock, and the page reads WebKit's gesture events. What a pinch
means is the page's choice:

    pinch='reflow'    (default) page zoom: CSS zoom on the whole page. The
                      grid lays itself out again, so zooming out gives more
                      columns, not just smaller text.
    pinch='magnify'   one element (pinch_target, a CSS selector) grows up
                      to max_magnify times its fitted width and the page
                      scrolls around it. It gets class ek-magnified and
                      --board-width, so its own CSS can scale text with it.
                      For game boards.
    pinch=None        no pinch (native zoom is still locked).

A CSS transform previews the pinch; on lift it becomes the real size, with
the point between the fingers kept in place. With zoom_key the result (the
page zoom, or for magnify the magnification) is remembered in
ek.store('cards') and comes back next time; zoom= is only the first size.

fresh_on_grow is on by default: the grid reflows to the width, and the old
UIWebView can draw a reflowing page clipped after a resize (tiles.Code).
A fresh web view keeps the zoom and the pinch. Other Code options
(on_scroll, dismiss_keyboard, extra_css) pass through.
"""
import json
import time

from .. import cards as card_kit
from ...stores import store
from .code import Code


# --- Settings -------------------------------------------------------------

ZOOM_STORE = 'cards'
MIN_ZOOM = 0.5                   # reflow: smallest page zoom
MAX_ZOOM = 2.0                   # reflow: largest page zoom
MAX_MAGNIFY = 4.0                # magnify: default largest magnification
PINCH_SYNC_SECONDS = 0.5         # how often the page's pinch result is read back
ZOOM_SCRIPT = "document.documentElement.style.zoom = '%.3f'"

# What a pinch means (see the module docstring).
REFLOW = 'reflow'
MAGNIFY = 'magnify'


# --- The page side of the pinch ---------------------------------------------

PINCH_SCRIPT = r"""
(function () {
  if (window.ekPinch) { return; }
  var G = window.ekPinch = {mode: __MODE__, target: __TARGET__, min: __MIN__,
                            max: __MAX__, value: __VALUE__, active: false,
                            base: 1, anchor: null};

  var style = document.createElement('style');
  style.textContent = '.ek-magnified { flex: none !important; max-width: none !important; }';
  document.head.appendChild(style);

  function clamp(value) {
    return Math.min(G.max, Math.max(G.min, value));
  }
  function pageZoom() {
    return parseFloat(document.documentElement.style.zoom) || 1;
  }
  function element() {
    return G.mode === 'magnify' ? document.querySelector(G.target) : document.body;
  }

  // reflow: the value is the page's CSS zoom (Python's set_zoom also sets it,
  // so it is read live). magnify: how many times its fitted width the
  // element is.
  function apply() {
    if (G.mode === 'reflow') {
      document.documentElement.style.zoom = G.value.toFixed(3);
      return;
    }
    var el = element();
    if (!el) { return; }
    el.classList.remove('ek-magnified');
    el.style.width = '';
    if (G.value <= 1.001) { return; }
    var fitted = el.getBoundingClientRect().width;
    var width = fitted * G.value;
    el.classList.add('ek-magnified');
    el.style.width = width + 'px';
    el.style.setProperty('--board-width', width + 'px');
  }
  G.read = function () { return G.mode === 'reflow' ? pageZoom() : G.value; };
  G.set = function (value) { G.value = clamp(value); apply(); };

  function fingerPoint(event) {
    if (event.clientX || event.clientY) { return [event.clientX, event.clientY]; }
    return [window.innerWidth / 2, window.innerHeight / 2];
  }

  document.addEventListener('gesturestart', function (event) {
    event.preventDefault();
    var el = element();
    if (!el) { return; }
    G.active = true;
    G.base = G.read();
    var rect = el.getBoundingClientRect();
    var point = fingerPoint(event);
    G.anchor = {x: point[0], y: point[1],
                fx: (point[0] - rect.left) / (rect.width || 1),
                fy: (point[1] - rect.top) / (rect.height || 1)};
    el.style.transformOrigin = (point[0] - rect.left) + 'px ' + (point[1] - rect.top) + 'px';
  }, false);

  document.addEventListener('gesturechange', function (event) {
    event.preventDefault();
    if (!G.active) { return; }
    var preview = clamp(G.base * event.scale) / G.base;
    element().style.transform = 'scale(' + preview + ')';
  }, false);

  document.addEventListener('gestureend', function (event) {
    event.preventDefault();
    if (!G.active) { return; }               // WebKit can send gestureend twice
    G.active = false;
    var el = element();
    el.style.transform = '';
    G.value = clamp(G.base * event.scale);
    apply();
    // Keep the point that was between the fingers where it was.
    var rect = el.getBoundingClientRect();
    window.scrollBy(rect.left + G.anchor.fx * rect.width - G.anchor.x,
                    rect.top + G.anchor.fy * rect.height - G.anchor.y);
    if (window.ekTapProbe) {
      ekTapProbe.records.push({event: 'pinch', lab: ekTapProbe.label, at: Date.now(),
                               mode: G.mode, zoom: G.value, gesture_scale: event.scale});
    }
  }, false);

  // magnify: a new page or a resize needs the size again.
  if (G.mode === 'magnify') {
    new MutationObserver(function () {
      var el = element();
      if (el && !G.active && G.value > 1.001 && !el.classList.contains('ek-magnified')) {
        apply();
      }
    }).observe(document.body, {childList: true, subtree: true});
    window.addEventListener('resize', function () {
      if (!G.active) { apply(); }
    });
    apply();
  }
})();
"""


def pinch_script(mode, target, low, high, value):
    """The page's pinch script for one tile (pure: a string)."""
    return (PINCH_SCRIPT.replace('__MODE__', json.dumps(mode))
                        .replace('__TARGET__', json.dumps(target))
                        .replace('__MIN__', repr(float(low)))
                        .replace('__MAX__', repr(float(high)))
                        .replace('__VALUE__', repr(float(value))))


# --- The tile -----------------------------------------------------------------

class Cards(Code):

    def __init__(self, window, on_pick=None, extra_css='', zoom=1.0, zoom_key=None,
                 pinch=REFLOW, pinch_target=None, max_magnify=MAX_MAGNIFY, **options):
        if pinch not in (REFLOW, MAGNIFY, None):
            raise ValueError("pinch is 'reflow', 'magnify' or None, not %r" % (pinch,))
        if pinch == MAGNIFY and not pinch_target:
            raise ValueError("pinch='magnify' needs pinch_target, the CSS selector to grow")
        options.setdefault('fresh_on_grow', True)
        Code.__init__(self, window, on_pick=on_pick,
                      extra_css=card_kit.CSS + extra_css, **options)
        self.zoom_key = zoom_key
        self.pinch = pinch
        self.pinch_target = pinch_target
        self.max_magnify = float(max_magnify)
        saved = store(ZOOM_STORE).get(zoom_key) if zoom_key else None
        if pinch == MAGNIFY:
            self.zoom = self.clamp(zoom)
            self.magnify = self.clamp_magnify(saved or 1.0)
        else:
            self.zoom = self.clamp(saved or zoom)
            self.magnify = 1.0
        self.next_pinch_sync = 0.0
        self.scroll_view = None          # (web view, its scroll view), once found
        self.apply_zoom()
        self.install_pinch()
        self.every(self.keep_pinch)

    def show(self, page, keep_scroll=False):
        """Show a cards.Page, replacing what was there; a page identical to
        the one showing is skipped (tools that refresh on their clock).
        keep_scroll=True keeps the page where it was scrolled (a redraw after
        a tap); otherwise it starts at the top."""
        section = page.section()
        if section[0] == getattr(self, 'shown_page', None):
            return
        self.shown_page = section[0]
        self.set_section(section, keep_scroll=keep_scroll)

    def say(self, words):
        self.shown_page = None
        Code.say(self, words)

    # --- Zoom and magnification ---------------------------------------------

    @staticmethod
    def clamp(zoom):
        return min(MAX_ZOOM, max(MIN_ZOOM, float(zoom)))

    def clamp_magnify(self, value):
        return min(self.max_magnify, max(1.0, float(value)))

    def set_zoom(self, zoom):
        """Page zoom (reflowing). Remembered under zoom_key on a reflow page."""
        self.zoom = self.clamp(zoom)
        self.apply_zoom()
        self.remember()

    def set_magnify(self, value):
        """Magnification of pinch_target on a magnify page, remembered under
        zoom_key."""
        self.magnify = self.clamp_magnify(value)
        self.run('window.ekPinch && ekPinch.set(%r)' % self.magnify)
        self.remember()

    def remember(self):
        if not self.zoom_key:
            return
        value = self.magnify if self.pinch == MAGNIFY else self.zoom
        store(ZOOM_STORE)[self.zoom_key] = value

    def apply_zoom(self):
        self.run(ZOOM_SCRIPT % self.zoom)

    def rebuild(self):
        """A fresh web view (fresh_on_grow) comes up at the same zoom, with
        the pinch installed again."""
        Code.rebuild(self)
        self.apply_zoom()
        self.install_pinch()

    # --- The pinch ------------------------------------------------------------

    def install_pinch(self):
        if self.pinch is None:
            return
        if self.pinch == REFLOW:
            low, high, value = MIN_ZOOM, MAX_ZOOM, self.zoom
        else:
            low, high, value = 1.0, self.max_magnify, self.magnify
        self.run(pinch_script(self.pinch, self.pinch_target, low, high, value))

    def keep_pinch(self, now=None):
        """On the clock: keep native zoom locked, and read the page's pinch
        result back now and then."""
        self.lock_native()
        if self.pinch is None:
            return
        now = time.time()
        if now < self.next_pinch_sync:
            return
        self.next_pinch_sync = now + PINCH_SYNC_SECONDS
        self.sync_pinch()

    def page_scroll_view(self):
        """The scroll view inside ui.WebView (SUIWebView > UIWebView), or None.
        Only a found view is cached: a miss (web view not built yet) is
        looked for again next time."""
        if self.scroll_view is not None and self.scroll_view[0] is self.web:
            return self.scroll_view[1]
        found = None
        try:
            views = list(self.web.objc_instance.subviews())
            while views:
                view = views.pop(0)
                if 'WebView' in str(view.className()) and view.respondsToSelector_('scrollView'):
                    found = view.scrollView()
                    break
                views.extend(view.subviews())
        except Exception:
            found = None
        if found is not None:
            self.scroll_view = (self.web, found)
        return found

    def lock_native(self):
        """Keep UIWebView from zooming natively. WebKit reopens the range after
        page changes, so this runs every tick. Never calls setZoomScale_:
        snapping the scroll view behind WebKit's back puts the two out of
        step."""
        scroll = self.page_scroll_view()
        if scroll is None:
            return
        try:
            if scroll.minimumZoomScale() != 1.0:
                scroll.setMinimumZoomScale_(1.0)
            if scroll.maximumZoomScale() != 1.0:
                scroll.setMaximumZoomScale_(1.0)
            if scroll.bouncesZoom():
                scroll.setBouncesZoom_(False)
            recogniser = scroll.pinchGestureRecognizer()
            if recogniser is not None and recogniser.isEnabled():
                recogniser.setEnabled_(False)
        except Exception:
            pass

    def sync_pinch(self):
        """The page owns the pinch; keep the tile's copy (and zoom_key) current
        so a rebuild comes back at the same size."""
        web = getattr(self, 'web', None)
        if web is None or not getattr(self, 'ready', False):
            return
        try:
            value = float(web.eval_js('window.ekPinch ? String(ekPinch.read()) : ""'))
        except Exception:
            return
        if self.pinch == REFLOW:
            value = self.clamp(value)
            if abs(value - self.zoom) > 0.001:
                self.zoom = value
                self.remember()
        else:
            value = self.clamp_magnify(value)
            if abs(value - self.magnify) > 0.001:
                self.magnify = value
                self.remember()
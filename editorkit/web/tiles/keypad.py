"""Keypad on a web page: pages of keys in rows, filling the space it is given.

    keypad = web.tiles.Keypad(window, pages, on_key=pressed, first='123')
    keypad.show_page('f(x)')

The same API as the native tiles.Keypad: pages maps a page name to rows; a
row is a list of key specs (dicts): label, kind ('digit', 'op', 'action' or
'go': sets the look), span (relative width, default 1), plus whatever the
tool needs. A tap calls on_key(spec). Rows share the height evenly and keys
share their row by span.

Why a web keypad: fast taps (web-views guide) make it as quick as native
buttons, it takes the editor theme like every page, and it reflows rather
than truncating. It is a Cards tile with pinch=None (native zoom locked,
nothing to zoom) and dismiss_keyboard=False (it lives in the keyboard's
place).
"""
import html

from ...native.base import palette_for
from .. import codeview
from .cards import Cards


# --- Settings -------------------------------------------------------------

SHORT_LABEL = 3                  # longer labels use the small font

CSS = """
html, body { height: 100%; overflow: hidden; }
.kp { position: fixed; left: 0; right: 0; top: 0; bottom: 0; padding: 6px;
    box-sizing: border-box; display: flex; flex-direction: column; gap: 6px;
    -webkit-user-select: none; }
.kp-row { flex: 1 1 0; display: flex; gap: 6px; min-height: 0; }
.kp-key { flex-basis: 0; min-width: 0; border-radius: 8px; display: flex;
    align-items: center; justify-content: center;
    font: 20px -apple-system, sans-serif; background: var(--card); color: var(--text); }
.kp-key.small { font-size: 15px; }
.kp-key.op { color: var(--accent); }
.kp-key.action { background: var(--kp-edge); }
.kp-key.go { background: var(--accent); color: var(--kp-on-accent); font-weight: 600; }
.kp-key:active { filter: brightness(1.3); }
"""


class Keypad(Cards):

    def __init__(self, window, pages, on_key=None, first=None, **options):
        palette = palette_for(window)
        # The two key colours the page shell has no variable for (as the
        # native keypad: actions on edge, = on the accent).
        colours = ':root { --kp-edge: %s; --kp-on-accent: %s; }\n' % (
            codeview.css_colour(palette.edge), codeview.css_colour(palette.on_accent))
        options.setdefault('dismiss_keyboard', False)
        Cards.__init__(self, window, on_go=self.tapped, extra_css=colours + CSS,
                       pinch=None, **options)
        self.pages = pages
        self.on_key = on_key
        self.page = None
        self.keys = {}                   # data-go -> key spec, for the page shown
        self.show_page(first or next(iter(pages)))

    def show_page(self, name):
        self.page = name
        self.keys = {}
        rows = []
        for row_number, specs in enumerate(self.pages[name]):
            keys = []
            for key_number, spec in enumerate(specs):
                go = 'k%d_%d' % (row_number, key_number)
                self.keys[go] = spec
                label = spec['label']
                classes = 'kp-key %s%s' % (spec.get('kind', 'digit'),
                                           ' small' if len(label) > SHORT_LABEL else '')
                keys.append('<div class="%s" data-go="%s" style="flex-grow: %s">%s</div>'
                            % (classes, go, spec.get('span', 1), html.escape(label)))
            rows.append('<div class="kp-row">%s</div>' % ''.join(keys))
        self.set_html('<div class="kp">%s</div>' % ''.join(rows))

    def tapped(self, payload):
        spec = self.keys.get(payload)
        if spec is not None and self.on_key:
            self.on_key(spec)
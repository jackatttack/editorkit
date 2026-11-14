"""Card on a web page: a message laid over the page as the window's sheet;
a tap anywhere closes it.

    card = web.tiles.Card(window, 'What this does…', on_close=done)
    window.show_sheet(card)
    card.set_text('Something else')

The same API as the native tiles.Card. Text is split on blank lines: the
first paragraph is the heading, the rest are notes (single line breaks are
kept). A tap calls on_close() when given (the owner closes the sheet),
otherwise it closes the sheet itself.

Why a web card: long help wraps and reflows to the window instead of being
cut, it takes the editor theme like every page, and a pinch makes it bigger
to read. The whole card is one tappable area, so a tap anywhere closes it,
as the native card did.
"""
from .. import cards as card_kit
from .. import prose
from .cards import Cards


# --- Settings -------------------------------------------------------------

HINT_TEXT = 'Tap to close'

CSS = """
.hc { min-height: 100vh; box-sizing: border-box; padding: 16px; }
.hc .ek-note { white-space: pre-wrap; }
.hc-hint { margin-top: 18px; color: var(--muted); font-size: 12px; text-align: center; }
"""

# The item every tap on the card hands back.
CLOSE = 'close'


class Card(Cards):

    def __init__(self, window, text='', on_close=None, **options):
        Cards.__init__(self, window, on_pick=self.tapped, extra_css=CSS, **options)
        self.on_close = on_close
        self.set_text(text)

    def set_text(self, text):
        """Show text in the docs' look (editorkit.web.prose): the first
        paragraph as the heading, the rest as prose, with `code` chips and
        bulleted lists. A tap anywhere on the card closes it."""
        paragraphs = [part.strip() for part in (text or '').split('\n\n') if part.strip()]
        heading = paragraphs[0] if paragraphs else ''
        body = '\n\n'.join(paragraphs[1:])
        inner = prose.article(prose.heading(heading, 2), prose.text(body))
        hint = '<div class="hc-hint">%s</div>' % card_kit.escape(HINT_TEXT)
        page = card_kit.Page()
        # One wrapper carries the tap, so anywhere on the card closes it.
        page.parts.append('<div class="hc"%s>%s%s</div>' % (page.go(CLOSE), inner, hint))
        self.show(page)

    def tapped(self, item):
        if self.on_close:
            self.on_close()
        else:
            self.window.close_sheet()
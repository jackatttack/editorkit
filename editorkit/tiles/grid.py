"""Grid: cards in rows that reflow with the width, in optional sections.

    grid = tiles.Grid(window, on_tap=opened)          # opened(item)
    grid.show([
        {'heading': 'COPY'},                           # starts a section
        {'emoji': '📋', 'title': 'Copy Script', 'caption': 'clipboard',
         'item': tool},
        {'emoji': '🧹', 'title': 'Clear', 'tint': '#FF5A5F', 'item': tool},
    ])

Columns follow the width: as many cards at least MIN_CARD_WIDTH wide as
fit (up to MAX_COLUMNS), so a narrow window shows one per row and names
stay whole. A card with 'dim': True is drawn quieter (a tool still to
come); 'tint' colours its title (a warning, a danger).
"""
import ui

from .base import GAP, Tile


# --- Settings -------------------------------------------------------------

MIN_CARD_WIDTH = 150          # two columns in a phone-width panel
MAX_COLUMNS = 4
CARD_HEIGHT = 64
CORNER_RADIUS = 10
PRESSED_ALPHA = 0.6
HEADING_HEIGHT = 22
SECTION_GAP = 14
ICON_FONT = ('<system>', 24)
TITLE_FONT = ('<system-bold>', 15)
CAPTION_FONT = ('<system>', 12)
HEADING_FONT = ('<system-bold>', 11)


def columns_for(width, min_width=MIN_CARD_WIDTH, gap=GAP, most=MAX_COLUMNS):
    """How many cards fit across width, at least one."""
    return max(1, min(most, int((width + gap) // (min_width + gap))))


class GridCard(ui.View):
    """One card: emoji, title and caption. A tap calls on_tap(item)."""

    def __init__(self, spec, palette, on_tap):
        self.item = spec.get('item')
        self.on_tap = on_tap
        dim = spec.get('dim', False)
        self.background_color = palette.background
        self.border_width = 1
        self.border_color = palette.edge
        self.corner_radius = CORNER_RADIUS
        self.icon = self.make_label(spec.get('emoji', ''), ICON_FONT, palette.text)
        self.icon.alignment = ui.ALIGN_CENTER
        title_colour = spec.get('tint') or (palette.dim if dim else palette.text)
        self.title = self.make_label(spec.get('title', ''), TITLE_FONT, title_colour)
        self.caption = self.make_label(spec.get('caption', ''), CAPTION_FONT, palette.dim)

    def make_label(self, text, font, colour):
        label = ui.Label(text=text, font=font)
        label.text_color = colour
        label.touch_enabled = False
        self.add_subview(label)
        return label

    def layout(self):
        width, height = self.width, self.height
        self.icon.frame = (8, 0, 40, height)
        self.title.frame = (52, height / 2 - 20, max(0, width - 58), 20)
        self.caption.frame = (52, height / 2 + 1, max(0, width - 58), 18)

    def touch_began(self, touch):
        self.alpha = PRESSED_ALPHA

    def touch_ended(self, touch):
        self.alpha = 1.0
        x, y = touch.location
        if 0 <= x <= self.width and 0 <= y <= self.height and self.on_tap:
            self.on_tap(self.item)


class Grid(Tile):

    def __init__(self, window, on_tap=None):
        Tile.__init__(self, window)
        self.on_tap = on_tap
        self.items = []              # [('heading' | 'card', view)], in order
        self.scroll = ui.ScrollView()
        self.add_subview(self.scroll)

    def show(self, specs):
        for _, view in self.items:
            self.scroll.remove_subview(view)
        self.items = []
        for spec in specs:
            if 'heading' in spec:
                label = ui.Label(text=spec['heading'], font=HEADING_FONT)
                label.text_color = self.palette.dim
                label.touch_enabled = False
                self.items.append(('heading', label))
            else:
                self.items.append(('card', GridCard(spec, self.palette, self.tapped)))
        for _, view in self.items:
            self.scroll.add_subview(view)
        self.layout()

    def tapped(self, item):
        if self.on_tap:
            self.on_tap(item)

    def layout(self):
        width = self.width
        self.scroll.frame = (0, 0, width, self.height)
        columns = columns_for(width)
        card_width = (width - (columns - 1) * GAP) / float(columns)
        y = 0
        column = 0
        for kind, view in self.items:
            if kind == 'heading':
                if column:                       # finish a part-filled row
                    y += CARD_HEIGHT + GAP
                    column = 0
                if y:
                    y += SECTION_GAP
                view.frame = (2, y, width, HEADING_HEIGHT)
                y += HEADING_HEIGHT
            else:
                view.frame = (column * (card_width + GAP), y, card_width, CARD_HEIGHT)
                column += 1
                if column == columns:
                    column = 0
                    y += CARD_HEIGHT + GAP
        if column:
            y += CARD_HEIGHT + GAP
        self.scroll.content_size = (width, y)
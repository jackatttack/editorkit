"""Toolbox's hub: the 🏡 pin that holds every tool, the tray, recent
scripts and Find.

Top to bottom when open:
    the tray bar   a chip per minimised window: tap brings it back, hold
                   and let go closes it
    the field      find a tool, an open window or a recent script
    Tools tab      the tools, as cards; a tap minimises the hub and opens
                   the tool where it works best (recent scripts are in Find)
    Find tab       what the field finds: Open windows, Recent scripts, Tools

Typing switches to Find; an empty field goes back to Tools. ? in the
header turns on help mode: a tap on a tool card then explains the tool.

Recent scripts: the hub listens for the open file changing (ek.on_change,
keyed so a rerun never adds a second listener) and keeps the list in
ek.store('deck'), paths relative to Documents, most recent first.

The hub is the tray home (Window(tray_home=True)): minimised windows shrink
into its pin and wait in the tray bar.
"""
import os
import time

import ui

import editorkit as ek
from editorkit.web import codeview

from editorkit import browse
from editorkit.native.chips import Chips

from . import filecards      # one picture of a file (Recent, Files named)
from . import files_page     # the folder sheet that picks where Find looks
from . import search         # Find shares Search's file-name and code scan
from editorkit import layouts, sources, native
from editorkit.web import tiles as web_tiles
from editorkit.native.base import Tile

from . import tools


# --- Settings -------------------------------------------------------------

TITLE = 'Toolbox'
EMOJI = '🏡'
WINDOW_KEY = 'deck-hub'
HELP_ICON = '?'
SOON_CAPTION = 'soon'
TOOLS_PAGE = 'Tools'
FIND_PAGE = 'Find'
FIND_PLACEHOLDER = 'Find a tool, window or script'

RECENT_LIMIT = 20              # recent scripts kept (and found by Find)
STORE_NAME = 'deck'
RECENT_KEY = 'recent_files'
LISTENER_KEY = 'deck-recent-files'
PYTHON_EMOJI = '🐍'
FILE_EMOJI = '📄'
DOCUMENTS = os.path.expanduser('~/Documents')

TRAY_HEIGHT = 56
TRAY_EMPTY = 'Minimised windows wait here'
CHIP_HEIGHT = 40
CHIP_GAP = 8
CHIP_FONT = ('<system-bold>', 15)
HOLD_TO_CLOSE_SECONDS = 0.45   # hold a chip this long, then let go: close
TAP_SLOP = 8                   # points a finger may wander and still tap


# --- Recent scripts -----------------------------------------------------------

def stored_path(path):
    """Inside Documents, a path relative to it (the app's own folder can
    move when iOS updates it); anywhere else, as it is."""
    relative = os.path.relpath(path, DOCUMENTS)
    return path if relative.startswith('..') else relative


def real_path(stored):
    return stored if os.path.isabs(stored) else os.path.join(DOCUMENTS, stored)


def remember_file(path):
    """Put path first in the recent scripts (once, capped)."""
    if not path or not os.path.isfile(path):
        return
    deck = ek.store(STORE_NAME)
    keep = stored_path(path)
    recent = [stored for stored in deck.get(RECENT_KEY, []) if stored != keep]
    deck[RECENT_KEY] = ([keep] + recent)[:RECENT_LIMIT]


def recent_files():
    """Recent scripts that still exist, most recent first, leaving out the
    one open now."""
    current = ek.current_file()
    found = []
    for stored in ek.store(STORE_NAME).get(RECENT_KEY, []):
        path = real_path(stored)
        if not os.path.isfile(path):
            continue
        if current and os.path.normpath(path) == os.path.normpath(current):
            continue
        found.append(path)
    return found


def file_emoji(path):
    return PYTHON_EMOJI if path.endswith('.py') else FILE_EMOJI


def folder_caption(path):
    folder = os.path.dirname(stored_path(path))
    return folder or 'Documents'


# --- Cards ------------------------------------------------------------------
# The Tools page is on editorkit's card kit (like Files, Search, Snippets).
from editorkit.web import cards as card_kit

START_ZOOM = 0.9                 # the Tools page's first size; a pinch is remembered
CARD_MIN_WIDTH = 130             # narrowest a tool card gets before the grid drops a column
HELP_NOTE = 'Help: tap a tool to read about it. ? again to finish.'
TIDY_ICON = '🪟'                 # header: lay the open windows out evenly
RECENT_HEADING = 'Recent scripts'
RECENT_ON_TOOLS = 12             # recent scripts under the tool cards
KEEP_FIND_OPEN = True            # opening a found script keeps the hub and its search on
                                 #   screen (several can be opened); False: the hub folds
CLEAR_ICON = '⌫'                 # header, while Find holds a term: back to the home view
INTRO = 'Tools over your code, built on editorkit. New here? 🎓 Learn has lessons and examples.'


def tool_cards(specs):
    """One card per tool spec (tool_card): its emoji large beside where it
    opens; 'soon' tools dimmed. Taps give each spec's item."""
    return [card_kit.Card(spec['title'], item=spec['item'],
                          body=card_kit.face(spec['emoji'], spec['caption'], dim=spec['dim']))
            for spec in specs]


def recent_cards(paths):
    """Recent scripts as Toolbox's file cards: a tap opens one in the
    editor, 📜 in a script window."""
    return [filecards.file_card(path, ('file', path), search.ViewHit(search.Hit(path, 1, 0, 0)),
                                where=os.path.dirname(stored_path(path)) or 'Documents')
            for path in paths]


def hub_page(specs, helping=False, recent=()):
    """The Tools page: on the home view a line on what Toolbox is with ℹ️
    About, then the tool cards, then recent scripts as file cards."""
    page = card_kit.Page()
    if helping:
        page.note(HELP_NOTE)
    if not any(spec['item'][0] == 'back' for spec in specs):    # home, not a group
        page.note(INTRO)
        page.buttons([card_kit.Action('ℹ️ About', ('about', None))])
    page.grid(tool_cards(specs), min_width=CARD_MIN_WIDTH)
    if recent:
        page.heading(RECENT_HEADING)
        page.grid(recent_cards(recent), min_width=filecards.CARD_WIDTH)
    return page

def tool_card(tool):
    if 'group' in tool:
        count = len(tool['group'])
        return {'emoji': tool['emoji'], 'title': tool['name'],
                'caption': '%d %s' % (count, tool['home'] if count != 1 else tool['home'].rstrip('s')),
                'dim': False, 'item': ('group', tool)}
    ready = tool['open'] is not None
    return {'emoji': tool['emoji'], 'title': tool['name'],
            'caption': tool.get('what', tool['home']) if ready else SOON_CAPTION,
            'dim': not ready, 'item': ('tool', tool)}


BACK_CARD = {'emoji': '⬅️', 'title': 'Back', 'caption': 'all tools', 'dim': False,
             'item': ('back', None)}


# --- The tray bar -----------------------------------------------------------

class Chip(ui.View):
    """One minimised window in the tray bar. Tap: bring it back. Hold, then
    let go: close it."""

    def __init__(self, window, palette, on_tap, on_hold):
        self.window = window
        self.on_tap = on_tap
        self.on_hold = on_hold
        self.background_color = palette.background
        self.border_width = 1
        self.border_color = palette.edge
        self.corner_radius = CHIP_HEIGHT / 2.0
        self.label = ui.Label(font=CHIP_FONT, text_color=palette.text,
                              alignment=ui.ALIGN_CENTER,
                              text='%s  %s' % (window.emoji, window.title))
        self.label.touch_enabled = False
        self.add_subview(self.label)
        self.width = ui.measure_string(self.label.text, font=CHIP_FONT)[0] + 28
        self.height = CHIP_HEIGHT
        self.pressed_at = None
        self.travel = 0.0

    def layout(self):
        self.label.frame = (0, 0, self.width, self.height)

    def touch_began(self, touch):
        self.pressed_at = time.time()
        self.travel = 0.0
        self.alpha = 0.6

    def touch_moved(self, touch):
        self.travel += (abs(touch.location.x - touch.prev_location.x)
                        + abs(touch.location.y - touch.prev_location.y))
        if self.travel > TAP_SLOP:
            self.pressed_at = None            # a scroll, not a tap or a hold
            self.alpha = 1.0

    def touch_ended(self, touch):
        self.alpha = 1.0
        if self.pressed_at is None:
            return
        held = time.time() - self.pressed_at
        self.pressed_at = None
        if held >= HOLD_TO_CLOSE_SECONDS:
            self.on_hold(self.window)
        else:
            self.on_tap(self.window)


class TrayBar(Tile):
    """The bar across the top of the open hub: one chip per minimised
    window, most recent first, scrolling sideways when they overflow. A Tile,
    so it stacks in the accessory column above the field."""

    HEIGHT = TRAY_HEIGHT

    def __init__(self, window, on_tap, on_hold):
        Tile.__init__(self, window)
        self.on_tap = on_tap
        self.on_hold = on_hold
        self.scroll = ui.ScrollView()
        self.scroll.shows_horizontal_scroll_indicator = False
        self.scroll.background_color = (0, 0, 0, 0)
        self.add_subview(self.scroll)
        self.empty = ui.Label(text=TRAY_EMPTY, alignment=ui.ALIGN_CENTER,
                              font=('<system>', 13))
        self.empty.text_color = self.palette.dim
        self.empty.touch_enabled = False
        self.add_subview(self.empty)
        self.chips = []

    def layout(self):
        self.scroll.frame = (0, 0, self.width, self.height)
        self.empty.frame = (0, 0, self.width, self.height)
        self.place_chips()

    def show(self, windows):
        palette = getattr(self.window, 'palette', None) or self.palette
        for chip in self.chips:
            self.scroll.remove_subview(chip)
        self.chips = [Chip(window, palette, self.on_tap, self.on_hold) for window in windows]
        for chip in self.chips:
            self.scroll.add_subview(chip)
        self.empty.hidden = bool(self.chips)
        self.place_chips()

    def place_chips(self):
        x = CHIP_GAP
        top = (self.height - CHIP_HEIGHT) / 2.0
        for chip in self.chips:
            chip.frame = (x, top, chip.width, CHIP_HEIGHT)
            x += chip.width + CHIP_GAP
        self.scroll.content_size = (x, self.height)


# --- The hub ----------------------------------------------------------------

# --- Find: one search for everything --------------------------------------
#
# The Find page lists, in order: open windows, recent scripts and tools
# (instant, on every keystroke), then files by name and code (Search's
# scan, after a pause in typing). Each section has a header with a count;
# a tap on the header folds the section, remembered while the hub lives.
# Folding toggles a class on the page, so a running scan carries on.

FIND_SECTIONS = (('open', 'Open'), ('recent', 'Recent'), ('tools', 'Tools'),
                 ('names', 'Files named'), ('code', 'Code'))
FIND_CODE_FILES = 12         # code hits from this many files until Show all
FIND_NAME_FILES = 6          # file-name cards until Show all
FIND_RECENT = 6              # recent script cards
MORE_LABEL = 'Show all ↓'    # the row after a capped section: lifts its cap
SCOPE_HERE = '⌂'             # chip: search the open file's folder
SCOPE_MEMORY = {}            # the folder Find last searched, while Toolbox is installed

FIND_CSS = search.RESULTS_CSS + """
.hf-head { display: flex; align-items: baseline; gap: 6px; margin: 12px 6px 4px;
    font: 600 13px -apple-system, sans-serif; color: var(--muted); }
.hf-arrow::after { content: "▾"; }
.hf-count { font-weight: 400; opacity: 0.75; }
.hf-grid { width: calc(100vw - 20px); }
""" + ''.join(
    'body.hf-hide-%s .hf-%s { display: none; }\n'
    'body.hf-hide-%s .hf-head-%s .hf-arrow::after { content: "▸"; }\n'
    % (name, name, name, name) for name, title in FIND_SECTIONS)


def head_section(name, count):
    """A section's header: its title and count; a tap hands back ('fold', name).
    The count has an id so it can change while the scan runs."""
    ids = codeview.SectionIds('h-%s' % name)
    title = dict(FIND_SECTIONS)[name]
    html = ('<div class="hf-head hf-head-%s"%s><span class="hf-arrow"></span>'
            '<span>%s</span><span class="hf-count" id="hf-count-%s">%s</span></div>'
            % (name, codeview.go_attribute(ids.go(('fold', name))),
               codeview.escape(title), name, count))
    return html, ids.items


def rows_body(section, fold_name, rows):
    """codeview Rows as a section's body, folding with fold_name's header."""
    html, items = codeview.rows_section(section, '', rows)
    return '<div class="hf-body hf-%s">%s</div>' % (fold_name, html), items


def grid_body(section, fold_name, grid, min_width):
    """Cards (card_kit.Card) as a section's body, folding with fold_name's header."""
    page = card_kit.Page(section)
    page.grid(grid, min_width=min_width)
    html, items = page.section()
    return '<div class="hf-body hf-%s hf-grid">%s</div>' % (fold_name, html), items


def scope_label(folder):
    return 'in %s ▾' % (os.path.basename(folder) or folder)


class Hub:

    def __init__(self):
        self.help_mode = False
        self.group = None            # the group whose page shows (Games), or None
        self.window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, tray_home=True)
        self.window.add_button(HELP_ICON, self.toggle_help, name='help')
        # 🪟 Tidy lives in the header: always one tap away, not a tool.
        self.window.add_button(TIDY_ICON, self.tidy_tapped, name='tidy')

        # One page, so no tabs: the results tile shows the home view (tool
        # cards, recent scripts) while the field is empty, Find's sections
        # while typing (refresh_grid and start_find).

        self.tray_bar = TrayBar(self.window, on_tap=self.tray_tapped, on_hold=self.tray_held)
        # Find: one web page of sections (see "Find: one search for everything").
        # fresh_on_grow: a page whose width follows the window draws clipped after
        # a resize (the iPad showed the tool grid cut off at two thirds).
        self.results = web_tiles.Code(self.window, on_pick=self.picked, extra_css=FIND_CSS,
                                      fresh_on_grow=True)
        # Where Find looks: a folder chip (a sheet of folder tiles) and ⌂.
        self.scope = SCOPE_MEMORY.get('folder', DOCUMENTS)
        if not os.path.isdir(self.scope):
            self.scope = DOCUMENTS
        self.scope_chips = Chips(self.window)
        self.scope_chips.add('scope', scope_label(self.scope), lambda name: self.choose_scope())
        self.scope_chips.add('here', SCOPE_HERE, lambda name: self.scope_to_file())
        self.find = layouts.query_list(
            self.window, FIND_PLACEHOLDER, on_change=self.typed, page=FIND_PAGE,
            body=self.results, rows_above=[self.tray_bar], rows=[self.scope_chips],
            compact_in_dock=False)
        self.find.top.set_visible(self.tray_bar, bool(self.window.tray()))
        self.opener = ek.Opener(self.window)
        self.folded = set()              # Find sections folded by a tap on their header
        self.term = ''
        self.clear_shown = False         # ⌫ in the header (show_clear_button)
        self.scan_due = None             # when the file scan starts (after typing stops)
        self.find_names = self.find_code = False
        self.counts = {'names': 0, 'code': 0}
        self.code_files = 0
        self.heads = set()               # sections whose header is on the page
        self.capped = False
        self.names_more = False
        self.expanded = set()            # sections whose cap Show all lifted
        self.scope_sheet = None          # the folder sheet, made on first use
        self.scan_job = ek.Job(self.window, search.scan,
                               on_items=self.sections_arrived, on_done=self.scan_done,
                               on_error=self.scan_failed)
        self.window.every(self.find_tick)
        self.card = web_tiles.Card(self.window, on_close=self.close_help)
        self.window.on('tray', self.refresh)
        self.window.on('open', self.refresh)
        self.window.on('console', self.refresh)
        # Pull an editor tab down out of the tab bar: it opens as a script
        # window. The hub lives as long as Toolbox, so its clock keeps new
        # tabs attached.
        from editorkit import tabpull
        tabpull.on_pull(self.tab_pulled, self.window)

        remember_file(ek.current_file())
        ek.on_change(self.file_changed, kinds=('file',), key=LISTENER_KEY)
        self.refresh_grid()

    def show(self):
        self.window.show()

    def tidy_tapped(self, *ignored):
        """🪟: fold the hub, then lay the open windows out evenly once it has
        finished moving (tapped again within a while: put them back)."""
        self.window.minimise()
        self.window.when_still(lambda window: ek.tidy())

    def tab_pulled(self, path):
        """An editor tab pulled down out of the tab bar: its script window."""
        from . import scriptview
        from editorkit import tabs
        from editorkit.windows import tabrow
        # A window's stand-in tab: the window comes back out as itself.
        live = ek.live_windows()
        for window in (live.values() if hasattr(live, 'values') else live):
            if tabrow.same_path(getattr(window, 'tab_path', None), path):
                window.out_of_tab()
                tabs.close_tab(path)
                return
        # A file's tab turns into its code view: the window opens, the tab
        # closes (dropping the window back into the tab row opens it again).
        if scriptview.open_script_window(path) is not None:
            tabs.close_tab(path)

    def refresh(self, *ignored):
        waiting = self.window.tray()
        self.tray_bar.show(waiting)
        self.find.top.set_visible(self.tray_bar, bool(waiting))   # no space for an empty tray
        self.start_find(self.term, keep_expanded=True)

    def refresh_grid(self):
        """The home view, shown while the field is empty: a card per tool
        (or a group's tools after a Back card), then recent scripts. Typing
        replaces it with Find's sections; nothing to do while it does."""
        if self.term:
            return
        if self.group is not None:
            specs = [BACK_CARD] + [tool_card(tool) for tool in self.group['group']]
        else:
            specs = [tool_card(tool) for tool in tools.TOOLS]
        recent = recent_files()[:RECENT_ON_TOOLS] if self.group is None else ()
        html, items = hub_page(specs, self.help_mode, recent).section()
        self.results.set_section(('<div class="hf-grid">%s</div>' % html, items))

    def file_changed(self, event):
        path = event['new']
        if path and '/.' not in path:      # not stand-in tabs (.editorkit) or other hidden files
            remember_file(path)

    # --- Find -------------------------------------------------------------

    def open_source(self):
        """Windows waiting in the tray, most recent first."""
        return sources.ListSource(
            'Open', self.window.tray,
            lambda window: sources.Row(window.emoji, window.title, ('window', window)))

    def recent_source(self):
        """Recent scripts, most recent first."""
        return sources.ListSource(
            'Recent', recent_files,
            lambda path: sources.Row(file_emoji(path), stored_path(path), ('file', path)))

    def tools_source(self):
        """Every tool that can open now."""
        ready = [tool for tool in tools.every_tool() if tool['open'] is not None]
        return sources.ListSource(
            'Tools', ready,
            lambda tool: sources.Row(tool['emoji'], '%s  ·  %s' % (tool['name'], tool.get('what', tool['home'])),
                                     ('tool', tool)))

    def typed(self, field, text):
        self.start_find(text.strip())

    def start_find(self, term, keep_expanded=False):
        """Show the instant sections for term now, and have the clock start
        the file scan after a pause in typing: names from MIN_NAME_LETTERS,
        code from MIN_CODE_LETTERS. A new term puts every cap back unless
        keep_expanded."""
        self.scan_job.cancel()
        if not keep_expanded:
            self.expanded = set()
        self.term = term
        self.scan_due = None
        self.counts = {'names': 0, 'code': 0}
        self.code_files = 0
        self.heads = set()
        self.capped = False
        self.names_more = False
        if not term:
            self.refresh_grid()              # the home view
            return
        self.results.set_section(self.instant_section(term))
        self.apply_folds()
        self.find_names = len(term) >= search.MIN_NAME_LETTERS
        self.find_code = len(term) >= search.MIN_CODE_LETTERS
        if self.find_names or self.find_code:
            self.scan_due = time.time() + search.TYPING_PAUSE

    def instant_section(self, term):
        """Open windows (rows), recent scripts (file cards) and tools (the
        Tools tab's cards) matching term, each under its header; a section
        with nothing is left out."""
        pieces, items = [], {}

        def add(name, count, body):
            self.heads.add(name)
            head_html, head_items = head_section(name, count)
            pieces.extend([head_html, body[0]])
            items.update(head_items)
            items.update(body[1])

        windows = self.open_source().search(term)
        if windows:
            add('open', len(windows), rows_body(
                'f-open', 'open',
                [codeview.Row('%s  %s' % (row.label, row.text), 'plain', row.item)
                 for row in windows]))
        recent = [row.item[1] for row in self.recent_source().search(term)]
        if recent:
            add('recent', len(recent), grid_body(
                'f-recent', 'recent', recent_cards(recent[:FIND_RECENT]), filecards.CARD_WIDTH))
        found = [row.item[1] for row in self.tools_source().search(term)]
        if found:
            add('tools', len(found), grid_body(
                'f-tools', 'tools', tool_cards([tool_card(tool) for tool in found]),
                CARD_MIN_WIDTH))
        return ''.join(pieces), items

    def show_clear_button(self, wanted):
        """⌫ in the header while Find holds a term: one tap empties Find and
        goes back to the home view."""
        if wanted == self.clear_shown:
            return
        self.clear_shown = wanted
        if wanted:
            self.window.add_button(CLEAR_ICON, lambda *ignored: self.reset_find(), name='clear')
        else:
            self.window.remove_button('clear')

    def find_tick(self, *ignored):
        self.show_clear_button(bool(self.term))
        if self.scan_due is not None and time.time() >= self.scan_due:
            self.scan_due = None
            name_limit = search.MAX_NAME_HITS if 'names' in self.expanded else FIND_NAME_FILES
            self.scan_job.start(self.term, self.scope, search.DEFAULT_CONTEXT,
                                (False, False, False), None,
                                (self.find_names, self.find_code), (name_limit, False))

    def add_head(self, pieces, items, name):
        """A scanned section's header, once and in order: Files named comes
        before Code whenever names were searched, even with none found."""
        if name in self.heads:
            return
        if name == 'code' and self.find_names:
            self.add_head(pieces, items, 'names')
        self.heads.add(name)
        html, head_items = head_section(name, self.counts[name])
        pieces.append(html)
        items.update(head_items)

    def sections_arrived(self, arrived):
        """The scan's sections for this beat: the Files named cards, then a
        section per file of code, up to FIND_CODE_FILES files and a More row."""
        pieces, items = [], {}
        for path, (html, section_items), lines, targets in arrived:
            if path is None:
                self.counts['names'] = lines
                self.names_more = lines >= FIND_NAME_FILES and 'names' not in self.expanded
                self.add_head(pieces, items, 'names')
                pieces.append('<div class="hf-body hf-names">%s</div>' % html)
                items.update(section_items)
                if self.names_more:
                    more_html, more_items = rows_body(
                        'f-more-names', 'names',
                        [codeview.Row(MORE_LABEL, 'plain', ('more', 'names'))])
                    pieces.append(more_html)
                    items.update(more_items)
                continue
            self.add_head(pieces, items, 'code')
            self.counts['code'] += lines
            self.code_files += 1
            if 'code' in self.expanded or self.code_files <= FIND_CODE_FILES:
                pieces.append('<div class="hf-body hf-code">%s</div>' % html)
                items.update(section_items)
            elif self.code_files == FIND_CODE_FILES + 1:
                more_html, more_items = rows_body(
                    'f-more', 'code', [codeview.Row(MORE_LABEL, 'plain', ('more', 'code'))])
                pieces.append(more_html)
                items.update(more_items)
        if pieces:
            self.results.add_section((''.join(pieces), items))
        self.update_counts()
        self.apply_folds()

    def scan_done(self, capped):
        self.capped = bool(capped)
        pieces, items = [], {}
        for name, searched in (('names', self.find_names), ('code', self.find_code)):
            if searched:
                self.add_head(pieces, items, name)
        if pieces:
            self.results.add_section((''.join(pieces), items))
        self.update_counts()
        self.apply_folds()

    def scan_failed(self, *details):
        print('Find: the file scan failed:', *details)

    def update_counts(self):
        script = []
        for name in ('names', 'code'):
            more = self.capped if name == 'code' else self.names_more
            text = '%d%s' % (self.counts[name], '+' if more else '')
            script.append("var e = document.getElementById('hf-count-%s'); "
                          "if (e) e.textContent = '%s';" % (name, text))
        self.results.run(' '.join(script))

    def apply_folds(self):
        self.results.run(' '.join(
            "document.body.classList.%s('hf-hide-%s');"
            % ('add' if name in self.folded else 'remove', name)
            for name, title in FIND_SECTIONS))

    def toggle_fold(self, name):
        self.folded ^= {name}
        self.apply_folds()

    def picked(self, item):
        """A tap on the Find page: a header folds its section. A found script
        opens and Find keeps its search, with the hub on screen while
        KEEP_FIND_OPEN (⌫ empties it); a tool or window opens after Find
        empties and the hub folds away."""
        if type(item) is tuple and item[0] == 'fold':
            self.toggle_fold(item[1])
            return
        if type(item) is tuple and item[0] == 'more':
            self.expanded.add(item[1])
            self.start_find(self.term, keep_expanded=True)
            return
        if not self.term:                    # the home view: tool cards, recent scripts
            self.card_tapped(item)
            return
        if not isinstance(item, search.Hit) and not isinstance(item, (search.ViewHit,
                                                                      search.NameHit)):
            self.reset_find()
            self.open_item(item)                 # a tool or a window: folds the hub
            return
        self.find.field.unfocus()
        if not KEEP_FIND_OPEN:
            self.window.minimise()
        if isinstance(item, search.ViewHit):
            from . import scriptview
            scriptview.open_script_window(item.hit.path, item.hit.line)
        elif isinstance(item, search.NameHit):
            self.opener.go(item.path)
        else:
            self.opener.go(item.path, item.line, item.start, item.end)

    def reset_find(self):
        self.find.field.set_value('')
        self.find.field.unfocus()
        self.start_find('')

    def find_for(self, term='', scope=None):
        """Find showing term in scope (Files' 🔍, Find in script's ⤢)."""
        if scope:
            self.set_scope(scope)
        term = term or ''
        self.find.field.set_value(term)
        self.start_find(term.strip())
        self.find.field.focus()

    # --- Find: where to look ----------------------------------------------

    def set_scope(self, folder):
        self.scope = SCOPE_MEMORY['folder'] = folder
        self.scope_chips.set_label('scope', scope_label(folder))
        self.start_find(self.term, keep_expanded=True)

    def scope_to_file(self):
        path = ek.current_file()
        self.set_scope(os.path.dirname(path) if path else DOCUMENTS)

    def choose_scope(self):
        """The scope chip: a sheet of folder tiles like Files' (tap a tile to
        go in, a chip to go up), with 'Search in' to pick and Cancel."""
        self.find.field.unfocus()
        if self.scope_sheet is None:
            self.scope_sheet = web_tiles.Cards(self.window, on_pick=self.scope_picked,
                                               zoom=search.SCOPE_ZOOM, zoom_key='find-scope',
                                               extra_css=files_page.CSS)
            # Opaque, or the results show through the sheet.
            self.scope_sheet.background_color = self.window.palette.panel
        self.browse_scope(self.scope)
        self.window.show_sheet(self.scope_sheet)

    def browse_scope(self, folder):
        entries = browse.list_folder(folder, folders_only=True)
        self.scope_sheet.show(files_page.folder_picker_page(
            folder, DOCUMENTS, entries, files_page.facts_for_entry, now=time.time()))

    def scope_picked(self, item):
        kind, value = item
        if kind == 'folder':
            self.browse_scope(value)
        elif kind == 'pick':
            self.window.close_sheet()
            self.set_scope(value)
        elif kind == 'cancel':
            self.window.close_sheet()

    def open_item(self, item):
        """Minimise the hub, then open what was picked: a tool, a window
        from the tray, or a script."""
        kind, thing = item
        self.window.minimise()
        if self.group is not None:
            self.group = None            # next time the hub opens on every tool
            self.refresh_grid()
        if kind == 'window':
            thing.show()
        elif kind == 'file':
            ek.open_file(thing)
        else:
            thing['open']()

    # --- The tray ---------------------------------------------------------

    def tray_tapped(self, window):
        self.window.minimise()
        window.show()

    def tray_held(self, window):
        window.close()

    # --- Cards and help ---------------------------------------------------

    def card_tapped(self, item):
        if isinstance(item, search.ViewHit):         # 📜 on a recent script's card
            from . import scriptview
            self.window.minimise()
            scriptview.open_script_window(item.hit.path, item.hit.line)
            return
        kind, thing = item
        if kind == 'about':
            from . import learn
            self.card.set_text(learn.ABOUT)
            self.window.show_sheet(self.card)
            return
        if kind == 'back':
            self.group = None
            self.refresh_grid()
            return
        if kind == 'group' and not self.help_mode:
            self.group = thing
            self.refresh_grid()
            return
        if kind in ('tool', 'group') and (self.help_mode or thing['open'] is None):
            text = '%s  %s\n\n%s' % (thing['emoji'], thing['name'], thing['about'])
            if 'group' not in thing and thing.get('home'):
                text += '\n\nOpens %s.' % thing['home']
            self.card.set_text(text)
            self.window.show_sheet(self.card)
            return
        self.open_item(item)

    def toggle_help(self, *ignored):
        self.help_mode = not self.help_mode
        self.window.set_button('help', on=self.help_mode)
        self.refresh_grid()              # the help note comes and goes
        if not self.help_mode:
            self.close_help()

    def close_help(self, *ignored):
        if self.window.sheet is self.card:
            self.window.close_sheet()


def open_hub():
    hub = Hub()
    hub.show()
    return hub


def open_find(term='', scope=None):
    """The hub on its Find page, searching for term in scope (a folder;
    None keeps the last one)."""
    hub = open_hub()
    hub.find_for(term, scope)
    return hub
"""Find bar: search the open script in place.

A slim bar across the top of the code (home='top_bar'). Matches are marked
with the editor's own search highlight and the current one is selected and
scrolled to; ◀ ▶ (or Return) step through them. The second row replaces
the current match or all of them. Header toggles: Aa (case), W (whole
word), .* (regex). Edits to the script, or a tab switch, are noticed and
the matches found again.

    from editorkit_toolbox import find
    find.open_find()
"""
import os

import ui
import editorkit as ek


# --- Settings -------------------------------------------------------------

TITLE = 'Find in script'
EMOJI = '🔍'                  # Search (the wide mode) is 🔎
WINDOW_KEY = 'deck-find'
BAR_HEIGHT = 150             # header plus the find and replace rows (⇄ on)
COMPACT_HEIGHT = 108         # header plus the find row: the usual size
REPLACE_ICON = '⇄'           # header: show or hide the Replace row
WIDEN_ICON = '⤢'             # header: this search in the full Search
ROW_HEIGHT = 36
GAP = 6
COUNT_WIDTH = 64
REPLACE_WIDTH = 84
ALL_WIDTH = 52
RECHECK_SECONDS = 0.5        # how often to notice edits to the script

# Colours come from the window's palette (FindBar.palette), so the bar
# follows the theme, light or dark (RELEASE.txt 1.2).

# Header toggles: (attribute, icon), in header order.
TOGGLES = (('case_sensitive', 'Aa'), ('whole_word', 'W'), ('regex', '.*'))


class FindBar(ui.View):
    """The find and replace rows. Searches through ek.find_all, marks with
    ek.highlight, moves with ek.select and edits with ek.replace."""

    def __init__(self, window):
        self.window = window
        self.case_sensitive = False
        self.whole_word = False
        self.regex = False
        self.hits = []               # [(start, end)] in Python indices
        self.current = -1            # index into hits, -1 for none
        self.anchor = 0              # search from here: the cursor when typing began
        self.seen = None             # (length, hash) of the text last searched
        self.next_check = 0.0
        self.replacing = False       # the Replace row shows (⇄)
        self.widening = False        # ⤢ closed the bar: whoever opened it stays away
        self.start_term = None       # open_find(term=): the first search, over the selection

        self.term_field = self.make_field('Find')
        self.replace_field = self.make_field('Replace with')
        self.count_label = ui.Label(font=('<system>', 13), alignment=ui.ALIGN_CENTER)
        self.count_label.text_color = self.palette().dim
        self.add_subview(self.count_label)
        self.previous_button = self.make_button('◀', self.previous_hit)
        self.next_button = self.make_button('▶', self.next_hit)
        self.replace_button = self.make_button('Replace', self.replace_one)
        self.all_button = self.make_button('All', self.replace_every)
        for view in (self.replace_field, self.replace_button, self.all_button):
            view.hidden = True       # compact until ⇄

    # --- Building ---------------------------------------------------------

    def palette(self):
        """The window's palette (the shared one once shown), so the bar
        follows the theme, light or dark."""
        from editorkit.tiles.base import palette_for
        return palette_for(self.window)

    def make_field(self, placeholder):
        from editorkit.tiles.base import style_field
        from editorkit.tiles.field import tint_placeholder
        field = style_field(ui.TextField(placeholder=placeholder), self.palette())
        tint_placeholder(field, self.palette().dim)
        field.delegate = self
        self.add_subview(field)
        return field

    def make_button(self, title, action):
        palette = self.palette()
        button = ui.Button(title=title, font=('<system-bold>', 14))
        button.background_color = palette.background
        button.tint_color = palette.text
        button.corner_radius = 8
        button.action = action
        self.add_subview(button)
        return button

    def restyle(self):
        """The theme changed: re-apply the palette's colours."""
        from editorkit.tiles.field import tint_placeholder
        palette = self.palette()
        for field in (self.term_field, self.replace_field):
            field.background_color = palette.background
            field.text_color = palette.text
            field.tint_color = palette.accent
            tint_placeholder(field, palette.dim)
        for button in (self.previous_button, self.next_button, self.replace_button,
                       self.all_button):
            button.background_color = palette.background
            button.tint_color = palette.text
        self.count_label.text_color = palette.dim

    def layout(self):
        width = self.width
        size = ROW_HEIGHT
        next_x = width - size
        previous_x = next_x - GAP - size
        count_x = previous_x - GAP - COUNT_WIDTH
        self.term_field.frame = (0, 0, max(40, count_x - GAP), size)
        self.count_label.frame = (count_x, 0, COUNT_WIDTH, size)
        self.previous_button.frame = (previous_x, 0, size, size)
        self.next_button.frame = (next_x, 0, size, size)
        row = size + GAP
        all_x = width - ALL_WIDTH
        replace_x = all_x - GAP - REPLACE_WIDTH
        self.replace_field.frame = (0, row, max(40, replace_x - GAP), size)
        self.replace_button.frame = (replace_x, row, REPLACE_WIDTH, size)
        self.all_button.frame = (all_x, row, ALL_WIDTH, size)

    # --- Opening and closing --------------------------------------------

    def begin(self):
        """On open: prefill with a one-line selection, find, focus the field."""
        chosen = ek.selection()
        if self.start_term:
            self.term_field.text, self.start_term = self.start_term, None
        elif chosen and chosen[1] > chosen[0]:
            picked = ek.text()[chosen[0]:chosen[1]]
            if picked and '\n' not in picked:
                self.term_field.text = picked
        self.anchor = chosen[0] if chosen else 0
        self.show_replace(self.replacing)    # the remembered size may be the tall one
        self.search(select=bool(self.term_field.text))
        self.term_field.begin_editing()

    def end(self):
        ek.clear_highlights()

    def widen(self):
        """⤢: this term in the hub's Find, over the script's folder; the bar
        closes (without bringing back Scissors, if it came from there)."""
        term = self.term_field.text or ''
        path = ek.current_file()
        self.widening = True
        self.window.close()
        from . import hub
        hub.open_find(term=term, scope=os.path.dirname(path) if path else None)

    def show_replace(self, on):
        """⇄: the Replace row and a taller bar, or the find row alone."""
        self.replacing = on
        for view in (self.replace_field, self.replace_button, self.all_button):
            view.hidden = not on
        self.window.set_button('replace', on=on)
        self.window.size = (0, BAR_HEIGHT if on else COMPACT_HEIGHT)
        self.window.when_still(lambda window: window.move_to('top_bar', keyboard=False))

    # --- Finding ----------------------------------------------------------

    def search(self, select=False):
        """Find every match from scratch; the current one is the first at or
        after the anchor. With select, select and scroll to it."""
        term = self.term_field.text or ''
        source = ek.text()
        self.seen = (len(source), hash(source))
        self.hits = ek.find_all(term, source, self.case_sensitive, self.whole_word, self.regex)
        self.show_marks(term)
        if self.hits:
            self.current = next((number for number, (start, _) in enumerate(self.hits)
                                 if start >= self.anchor), 0)
            if select:
                self.go()
        else:
            self.current = -1
        self.show_count()

    def show_marks(self, term):
        # The editor's own marks are plain text, so they would mislead in
        # whole-word or regex mode: there only the selection shows the match.
        if term and not self.regex and not self.whole_word:
            ek.highlight(term, self.case_sensitive)
        else:
            ek.clear_highlights()

    def go(self):
        start, end = self.hits[self.current]
        ek.select(start, end)

    def next_hit(self, *ignored):
        if self.hits:
            self.current = (self.current + 1) % len(self.hits)
            self.go()
            self.show_count()

    def previous_hit(self, *ignored):
        if self.hits:
            self.current = (self.current - 1) % len(self.hits)
            self.go()
            self.show_count()

    def show_count(self, note=None):
        if note is not None:
            self.count_label.text = note
        elif not self.term_field.text:
            self.count_label.text = ''
        elif not self.hits:
            self.count_label.text = 'none'
        else:
            self.count_label.text = '%d/%d' % (self.current + 1, len(self.hits))

    # --- Replacing --------------------------------------------------------

    def replace_one(self, *ignored):
        """Replace the current match, then move to the next."""
        if self.current < 0:
            return
        start, end = self.hits[self.current]
        new_text = self.replace_field.text or ''
        if ek.replace(start, end, new_text):
            self.anchor = start + len(new_text)
            self.search(select=True)

    def replace_every(self, *ignored):
        term = self.term_field.text or ''
        if not term:
            return
        count = ek.replace_all(term, self.replace_field.text or '',
                               self.case_sensitive, self.whole_word, self.regex)
        self.anchor = 0
        self.search(select=False)
        self.show_count('%d done' % count)

    # --- Toggles and fields -----------------------------------------------

    def toggle(self, name):
        setattr(self, name, not getattr(self, name))
        self.window.set_button(name, on=getattr(self, name))
        self.search(select=True)

    def textfield_did_change(self, field):
        if field is self.term_field:
            chosen = ek.selection()
            # Keep searching from where typing began, not from the last match.
            if self.current < 0 and chosen:
                self.anchor = chosen[0]
            self.search(select=True)

    def textfield_should_return(self, field):
        if field is self.term_field:
            self.next_hit()
        else:
            self.replace_one()
        return False

    # --- The window's clock -----------------------------------------------

    def tick(self, now):
        """Notice edits and tab switches, and find again without jumping."""
        if now < self.next_check or not self.term_field.text:
            return
        self.next_check = now + RECHECK_SECONDS
        source = ek.text()
        if (len(source), hash(source)) != self.seen:
            if self.current >= 0:
                self.anchor = self.hits[self.current][0]
            self.search(select=False)


def open_find(path=None, on_close=None, term=None):
    """Open the Find bar (or bring the open one back). path: search that
    file, opened as the tab first when it is not the open one (the bar
    finds again on the tab switch). on_close(): runs when the bar closes
    (Scissors comes back)."""
    if path and os.path.realpath(path) != os.path.realpath(ek.current_file() or ''):
        ek.open_file(path)
    # Tinted so code shows through; a top bar insets the code by default,
    # so the current match is never hidden under the bar.
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, home='top_bar',
                       size=(0, COMPACT_HEIGHT), backdrop='tinted')
    bar = FindBar(window)
    bar.start_term = term            # Search's ⤡: carry the term over
    window.find_bar = bar            # for the deck's checks (checks/regression.py)
    window.add_page('Find', bar)
    window.add_button(WIDEN_ICON, lambda _window: bar.widen(), name='widen')
    window.add_button(REPLACE_ICON, lambda _window: bar.show_replace(not bar.replacing),
                      name='replace')
    for name, icon in TOGGLES:
        window.add_button(icon, lambda _window, name=name: bar.toggle(name), name=name)
    window.on('open', lambda _window: bar.begin())

    def closed(_window):
        bar.end()
        if on_close is not None and not bar.widening:
            on_close()
    window.on('close', closed)
    window.show()
    return window
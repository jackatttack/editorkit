"""query_list: a field to type a query into, and a list of what it finds.

Over the code:

    +----------------------------+
    | header: title, ⋯, buttons  |
    +----------------------------+
    | [📄] [⇄] [Aa] [W] [.*] [?] |   accessory: Controls (⋯ shows / hides)
    | [ query            ] 12 ⌂  |   accessory: Field
    | [ replace with     ] 1 All |   accessory: extra rows (optional)
    | Documents › projects › …   |   accessory: Path (optional)
    +----------------------------+
    | heading                    |   page: Results, or any tile given as
    |    12  a matching line     |   body (Search gives a Code tile)
    +----------------------------+

In the keyboard's place (compact): one job on screen, the rest a tap away.

    +----------------------------+
    | header                     |
    | def · in deck · 133      ▾ |   accessory: Bar (tap: unfold)
    +----------------------------+
    | the body, as tall as it    |
    | can be                     |
    +----------------------------+

The field, extra rows and path fold into the Bar when the window drops into
the keyboard's place and unfold when it leaves (or the Bar is tapped); rows
the tool had hidden stay hidden. ⋯ and its Controls row come from
layouts.Accessory, shared with browser. summary() gives the Bar's words.

Used by: Search (deck; also its Find mode). Fits anything that turns a
typed query into a list to pick from: symbols, commands, files.

    view = layouts.query_list(window, 'Search code', on_change=typed,
                              controls=True, body=code, path=path,
                              rows=[replace_field], summary=lambda: 'def · 12')
    view.field, view.body, view.controls, view.top.set_visible(row, True)
"""
from .. import native
from ..job import Job
from .accessory import Accessory


# --- Settings -------------------------------------------------------------

SLOW_SEARCH_DELAY = 0.3       # a pause in typing before slow sources are asked
NOTHING_FOUND = 'Nothing found'


class QueryList:
    """The tiles of a query_list, folding into a Bar in the keyboard's place."""

    def __init__(self, window, placeholder, on_change, on_return, on_pick, page,
                 controls, help_intro, body, path, rows, summary, compact_in_dock,
                 sources=None, rows_above=()):
        self.window = window
        self.summary = summary
        self.compact_in_dock = compact_in_dock
        self.compact = False
        self.last_place = None
        self.shown_before = {}            # tile -> shown, while folded

        # Sources (ROADMAP F): the field asks each one as you type; the
        # tool's own on_change still runs after.
        self.sources = list(sources or ())
        self.user_on_change = on_change
        self.job = None
        if any(getattr(source, 'slow', False) for source in self.sources):
            self.job = Job(window, self._search_slow, on_items=self._slow_arrived,
                           on_done=self._slow_done)
        self.field = native.Field(window, placeholder,
                                 on_change=self.typed if self.sources else on_change,
                                 on_return=on_return)
        self.body = body if body is not None else native.Results(window, on_pick=on_pick)
        self.results = self.body
        self.path = path
        self.rows = list(rows)
        self.rows_above = list(rows_above)
        self.controls = native.Controls(window, intro=help_intro) if controls else None
        self.bar = native.Bar(window, on_tap=lambda bar: self.set_compact(False))
        self.bar.hidden = True

        stack = ([self.bar] + self.rows_above + [self.field] + self.rows
                 + ([path] if path is not None else []))
        self.accessory = Accessory(window, stack, self.controls)
        self.top = self.accessory.column
        window.add_page(page, self.body)
        self.field.every(self.watch)      # the field is ticked even while hidden
        if self.sources:
            self.search_again()           # an empty field lists everything

    def toggle_controls(self):
        self.accessory.toggle_controls()

    # --- Sources ----------------------------------------------------------

    def typed(self, *details):
        self.search_again()
        if self.user_on_change:
            self.user_on_change(*details)

    def search_again(self):
        """Ask every source for the field's text: quick ones now, slow ones
        on the Job after a pause in typing. Call it when a source's items
        change (a window opened or closed)."""
        term = self.field.value()
        self.results.clear()
        quick = [source for source in self.sources if not getattr(source, 'slow', False)]
        slow = [source for source in self.sources if getattr(source, 'slow', False)]
        for source in quick:
            self._show(source, source.search(term))
        if slow:
            self.job.start_later(SLOW_SEARCH_DELAY, term, slow)
        elif not self.results.rows:
            self.results.say(NOTHING_FOUND)

    def _show(self, source, rows):
        if not rows:
            return
        if getattr(source, 'title', ''):
            self.results.heading(source.title)
        for row in rows:
            self.results.row(row.label, row.text, item=row.item, dim=row.dim)

    @staticmethod
    def _search_slow(run, term, slow):
        for source in slow:
            if run.cancelled:
                return
            run.put((source, source.search(term)))

    def _slow_arrived(self, batch):
        for source, rows in batch:
            self._show(source, rows)

    def _slow_done(self, ignored):
        if not self.results.rows:
            self.results.say(NOTHING_FOUND)

    # --- Folding ----------------------------------------------------------

    def folding(self):
        return (self.rows_above + [self.field] + self.rows
                + ([self.path] if self.path is not None else []))

    def set_compact(self, compact):
        """Fold the field, rows and path into the Bar, or unfold them as they
        were (a row the tool had hidden stays hidden)."""
        if compact == self.compact:
            return
        self.compact = compact
        self.bar.hidden = not compact
        if compact:
            self.shown_before = dict((tile, not tile.hidden) for tile in self.folding())
            for tile in self.folding():
                tile.hidden = True
            self.field.unfocus()
            self.refresh_bar()
        else:
            for tile in self.folding():
                tile.hidden = not self.shown_before.get(tile, True)
        self.top.refit()

    def refresh_bar(self):
        self.bar.set_text(self.summary() if self.summary else self.field.value())

    def watch(self, now):
        """Fold on arriving in the keyboard's place, unfold on leaving it;
        keep the Bar's words current while folded."""
        place = getattr(self.window, 'place', None)
        if place != self.last_place:
            self.last_place = place
            if self.compact_in_dock:
                self.set_compact(place == 'dock')
        if self.compact:
            self.refresh_bar()


def query_list(window, placeholder='Search', on_change=None, on_return=None,
               on_pick=None, page='Results', controls=False, help_intro='',
               body=None, path=None, rows=(), summary=None, compact_in_dock=True,
               sources=None, rows_above=(), compact_in_keyboard=None):
    """Field (with Controls behind ⋯ when controls=True, rows_above over it,
    extra rows under it, and a Path last when given) in the accessory; body,
    or a Results list, as the page. In the dock they fold into a Bar showing
    summary() (or the query). sources (editorkit.sources) fill the Results
    list as you type; on_pick(item) gets the tapped row's item.
    compact_in_keyboard is the old name for compact_in_dock."""
    if compact_in_keyboard is not None:
        compact_in_dock = compact_in_keyboard
    if sources and body is not None:
        raise ValueError('query_list: sources fill the Results list; leave body out')
    return QueryList(window, placeholder, on_change, on_return, on_pick, page,
                     controls, help_intro, body, path, rows, summary, compact_in_dock,
                     sources, rows_above)
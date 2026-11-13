"""Snippets: saved text as rendered cards, over the code.

    the group chips    tap one to show its snippets; ＋ Group adds a group
    the cards          title, a highlighted preview (fields as pills),
                       ✏️ edit and 🗑 delete (tap twice); tap the card to
                       type it at the cursor
    ＋ Snippet / ➕     a new snippet, prefilled from the editor's selection
    ⌨                  into the keyboard's place; folded there, it comes
                       back there from the tray

Built on editorkit's card kit (editorkit.cards, tiles.Cards). Editing opens
the TextBox (ek.edit_text) with the title in its name field and the live
fields as chips. Live fields work when typed: ${cursor} places the cursor;
${date}, ${time} and ${clipboard} are filled in.

The library is its own file (LIBRARY_PATH), kept by deck/snippets_core.py
(a vendored copy of the snippet keyboard's core: atomic writes and a .bak
backup). A missing library is seeded from deck/snippet_seeds.py.

    from editorkit_toolbox import snippets
    snippets.open_snippets()
"""
import os
import sys
import time

import editorkit as ek
from editorkit import clip, layouts, tiles
from editorkit.web import cards
from editorkit.web import tiles as web_tiles

from . import snippet_seeds

from . import snippets_core      # vendored: the deck needs nothing outside its folder


# --- Settings -------------------------------------------------------------

TITLE = 'Snippets'
EMOJI = '🧩'
WINDOW_KEY = 'deck-snippets'
LIBRARY_PATH = os.path.expanduser('~/Documents/.editorkit/snippets/library.json')
CONFIRM_SECONDS = 3.0            # a second 🗑 within this deletes
FIELD_CHIPS = ('${cursor}', '${date}', '${time}', '${clipboard}')
NEW_ICON = '➕'
START_ZOOM = 0.8                 # the first size; a pinch is remembered after that
SHOWING_PLACES = ('dock', 'panel', 'console')   # places worth going back to
FOLDED_PLACES = ('tray', 'pin', 'hidden')       # places it comes back from


# --- The page -------------------------------------------------------------

def library_page(library, group_id, armed_id):
    """The group chips and the chosen group's cards. Items: ('group', id),
    ('insert', id), ('edit', id), ('delete', id), ('new', None) and
    ('new_group', None)."""
    page = cards.Page()
    chips = [cards.Chip(column['name'], item=('group', column['id']),
                        count=len(column['snippets']), colour=column['colour'],
                        on=column['id'] == group_id)
             for column in library.columns]
    chips.append(cards.Chip('＋ Group', item=('new_group', None), dashed=True))
    page.chips(chips)
    column = next((column for column in library.columns if column['id'] == group_id),
                  library.columns[0])
    grid = []
    for snippet in column['snippets']:
        sid = snippet['id']
        armed = sid == armed_id
        grid.append(cards.Card(
            snippet['title'], item=('insert', sid), colour=column['colour'],
            body=cards.code(snippet['text']),
            actions=[cards.Action('✏️', ('edit', sid)),
                     cards.Action('Sure?' if armed else '🗑', ('delete', sid), armed=armed)]))
    grid.append(cards.Card('＋ Snippet', item=('new', None), dashed=True))
    page.grid(grid)
    return page


# --- The library ----------------------------------------------------------

def open_library(path=LIBRARY_PATH):
    """The library at path; a missing one is created from the seeds."""
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    fresh = not os.path.exists(path)
    library = snippets_core.Library(path)
    if fresh:
        first = True
        for name, colour, snippets in snippet_seeds.SEEDS:
            if first:
                column = library.columns[0]
                column['name'], column['colour'] = name, colour
                first = False
            else:
                column = library.add_column(name, colour)
            for title, text in snippets:
                library.add_snippet(column['id'], title, text)
        library.save()
    return library


# --- The tool -------------------------------------------------------------

class SnippetsTool:

    def __init__(self, window):
        self.window = window
        self.library = None
        self.problem = ''
        self.group_id = None
        self.armed_id = None         # the snippet whose 🗑 waits for a second tap
        self.armed_until = 0.0
        self.last_place = None       # where it last was, to go back from the tray
        # Starts a little zoomed out; a pinch changes it and is remembered.
        self.board = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                 zoom_key='snippets')
        window.add_page(TITLE, self.board)
        window.add_button(NEW_ICON, lambda _window: self.new_snippet(), name='new')
        window.on('place', self.place_changed)
        self.prompt = layouts.prompt(window)
        window.every(self.tick)
        self.load()
        self.refresh()

    def load(self):
        try:
            self.library = open_library()
            self.problem = ''
        except snippets_core.LibraryError as error:
            self.library = None
            self.problem = str(error)
        if self.library is not None:
            known = [column['id'] for column in self.library.columns]
            if self.group_id not in known:
                self.group_id = known[0]

    def save(self):
        try:
            self.library.save()
        except snippets_core.LibraryChangedElsewhere:
            self.load()
            self.problem = 'The library changed elsewhere and was reloaded: try again.'
        except snippets_core.LibraryError as error:
            self.problem = str(error)
        self.refresh()

    def refresh(self):
        if self.library is None or self.problem:
            self.board.say(self.problem or 'No library')
            self.problem = '' if self.library is not None else self.problem
            return
        self.board.show(library_page(self.library, self.group_id, self.armed_id))

    def place_changed(self, window, old, new, *details):
        """Remember the last real place (the dock, over the code, the
        console). Coming back from the tray or a pin when it was last in the
        keyboard's place, go back there. Only that move: leaving the dock by
        hand ('open' also fires then) must never re-dock it."""
        if old in FOLDED_PLACES and new in SHOWING_PLACES:
            if self.last_place == 'dock' and new != 'dock':
                self.window.when_still(lambda window: window.to_dock())
            return
        if new in SHOWING_PLACES:
            self.last_place = new

    def tick(self, now=None):
        if self.armed_id and time.time() > self.armed_until:
            self.armed_id = None
            self.refresh()

    # --- Taps ---------------------------------------------------------------

    def picked(self, item):
        kind, value = item
        if kind == 'group':
            self.group_id = value
            self.refresh()
        elif kind == 'insert':
            self.insert(value)
        elif kind == 'edit':
            self.edit(value)
        elif kind == 'delete':
            self.delete(value)
        elif kind == 'new':
            self.new_snippet()
        elif kind == 'new_group':
            self.prompt.ask('New group', '', on_answer=self.add_group)

    def insert(self, snippet_id):
        """Type the snippet at the cursor with its live fields filled in, the
        cursor landing on ${cursor} when it has one."""
        snippet = self.library.snippet(snippet_id)
        text, cursor = snippets_core.expand_live_fields(snippet['text'], clip.text)
        end = ek.insert(text)
        if end is not None and cursor is not None:
            ek.select(end - len(text) + cursor)

    def edit(self, snippet_id):
        snippet = self.library.snippet(snippet_id)
        ek.edit_text(snippet['text'], title='Edit snippet', name=snippet['title'],
                     name_placeholder='Title', chips=FIELD_CHIPS,
                     draft_key='snippet:' + snippet_id,
                     on_done=lambda text, name: self.update(snippet_id, text, name))

    def update(self, snippet_id, text, name):
        self.library.update_snippet(snippet_id, title=name, text=text)
        self.save()

    def new_snippet(self):
        """➕ / ＋ Snippet: a new one in the shown group, from the selection."""
        chosen = ek.selection()
        text = ''
        if chosen and chosen[0] != chosen[1]:
            text = (ek.text() or '')[chosen[0]:chosen[1]]
        ek.edit_text(text, title='New snippet', name='', name_placeholder='Title',
                     chips=FIELD_CHIPS, draft_key='snippet:new',
                     on_done=self.add_snippet)

    def add_snippet(self, text, name):
        if not text.strip() or self.library is None:
            return
        self.library.add_snippet(self.group_id, name or '', text)
        self.save()

    def add_group(self, name):
        if not (name or '').strip() or self.library is None:
            return
        column = self.library.add_column(name)
        self.group_id = column['id']
        self.save()

    def delete(self, snippet_id):
        if self.armed_id == snippet_id and time.time() <= self.armed_until:
            self.armed_id = None
            self.library.delete_snippet(snippet_id)
            self.save()
            return
        self.armed_id = snippet_id
        self.armed_until = time.time() + CONFIRM_SECONDS
        self.refresh()


def open_snippets():
    """Open Snippets over the code. Returns the tool (tool.window)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, dock_button=True)
    tool = SnippetsTool(window)
    window.show()
    return tool
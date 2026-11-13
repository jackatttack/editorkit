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

from . import snippet_library, snippet_seeds

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
SEEN_STORE = 'snippet_seeds'     # ek.store: seeds already offered, so a deleted one stays deleted
SCRATCH_ICON = '📄'              # header: open the scratch pad beside the open script
SCRATCH_NAME = 'scratch_pad.py'
SCRATCH_TEXT = '# Scratch pad: try snippets here. Snippets never overwrites it.\n'
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

def all_seeds():
    """Every seed group: the starters (snippet_seeds), then the big library
    (snippet_library). Groups with the same name are joined into one, and a
    title the group already has is skipped: the first one wins."""
    merged = []
    for name, colour, snippets in list(snippet_seeds.SEEDS) + list(snippet_library.SEEDS):
        group = next((group for group in merged if group[0] == name), None)
        if group is None:
            group = (name, colour, [])
            merged.append(group)
        titles = set(title for title, _ in group[2])
        for title, text in snippets:
            if title not in titles:
                group[2].append((title, text))
                titles.add(title)
    return merged


def seeds_to_add(columns, seeds, offered):
    """([(group, colour, title, text)] to add, every key now offered).

    Each seed is offered once, keyed 'group/title': one you delete stays
    deleted, and one already in that group (same title) is never doubled.
    New seeds in a later release reach libraries that already exist."""
    have = set((column['name'], snippet['title'])
               for column in columns for snippet in column['snippets'])
    to_add, keys = [], list(offered)
    for name, colour, snippets in seeds:
        for title, text in snippets:
            key = '%s/%s' % (name, title)
            if key in keys:
                continue
            keys.append(key)
            if (name, title) not in have:
                to_add.append((name, colour, title, text))
    return to_add, keys


def open_library(path=LIBRARY_PATH):
    """The library at path, created if missing, with every seed it has not
    been offered yet added (seeds_to_add)."""
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    fresh = not os.path.exists(path)
    library = snippets_core.Library(path)
    memory = ek.store(SEEN_STORE)
    to_add, keys = seeds_to_add(library.columns, all_seeds(),
                                [] if fresh else memory.get('offered', []))
    if to_add:
        if fresh and library.columns and not library.columns[0]['snippets']:
            first = library.columns[0]               # a new library's empty first group
            first['name'], first['colour'] = to_add[0][0], to_add[0][1]
        by_name = dict((column['name'], column) for column in library.columns)
        for name, colour, title, text in to_add:
            if name not in by_name:
                by_name[name] = library.add_column(name, colour)
            library.add_snippet(by_name[name]['id'], title, text)
        library.save()
    memory['offered'] = keys
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
        window.add_button(SCRATCH_ICON, lambda _window: self.open_scratch_pad(), name='scratch')
        window.on('place', self.place_changed)
        self.prompt = layouts.prompt(window)
        window.every(self.tick)
        self.load()
        self.refresh()

    def open_scratch_pad(self):
        """📄: scratch_pad.py beside the open script (in Documents when none is
        open), made the first time and never overwritten, opened in the editor.
        Snippets stays up, ready to type into it."""
        current = ek.current_file()
        folder = os.path.dirname(current) if current else os.path.expanduser('~/Documents')
        path = os.path.join(folder, SCRATCH_NAME)
        if not os.path.exists(path):
            try:
                with open(path, 'x', encoding='utf-8') as handle:
                    handle.write(SCRATCH_TEXT)
            except OSError as problem:
                print('Snippets could not make a scratch pad: %s' % problem)
                return
        ek.open_file(path)

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
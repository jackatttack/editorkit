"""Search: find code across files and open a hit with one tap.

Built from tiles (layouts.query_list): controls behind ⋯ (with ? help), the
query, the folder path (tap a folder to search there), and the hits as code
(tiles.Code: syntax colours, line numbers, matches marked, context around
them). ⌂ goes back to the open file's folder. Dragging the results puts the
keyboard away; tap the field to bring it back.

A scan runs on a thread: it reads each matching file once and builds that
file's section of HTML, then hands it over. The code tile's clock adds the
sections to the page, so the ui is only touched on the main thread.

    from editorkit_toolbox import search
    search.open_search()
"""
import os
import json
import re
from collections import namedtuple
import threading
import time

import editorkit as ek
from editorkit import browse, files, layouts, matches, tiles
from editorkit.web import cards, codeview
from editorkit.web import tiles as web_tiles
from editorkit.tiles.chips import Chips

from . import filecards, files_page


# --- Settings -------------------------------------------------------------

TITLE = 'Search files'
EMOJI = '🔎'
WINDOW_KEY = 'deck-search'
TYPING_PAUSE = 0.35          # seconds after the last keystroke before searching
MIN_NAME_LETTERS = 2         # file names are searched from this many characters...
MIN_CODE_LETTERS = 3         # ...code from this many (two letters match almost every line)

CONTEXT_STEPS = (0, 2, 5)    # lines around each hit, stepped by the ± control
DEFAULT_CONTEXT = 2
DOCUMENTS = os.path.expanduser('~/Documents')

# After a tap on a row: 'stay' (the window stays where it is), 'dock'
# (drop into the keyboard's place) or 'minimise' (fold to the pin).
AFTER_PICK = 'stay'
DEBUG = False                # True: print each tap and what happened to the console


# Controls row: (attribute, icon, help), in order.
SWITCHES = (
    ('case_sensitive', 'Aa', 'Match capitals exactly: Board will not find board.'),
    ('whole_word', 'W', 'Whole words only: board will not find keyboard.'),
    ('regex', '.*', 'Read the query as a regular expression, e.g. def \\w+_board.'),
)
CONTEXT_HELP = ('Lines shown around each hit: tap to step through 0, 2 and 5. '
                'Every line opens at its own place in the file when tapped.')
FIND_TITLE = 'Find'
FILE_ICON = '📄'
REPLACE_ICON = '⇄'
WINDOW_ICON = '📜'
NAMES_LABEL = 'Names'        # chip: find files by name
CODE_LABEL = 'Code'          # chip: find text inside files
HERE_LABEL = '⌂'             # chip: scope back to the open file's folder
MAX_NAME_HITS = 40           # the Files named section shows at most this many
SCOPE_ZOOM = 0.8             # the folder picker's first size; a pinch is remembered
COMPACT_LABEL = '⤡ Script'   # field button: this term in the Find bar on the open script
COMPACT_WIDTH = 100
CONSOLE_ICON = '📟'          # header: these results as a card in the Console
# Name cards are the deck's file cards: filecards.py decides their look.
NAME_PREVIEW_LINES = filecards.PREVIEW_LINES
NAME_CARD_WIDTH = filecards.CARD_WIDTH
PREVIEW_EXTENSIONS = filecards.PREVIEW_EXTENSIONS

# The results page also draws name cards: the card kit's look, without its
# full-width page rule (code rows keep scrolling sideways); the cards sit in
# a block as wide as the window instead.
RESULTS_CSS = (cards.CSS.replace('#results { width: auto; min-width: 0; }', '')
               + filecards.CSS + """
.fx-names { width: calc(100vw - 20px); }
""")
ALL_TITLE = 'All'
CONFIRM_TITLE = 'Sure?'       # All across files asks first...
CONFIRM_SECONDS = 4           # ...and a second tap must come this soon
TEXT_CHECK_SECONDS = 0.5     # This file: how often to notice edits to the script
FILE_HELP = ('This file: search only the open script, unsaved edits included. '
             'Results follow your edits. Turns on by itself for Replace.')
REPLACE_HELP = ('Replace: shows a second field. Matches show what they would '
                'become (old struck through, new beside it). 1 replaces the match '
                'you last tapped (or the first), All replaces every one. With .* '
                'on, \\1 uses a group. This file only.')
HELP_INTRO = ('Tap a control to see what it does. Under the field: Names finds '
              'files by name (every word, any order), Code finds text inside '
              'files; one is always on. "in … ▾" picks the folder to search, '
              '⌂ goes back to the open file\'s folder. In the results, tap a '
              'row to open it in the editor at that place, or 📜 to open it '
              'in a script window. With ⇄ Replace on, a tap picks the match '
              'Replace acts on; All swaps every one. Tap ? or this card to '
              'finish.')


def folder_name(folder):
    """The folder as messages name it: relative to Documents."""
    relative = os.path.relpath(folder, DOCUMENTS)
    if relative == '.':
        return 'Documents'
    if relative.startswith('..'):
        return os.path.basename(folder)
    return relative


def same_file(first, second):
    return bool(first) and os.path.realpath(first) == os.path.realpath(second)


def read_exact(path):
    """A file's text exactly as stored (line endings kept), or None if it
    cannot be read as UTF-8."""
    try:
        with open(path, encoding='utf-8', newline='') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def write_exact(path, text):
    """Write text whole: into a temporary file beside it, then over it in
    one step, so a failure never leaves half a file."""
    temporary = path + '.search-replace.tmp'
    with open(temporary, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    os.replace(temporary, path)


# One match: the file, its 1-based line and its columns. Rows and matches
# on the page carry Hits as their items (codeview.file_section).
Hit = namedtuple('Hit', 'path line start end')

# 📜 at the start of a hit's row: that Hit, to open in a script window. Its
# own type, so ◀ ▶, ringing and Replace never take it for a match.
ViewHit = namedtuple('ViewHit', 'hit')

# A file found by its name: a tap opens it in the editor.
NameHit = namedtuple('NameHit', 'path')


def name_matches(name, term, case_sensitive=False):
    """Every word of term appears somewhere in name, in any order."""
    words = term.split()
    if not case_sensitive:
        name, words = name.casefold(), [word.casefold() for word in words]
    return bool(words) and all(word in name for word in words)


def files_named(term, scope, case_sensitive=False, limit=MAX_NAME_HITS):
    """Files under scope whose names match term, best first: names starting
    with the first word, then shallower files, then by name. Skips what
    Search skips (hidden, archives, site-packages). Returns (paths, more),
    more being True when the limit cut the list."""
    words = term.split()
    first = words[0] if words else ''
    first = first if case_sensitive else first.casefold()
    found = []
    for folder, folder_names, file_names in os.walk(scope):
        folder_names[:] = sorted(name for name in folder_names if not files.skip_folder(name))
        relative = os.path.relpath(folder, scope)
        depth = 0 if relative == '.' else relative.count(os.sep) + 1
        for name in file_names:
            if name.startswith('.') or not name_matches(name, term, case_sensitive):
                continue
            key = name if case_sensitive else name.casefold()
            found.append((not key.startswith(first), depth, key, os.path.join(folder, name)))
    found.sort()
    return [entry[3] for entry in found[:limit]], len(found) > limit


def names_section(section, term, paths, scope, more=False, heading=True):
    """The Files named section: each file as the deck's file card
    (filecards.file_card) with its folder under scope. A card gives its
    NameHit (open in the editor); 📜 its ViewHit (a script window).
    heading=False leaves out the section's own heading (the hub's Find has
    its own header). Pure, so it runs on the scan thread."""
    page = cards.Page(section)
    if heading:
        page.heading('Files named “%s”%s' % (term, ' (first %d)' % len(paths) if more else ''))
    grid = [filecards.file_card(path, NameHit(path), ViewHit(Hit(path, 1, 0, 0)),
                                where=os.path.relpath(os.path.dirname(path), scope))
            for path in paths]
    page.grid(grid, min_width=filecards.CARD_WIDTH)
    html, items = page.section()
    return '<div class="fx-names">%s</div>' % html, items


def hits_in(path, marks):
    """Every match in marks as a Hit, in the order the page shows them."""
    return [Hit(path, number, mark[0], mark[1])
            for number in sorted(marks) for mark in sorted(marks[number])]


def section_for(section, label, path, text, marks, context, python):
    """A file's part of the results: a tap on a match gives its Hit; a tap
    on a line gives the line's first match, or (a context line) the line."""
    def line_item(number, line_marks):
        if line_marks:
            return Hit(path, number, line_marks[0][0], line_marks[0][1])
        return Hit(path, number, 0, 0)

    def mark_item(number, mark):
        return Hit(path, number, mark[0], mark[1])

    def view_item(number, line_marks):
        return ViewHit(Hit(path, number, line_marks[0][0], line_marks[0][1]))
    return codeview.file_section(section, label, text, marks, context, python=python,
                                 line_item=line_item, mark_item=mark_item,
                                 row_button=(WINDOW_ICON, view_item))


def log(*parts):
    if DEBUG:
        print('[search]', *parts)


def context_icon(lines):
    return '±%d' % lines


class SearchTool:

    def __init__(self, window):
        self.window = window
        self.case_sensitive = False
        self.whole_word = False
        self.regex = False
        self.context = DEFAULT_CONTEXT
        self.scope = DOCUMENTS
        self.in_file = False         # This file: search the open script itself
        self.search_names = False    # Names chip: find files by name
        self.search_code = True      # Code chip: find text inside files
        self.name_count = 0          # files in the Files named section
        self.replacing = False       # the replace row is showing
        self.hit_list = []           # every match as a Hit, in the order shown
        self.position = -1           # the match ◀ ▶ are on (-1: none yet)
        self.keep_position = None    # after a Replace: carry on from here
        self.seen_text = None        # (length, hash) of the open script last searched
        self.opened = False
        self.paths = []              # each section's file, by index (rows name it)
        self.scanning = False
        self.capped = False
        self.count = 0               # matching lines on the page
        self.pending_search = None   # a win.after waiting to search again
        self.start_scope = None      # open_search(scope=): the first scope, not the open file's folder
        self.opener = ek.Opener(window)
        self.scan_job = ek.Job(window, self.scan, on_items=self.sections_arrived,
                               on_done=self.scan_done, on_error=self.scan_failed)

        self.code = web_tiles.Code(window, on_pick=self.picked, on_scroll=self.dragged,
                               extra_css=RESULTS_CSS)
        # Under the field: what to search (Names, Code) and where (scope, ⌂).
        self.chips = Chips(window)
        self.chips.add('search_names', NAMES_LABEL, self.toggle_kind)
        self.chips.add('search_code', CODE_LABEL, self.toggle_kind, on=True)
        self.chips.add('scope', 'in Documents ▾', lambda name: self.choose_scope())
        self.chips.add('here', HERE_LABEL, lambda name: self.scope_to_file())
        # The scope chip's folder picker: Files' tiles, as a sheet (made on first use).
        self.scope_sheet = None
        self.replace_field = tiles.Field(window, 'Replace with', on_change=self.typed,
                                         on_return=self.typed)
        self.replace_field.add_button('Replace', self.replace_one, width=84)
        self.all_button = self.replace_field.add_button(ALL_TITLE, self.replace_all, width=52)
        self.confirm_until = None         # across files: a second All before this applies
        self.replace_field.hidden = True
        self.view = layouts.query_list(window, 'Search', on_change=self.typed,
                                       on_return=self.typed, controls=True,
                                       help_intro=HELP_INTRO, body=self.code,
                                       rows=[self.chips, self.replace_field],
                                       summary=self.summary)
        # The field has its row to itself: ◀ ▶ gave way to taps on the
        # results, 📜 sits on every row, ⌂ is a chip, ⇄ is behind ⋯.
        self.field, self.controls = self.view.field, self.view.controls
        # Compact mode sits on the field's own row: always in reach.
        self.field.add_button(COMPACT_LABEL, lambda field: self.to_compact(),
                              width=COMPACT_WIDTH)
        window.add_button(CONSOLE_ICON, lambda _window: self.send_to_console(), 'console')
        self.controls.add('file', FILE_ICON, self.toggle_file, FILE_HELP)
        self.controls.add('replace', REPLACE_ICON, self.toggle_replace, REPLACE_HELP)
        for name, icon, about in SWITCHES:
            self.controls.add(name, icon, self.toggle, about)
        self.controls.add('context', context_icon(self.context), self.next_context,
                          CONTEXT_HELP)
        self.controls.set_on('context', self.context > 0)
        window.on('open', lambda _window: self.begin())
        window.on('close', lambda _window: self.stop())
        window.on('text', self.script_changed)
        window.on('file', self.script_changed)

    # --- Opening ----------------------------------------------------------

    def begin(self):
        """On open: the first time, scope to the open file's folder and
        prefill with a one-line selection; every time, focus the field."""
        if not self.opened:
            self.opened = True
            chosen = ek.selection()
            if chosen and chosen[1] > chosen[0]:
                picked = ek.text()[chosen[0]:chosen[1]]
                if picked and '\n' not in picked and not self.field.value():
                    self.field.set_value(picked)
            if self.start_scope:
                self.set_scope(self.start_scope)
            else:
                self.scope_to_file()
        if self.window.place != 'dock':
            self.field.focus()

    def stop(self):
        self.scan_job.cancel()
        if self.pending_search is not None:
            self.pending_search.stop()

    # --- Scope ------------------------------------------------------------

    def set_scope(self, folder):
        self.scope = folder
        self.chips.set_label('scope', 'in %s ▾' % (os.path.basename(folder) or folder))
        self.search_now()

    def scope_to_file(self, field=None):
        path = ek.current_file()
        self.set_scope(os.path.dirname(path) if path else DOCUMENTS)

    def choose_scope(self):
        """The scope chip: a sheet of folder tiles like Files' (tap a tile
        to go in, a chip to go up), with 'Search in' to pick and Cancel."""
        self.field.unfocus()
        if self.scope_sheet is None:
            self.scope_sheet = web_tiles.Cards(self.window, on_pick=self.scope_picked,
                                           zoom=SCOPE_ZOOM, zoom_key='search-scope',
                                           extra_css=files_page.CSS)
            # Opaque, or the results show through the sheet.
            self.scope_sheet.background_color = self.window.palette.panel
        self.browse_scope(self.scope)
        self.window.show_sheet(self.scope_sheet)

    def send_to_console(self):
        """📟: the results showing now as a card in the Console; taps there
        open the hits as they do here."""
        html = ''.join(self.code.shown_html)
        term = self.field.value()
        if not term or not html.strip():
            return
        from . import console
        count = len(self.hit_list) + self.name_count
        console.show((html, dict(self.code.items)),
                     title='Search · %s · %d' % (term, count))

    def to_compact(self):
        """⤡ Script: this term in the Find bar on the open script; Search
        closes (⤢ in the bar comes back here)."""
        term = self.field.value()
        self.window.close()
        from . import find
        find.open_find(term=term)

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

    def picked_folder(self, entry):
        self.set_scope(entry.path)

    # --- Controls ---------------------------------------------------------

    def toggle(self, name):
        setattr(self, name, not getattr(self, name))
        self.controls.set_on(name, getattr(self, name))
        self.search_now()

    def toggle_kind(self, name):
        """Names or Code chip: one of them always stays on."""
        other = 'search_code' if name == 'search_names' else 'search_names'
        if getattr(self, name) and not getattr(self, other):
            return
        setattr(self, name, not getattr(self, name))
        self.chips.set_on(name, getattr(self, name))
        self.search_now()

    def set_kinds(self, names, code):
        self.search_names, self.search_code = names, code
        self.chips.set_on('search_names', names)
        self.chips.set_on('search_code', code)

    def next_context(self, name):
        step = (CONTEXT_STEPS.index(self.context) + 1) % len(CONTEXT_STEPS)
        self.context = CONTEXT_STEPS[step]
        self.controls.set_icon('context', context_icon(self.context))
        self.controls.set_on('context', self.context > 0)
        self.search_now()

    def toggle_file(self, name=None):
        self.set_file_mode(not self.in_file)

    def set_file_mode(self, on):
        """This file (Find) or folders (Search); Replace works in both."""
        self.in_file = on
        self.controls.set_on('file', on)
        self.view.top.set_visible(self.chips, not on)
        self.window.set_title(FIND_TITLE if on else TITLE)
        self.cancel_confirm()
        self.search_now()

    def toggle_replace(self, name=None):
        self.set_replacing(not self.replacing)

    def set_replacing(self, on):
        self.replacing = on
        self.controls.set_on('replace', on)
        self.view.top.set_visible(self.replace_field, on)
        self.cancel_confirm()
        self.search_now()

    def paint(self, button, on):
        palette = self.code.palette
        button.background_color = palette.accent if on else palette.background
        button.tint_color = palette.on_accent if on else palette.text

    def dragged(self):
        self.field.unfocus()
        self.replace_field.unfocus()

    # --- Searching --------------------------------------------------------

    def typed(self, field, text):
        self.cancel_confirm()                 # what All would do has changed
        self.schedule()

    def search_now(self):
        if self.pending_search is not None:
            self.pending_search.stop()
            self.pending_search = None
        self.start()

    def start(self):
        """Stop any scan and clear the page, then search: the open script at
        once (This file), or folders as a background Job."""
        self.scan_job.cancel()
        self.paths = []
        self.hit_list = []
        keep, self.keep_position = self.keep_position, None
        self.position = -1
        self.count = 0
        self.name_count = 0
        self.scanning = self.capped = False
        self.code.set_html('')
        self.field.say('')
        term = self.field.value()
        if not term:
            self.show_count()
            return
        pattern = self.pattern_or_say()
        if pattern is None:
            return
        if self.in_file:
            self.search_open_script(pattern)
            if keep is not None and self.hit_list:
                self.position = min(keep, len(self.hit_list) - 1)
                self.goto_position()
            return
        replacement = self.replace_field.value() if self.replacing else None
        search_names = self.search_names and replacement is None
        search_code = self.search_code and len(term.strip()) >= MIN_CODE_LETTERS
        if not (search_names or search_code):
            self.code.say('Code is searched from %d characters.' % MIN_CODE_LETTERS)
            return
        self.scanning = True
        self.scan_job.start(term, self.scope, self.context,
                            (self.case_sensitive, self.whole_word, self.regex), replacement,
                            (search_names, search_code))

    def pattern_or_say(self):
        try:
            return files.make_pattern(self.field.value(), self.case_sensitive,
                                      self.whole_word, self.regex)
        except ValueError as error:
            self.code.say(str(error))
            return None

    # --- This file --------------------------------------------------------

    def search_open_script(self, pattern):
        """Every match in the open script's text (unsaved edits included),
        with replacement previews while Replace shows."""
        path = ek.current_file()
        if not path:
            self.code.say('No open script.')
            return
        text = ek.text()
        self.seen_text = (len(text), hash(text))
        replacement = self.replace_field.value() if self.replacing else None
        marks = matches.marks_in(text, pattern, replacement, self.regex)
        self.paths.append(path)
        self.count = len(marks)
        self.hit_list = hits_in(path, marks)
        if marks:
            self.code.add_section(section_for(0, os.path.basename(path), path, text, marks,
                                              self.context, path.endswith('.py')))
        self.show_count()

    @staticmethod
    def scan(run, term, scope, context, switches, replacement=None, kinds=(False, True),
             name_cards=(MAX_NAME_HITS, True)):
        """The folder scan (a Job, on its own thread, never touching ui): one
        section of HTML per file with matches, handed over as it is built.
        Returns whether it reached the cap. name_cards is (how many file-name
        cards, whether the section has its own heading). A staticmethod
        because it needs nothing from the tool: the hub's Find runs it too."""
        case_sensitive, whole_word, regex = switches
        hits = files.search(term, scope, case_sensitive=case_sensitive,
                            whole_word=whole_word, regex=regex)
        # Replace on: each file's marks come from matches.marks_in, which
        # also carries what every match would become (the preview).
        pattern = (files.make_pattern(term, case_sensitive, whole_word, regex)
                   if replacement is not None else None)
        section = {'path': None, 'text': '', 'marks': {}, 'index': 0}
        names, code = kinds
        if names:
            # Files named …: first, as section 0 (its path None marks it).
            name_limit, name_heading = name_cards
            paths, more = files_named(term, scope, case_sensitive, limit=name_limit)
            if paths:
                run.put((None, names_section(0, term, paths, scope, more, heading=name_heading),
                         len(paths), []))
                section['index'] = 1
        if not code:
            return False

        def hand_over():
            if section['path'] is None:
                return
            index = section['index']
            section['index'] += 1
            marks = section['marks']
            if pattern is not None:
                marks = matches.marks_in(section['text'], pattern, replacement, regex)
            path = section['path']
            body = section_for(index, os.path.relpath(path, scope), path, section['text'],
                               marks, context, path.endswith('.py'))
            run.put((path, body, len(marks), hits_in(path, marks)))

        total = 0
        for hit in hits:
            if run.cancelled:
                return False
            total += 1
            if hit.path != section['path']:
                hand_over()
                section.update(path=hit.path, text=files.read_text(hit.path) or '', marks={})
            section['marks'].setdefault(hit.line, []).append((hit.start, hit.end))
        hand_over()
        return total >= files.MAX_HITS

    def sections_arrived(self, items):
        """The scan's sections for this beat, in order."""
        pieces, picked = [], {}
        for path, (body, body_items), lines, targets in items:
            self.paths.append(path)
            pieces.append(body)
            picked.update(body_items)
            if path is None:
                self.name_count += lines      # the Files named section
            else:
                self.count += lines
            self.hit_list.extend(targets)
        self.code.add_section((''.join(pieces), picked))
        self.show_count()

    def scan_done(self, capped):
        self.scanning = False
        self.capped = bool(capped)
        self.show_count()

    def replace_one(self, field=None):
        """Replace the match ◀ ▶ are on (or the first), in whichever file it
        is in, then carry on to the next one. The open script goes through
        the editor (so undo works); another file is read fresh and written
        whole."""
        pattern = self.pattern_or_say()
        if pattern is None or not self.hit_list or self.scanning:
            return
        position = self.position if self.position >= 0 else 0
        path, line, start, end = self.hit_list[position]
        replacement = self.replace_field.value()
        self.keep_position = position
        if self.in_file or self.is_open_script(path):
            spot = matches.replacement_at(ek.text(), pattern, line, start, end,
                                          replacement, self.regex)
            if spot is not None:              # None: the text moved; just search afresh
                ek.replace(*spot)
        else:
            text = read_exact(path)
            spot = None if text is None else matches.replacement_at(
                text, pattern, line, start, end, replacement, self.regex)
            if spot is not None:
                write_exact(path, text[:spot[0]] + spot[2] + text[spot[1]:])
        self.search_now()                     # the next match takes its place

    def replace_all(self, field=None):
        """Replace every match: in the open script as one edit (This file),
        or in every file the search found. Across files the first tap says
        how many and turns All into Sure?; a second tap within
        CONFIRM_SECONDS applies."""
        pattern = self.pattern_or_say()
        if pattern is None:
            return
        replacement = self.replace_field.value()
        if self.in_file:
            if not ek.current_file():
                return
            text = ek.text()
            new_text, count = matches.replace_all(text, pattern, replacement, self.regex)
            if count:
                ek.replace(0, len(text), new_text)
            self.search_now()
            return
        if self.scanning:
            self.replace_field.say('wait…')
            return
        if self.capped:
            self.code.say('Too many hits to replace them all safely: narrow the search first.')
            return
        if not self.paths:
            return
        if self.confirm_until is not None and time.time() < self.confirm_until:
            self.cancel_confirm()
            self.replace_everywhere(pattern, replacement)
            return
        self.replace_field.say('%d in %d' % (len(self.hit_list), len(self.paths)))
        self.all_button.title = CONFIRM_TITLE
        self.paint(self.all_button, True)
        self.confirm_until = time.time() + CONFIRM_SECONDS
        self.window.after(CONFIRM_SECONDS,
                          lambda now: self.cancel_confirm() if self.confirm_until else None)

    def cancel_confirm(self):
        """All back to plain All, with no replace waiting."""
        if self.confirm_until is None:
            return
        self.confirm_until = None
        self.all_button.title = ALL_TITLE
        self.paint(self.all_button, False)
        self.replace_field.say('')

    def replace_everywhere(self, pattern, replacement):
        """Replace in every file the search found. Each file is read again
        now, never written from what the scan saw. The open script goes
        through the editor as one undoable edit; other files are written
        whole (write_exact). Files that cannot be read or written are
        skipped, counted in the note and listed in the console."""
        changed, failed = 0, []
        for path in list(self.paths):
            if self.is_open_script(path):
                text = ek.text()
                new_text, count = matches.replace_all(text, pattern, replacement, self.regex)
                if count:
                    ek.replace(0, len(text), new_text)
            else:
                text = read_exact(path)
                if text is None:
                    failed.append(path)
                    continue
                new_text, count = matches.replace_all(text, pattern, replacement, self.regex)
                if count:
                    try:
                        write_exact(path, new_text)
                    except (IOError, OSError):
                        failed.append(path)
                        continue
            if count:
                changed += 1
        self.search_now()
        if failed:
            print('Search: replace skipped %d file(s):\n  %s' % (len(failed), '\n  '.join(failed)))
            self.replace_field.say('✓%d ✗%d' % (changed, len(failed)))
        else:
            self.replace_field.say('✓ %d' % changed)

    def is_open_script(self, path):
        current = ek.current_file()
        return bool(current) and os.path.realpath(path) == os.path.realpath(current)

    def schedule(self, seconds=TYPING_PAUSE):
        """Search again after a quiet spell (typing, edits); a newer call
        moves it on."""
        if self.pending_search is not None:
            self.pending_search.stop()
        self.pending_search = self.window.after(seconds, lambda now: self.search_now())

    def script_changed(self, window, old, new):
        """The editor's text or file changed (win.on): This file searches
        again, unless the change is the echo of our own Replace."""
        if not self.in_file:
            return
        text = ek.text()
        if (len(text), hash(text)) != self.seen_text:
            self.schedule()

    def scan_failed(self, report):
        self.scanning = False
        last = report.strip().splitlines()[-1] if report.strip() else 'unknown error'
        self.code.say('Search failed: %s' % last)

    def show_count(self):
        where = self.where()
        total = len(self.hit_list) + self.name_count
        if not self.field.value():
            self.field.say('')
            self.code.say('Type to search %s' % where)
        elif self.scanning:
            self.field.say('%d…' % total)
        elif total == 0:
            self.field.say('')
            self.code.say('No matches in %s' % where)
        elif self.position >= 0:
            self.field.say('%d/%d' % (self.position + 1, total))
        else:
            self.field.say('%d%s' % (total, '+' if self.capped else ''))

    def step(self, delta):
        """◀ ▶: the previous or next match, selected in the code and marked
        in the results."""
        if not self.hit_list:
            return
        if self.position < 0:
            self.position = 0 if delta > 0 else len(self.hit_list) - 1
        else:
            self.position = (self.position + delta) % len(self.hit_list)
        self.goto_position()

    def goto_position(self):
        hit = self.hit_list[self.position]
        self.field.unfocus()
        self.replace_field.unfocus()
        self.opener.go(hit.path, hit.line, hit.start, hit.end)
        self.code.set_current(hit)
        self.show_count()

    def where(self):
        if self.in_file:
            return os.path.basename(ek.current_file() or '') or 'the open script'
        return folder_name(self.scope)

    def summary(self):
        """The folded bar's words: query · in where · count."""
        term = self.field.value() or 'nothing yet'
        count = '%d%s' % (self.count, '…' if self.scanning else ('+' if self.capped else ''))
        return '🔎 %s  ·  in %s  ·  %s' % (term, self.where(), count)

    # --- Opening a row ----------------------------------------------------

    def go(self, payload):
        """Old string taps ('file/line/start/end'), for callers from before
        ROADMAP G."""
        try:
            index, line, start, end = (int(part) for part in payload.split('/'))
        except ValueError:
            return
        if 0 <= index < len(self.paths):
            self.picked(Hit(self.paths[index], line, start, end))

    def picked(self, hit):
        """A tapped match or line (a Hit): make it the match ◀ ▶ and Replace
        are on, then open it there; move the window out of the code's way if
        AFTER_PICK says so. A context line's Hit just opens that line."""
        log('picked', hit)
        if isinstance(hit, ViewHit):
            self.view_hit(hit.hit)
            return
        if isinstance(hit, NameHit):
            self.field.unfocus()
            self.opener.go(hit.path)
            return
        if hit in self.hit_list:
            self.position = self.hit_list.index(hit)
        else:
            same_line = [number for number, known in enumerate(self.hit_list)
                         if known[:2] == hit[:2]]
            if same_line:
                self.position = same_line[0]
        if self.replacing:
            # Replace mode: a tap picks the hit Replace acts on. This file
            # also selects it in the code; across files it is only marked,
            # so a tap never switches the tab.
            if self.in_file:
                self.goto_position()
            else:
                self.code.set_current(hit)
                self.show_count()
            return
        self.field.unfocus()
        self.replace_field.unfocus()
        self.opener.go(hit.path, hit.line, hit.start, hit.end)
        self.show_count()
        if AFTER_PICK == 'dock' and self.window.place != 'dock':
            self.window.when_still(lambda window: window.to_dock())
        elif AFTER_PICK == 'minimise':
            self.window.when_still(lambda window: window.minimise())

    def view_hit(self, hit):
        """📜 on a row: that file in a script window at the hit's line; the
        hit becomes the one ◀ ▶ are on."""
        if hit in self.hit_list:
            self.position = self.hit_list.index(hit)
            self.code.set_current(hit)
            self.show_count()
        from . import scriptview
        scriptview.open_script_window(hit.path, hit.line)

    def open_as_window(self, field=None):
        """📜: the match ◀ ▶ are on (or the first) in a script window, at its
        line."""
        if not self.hit_list:
            return
        if 0 <= self.position < len(self.hit_list):
            hit = self.hit_list[self.position]
        else:
            hit = self.hit_list[0]
        from . import scriptview
        scriptview.open_script_window(hit.path, hit.line)




def open_search(find=False, scope=None, names=False, term=None):
    """Open Search over the code; find=True opens it in This file mode (Find);
    scope= searches that folder first instead of the open file's; names=True
    turns the Names chip on too (Files' 🔍); term= fills the field (Find's ⤢),
    winning over the editor's selection. Returns the tool (its window is
    tool.window)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = SearchTool(window)
    tool.start_scope = scope
    tool.set_kinds(names, True)
    if term:
        tool.field.set_value(term)
    if find:
        tool.set_file_mode(True)
    window.show()
    return tool
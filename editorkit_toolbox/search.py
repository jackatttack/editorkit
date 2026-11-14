"""Find's engine: search file names and code across a folder.

The hub's Find is Toolbox's one search across files (the hub's Find page,
Files' 🔍, and ⤢ in Find in script all open it); this module is what it
runs. scan() runs on a Job thread: it reads each matching file once, builds
that file's section of HTML (codeview.file_section) and hands it over; the
hub adds the sections on its clock, so the ui is only touched on the main
thread. Everything here is pure.
"""
import os
from collections import namedtuple

from editorkit import files, matches
from editorkit.web import cards, codeview

from . import filecards


# --- Settings ---------------------------------------------------------------------

TYPING_PAUSE = 0.35          # seconds after the last keystroke before searching
MIN_NAME_LETTERS = 2         # file names are searched from this many characters...
MIN_CODE_LETTERS = 3         # ...code from this many (two letters match almost every line)
DEFAULT_CONTEXT = 2          # lines shown around each hit
MAX_NAME_HITS = 40           # the Files named section shows at most this many
SCOPE_ZOOM = 0.8             # the folder picker's first size; a pinch is remembered
WINDOW_ICON = '📜'           # on a hit's row: open that file in a script window

# The results page also draws name cards: the card kit's look, without its
# full-width page rule (code rows keep scrolling sideways); the cards sit in
# a block as wide as the window instead.
RESULTS_CSS = (cards.CSS.replace('#results { width: auto; min-width: 0; }', '')
               + filecards.CSS + """
.fx-names { width: calc(100vw - 20px); }
""")


# --- What a tap hands back ----------------------------------------------------------

# One match: the file, its 1-based line and its columns. Rows and matches
# on the page carry Hits as their items (codeview.file_section).
Hit = namedtuple('Hit', 'path line start end')

# 📜 at the start of a hit's row: that Hit, to open in a script window. Its
# own type, so stepping, ringing and Replace never take it for a match.
ViewHit = namedtuple('ViewHit', 'hit')

# A file found by its name: a tap opens it in the editor.
NameHit = namedtuple('NameHit', 'path')


# --- File names -------------------------------------------------------------------

def name_matches(name, term, case_sensitive=False):
    """Every word of term appears somewhere in name, in any order."""
    words = term.split()
    if not case_sensitive:
        name, words = name.casefold(), [word.casefold() for word in words]
    return bool(words) and all(word in name for word in words)


def files_named(term, scope, case_sensitive=False, limit=MAX_NAME_HITS):
    """Files under scope whose names match term, best first: names starting
    with the first word, then shallower files, then by name. Skips what the
    code search skips (hidden, archives, site-packages). Returns (paths,
    more), more being True when the limit cut the list."""
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
    """The Files named section: each file as Toolbox's file card
    (filecards.file_card) with its folder under scope. A card gives its
    NameHit (open in the editor); 📜 its ViewHit (a script window).
    heading=False leaves out the section's own heading (the hub's Find has
    its own header)."""
    page = cards.Page(section)
    if heading:
        page.heading('Files named “%s”%s' % (term, ' (first %d)' % len(paths) if more else ''))
    grid = [filecards.file_card(path, NameHit(path), ViewHit(Hit(path, 1, 0, 0)),
                                where=os.path.relpath(os.path.dirname(path), scope))
            for path in paths]
    page.grid(grid, min_width=filecards.CARD_WIDTH)
    html, items = page.section()
    return '<div class="fx-names">%s</div>' % html, items


# --- Code -------------------------------------------------------------------------

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


# --- The scan ---------------------------------------------------------------------

def scan(run, term, scope, context, switches, replacement=None, kinds=(False, True),
         name_cards=(MAX_NAME_HITS, True)):
    """The folder scan, as an ek.Job's work (its own thread, never touching
    ui): one section of HTML per file with matches, handed over with
    run.put as it is built. Returns whether it reached the cap.

    switches is (case_sensitive, whole_word, regex); kinds is (names, code);
    name_cards is (how many file-name cards, whether that section has its own
    heading). With a replacement, each match also shows what it would become."""
    case_sensitive, whole_word, regex = switches
    hits = files.search(term, scope, case_sensitive=case_sensitive,
                        whole_word=whole_word, regex=regex)
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
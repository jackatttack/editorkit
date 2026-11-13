"""Lesson 10: Build a tool.

Run this script. You build a TODO tool for the open script: a search over
its TODO comments (the ones at the bottom of this file), your open windows
in the same search, notes beside each TODO, a copied report and a saved
one. The last step puts it all back.
"""
import os

import editorkit as ek
from editorkit import clip, fileops, layouts, sources
from editorkit.lessons import Lesson

lesson = Lesson('Build a tool', __file__)
HERE = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS = os.path.expanduser('~/Documents')
MARK = '# TODO'
state = {}


def todo_rows():
    """[(line, words)] for every line of the open script that starts with
    a TODO comment. Read fresh on each search, so the list is always current."""
    rows = []
    for number, line in enumerate((ek.text() or '').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(MARK):
            rows.append((number, stripped[len(MARK):].strip(' :')))
    return rows


def jump(item):
    """A tapped row: a TODO goes to its line, a window comes forward."""
    if isinstance(item, tuple):
        text = ek.text() or ''
        index = sum(len(line) + 1 for line in text.split('\n')[:item[0] - 1])
        ek.select(index)
        ek.reveal(index)
    else:
        item.show()


@lesson.step('A tool you can search')
def searchable():
    """layouts.query_list(window, placeholder, sources=[...], on_pick=...)
    is a whole tool in one line: a field, and a Results list filled from
    its sources as you type. sources.ListSource searches a list, or a
    function that returns one, so it is always current.

    Try it: each TODO at the bottom of this file is a row. Type to filter;
    tap one to jump there."""
    window = ek.Window('TODOs', emoji='✅', key='lesson-todos', owner=lesson.window)
    todos = sources.ListSource('In this script', todo_rows,
                               lambda todo: sources.Row(str(todo[0]), todo[1], todo))
    layouts.query_list(window, 'Filter TODOs', sources=[todos], on_pick=jump)
    window.show()


@lesson.step('Two sources, one search')
def two_sources():
    """A search can draw on several sources, each under its own heading.
    ek.live_windows() is every window showing, so the tool can find those
    too: a tap brings one forward.

    Try it, then type a window's name."""
    window = ek.Window('TODOs', emoji='✅', key='lesson-todos', owner=lesson.window)
    todos = sources.ListSource('In this script', todo_rows,
                               lambda todo: sources.Row(str(todo[0]), todo[1], todo))
    windows = sources.ListSource('Open windows', ek.live_windows,
                                 lambda shown: sources.Row(getattr(shown, 'emoji', '') or '🪟',
                                                           getattr(shown, 'title', 'window'),
                                                           shown))
    layouts.query_list(window, 'TODOs and windows', sources=[todos, windows], on_pick=jump)
    window.show()


@lesson.step('Mark them in the code')
def mark():
    """ek.annotate(line, words, style) puts a note beside a line, and
    ek.STYLES names the styles: ok, warning, error and note. Every TODO
    gets one here, taking the styles in turn.

    Try it, then look at the TODOs at the bottom of this file."""
    styles = sorted(ek.STYLES, key=ek.STYLES.get)
    todos = todo_rows()
    for count, (line, words) in enumerate(todos):
        ek.annotate(line, words or 'TODO', style=styles[count % len(styles)])
    return 'Marked %d TODOs with %s.' % (len(todos), ', '.join(styles))


@lesson.step('Copy them, safely')
def copy_report():
    """editorkit.clip reads and writes the clipboard through iOS itself.
    Use it rather than the clipboard module in anything that runs while
    windows are open: the clipboard module can freeze Pythonista then.

    Try it, then paste somewhere."""
    report = '\n'.join('line %d: %s' % todo for todo in todo_rows())
    clip.set_text(report)
    return 'Copied %d lines.' % report.count('\n') if report else 'No TODOs found.'


@lesson.step('Save a report, never overwrite')
def save_report():
    """fileops.new_file(folder, name, text) makes a file under a free name
    (todo_report.txt, then todo_report 2.txt) and never overwrites. Its
    friends rename, duplicate, move and trash are just as careful.

    Try it twice: two reports appear beside this lesson."""
    path = fileops.new_file(HERE, 'todo_report.txt', clip.text())
    state.setdefault('reports', []).append(path)
    return 'Saved %s.' % os.path.basename(path)


@lesson.step('Put it all back')
def put_back():
    """ek.clear_annotations() takes every note away, and fileops.trash moves
    the reports into Documents/_to_delete rather than deleting them. A tool
    closes only its own windows: ek.close_windows() would close Toolbox's
    too. Done ✓ closes the lesson's.

    Try it, then Done ✓."""
    ek.clear_annotations()
    moved = 0
    for path in state.pop('reports', []):
        if os.path.exists(path):
            fileops.trash(path, DOCUMENTS)
            moved += 1
    return 'Notes cleared; %d report%s moved to _to_delete.' % (moved, '' if moved == 1 else 's')


# --- The TODOs this lesson's tool finds -------------------------------------
# TODO: give the tool a header button that copies the report
# TODO: remember the filter between runs with ek.store
# TODO: show how many TODOs there are in the window's title


lesson.run()
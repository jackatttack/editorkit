"""TODOs: every TODO comment in the open script; type to filter, tap one to
go to its line.

The finished tool from Lesson 10 (Build a tool). Run it, or put it in
Toolbox's hub: Lesson 10's Join the hub step writes its plugin file,
Documents/Toolbox/tools/todos.json, which names this file's folder, its
module and main(). ek.run_tool(main) keeps this script's names alive after
it ends, so the window's callbacks can use them.
"""
import editorkit as ek
from editorkit import layouts, sources

# --- Settings ------------------------------------------------------------------

TITLE = 'TODOs'
EMOJI = '✅'
KEY = 'example-todos'
MARK = '# TODO'               # a line starting with this is a TODO


def todo_rows():
    """[(line, words)] for every line of the open script that starts with
    MARK. Read fresh on each search, so the list is always current."""
    rows = []
    for number, line in enumerate((ek.text() or '').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(MARK):
            rows.append((number, stripped[len(MARK):].strip(' :')))
    return rows


def as_row(todo):
    return sources.Row(str(todo[0]), todo[1], todo)


def go_to(todo):
    """A tapped TODO: select the start of its line and bring it into view."""
    start, _end = ek.line_range(todo[0])
    ek.select(start)
    ek.reveal(start)


def main():
    window = ek.Window(TITLE, emoji=EMOJI, key=KEY)
    todos = sources.ListSource('In this script', todo_rows, as_row)
    layouts.query_list(window, 'Filter TODOs', sources=[todos], on_pick=go_to)
    window.show()


if __name__ == '__main__':
    ek.run_tool(main)

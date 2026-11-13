"""A line diff as codeview Rows (Quick's Replace with clipboard). Pure.

    rows, added, removed = diff_rows(old_text, new_text)
    summary(added, removed)            # '+3 lines, −1 line'

Unchanged lines around each change show as 'code' rows (CONTEXT_LINES of
them), removed lines as 'remove' (struck through), added lines as 'add'
(green), with a ⋯ note between separate changes. Numbers are the line in
the new text (the old text's for removed lines). tests/smoke_diff_rows.py.
"""
import difflib

from editorkit.web.codeview import Row


# --- Settings -------------------------------------------------------------

CONTEXT_LINES = 2
MAX_ROWS = 400                   # longer diffs are cut, with "… n more rows"


def diff_rows(old_text, new_text, context=CONTEXT_LINES, limit=MAX_ROWS):
    old, new = old_text.splitlines(), new_text.splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    rows, added, removed = [], 0, 0
    for group in matcher.get_grouped_opcodes(context):
        if rows:
            rows.append(Row('⋯', 'note'))
        for tag, old_start, old_end, new_start, new_end in group:
            if tag == 'equal':
                for offset in range(old_end - old_start):
                    rows.append(Row(old[old_start + offset], 'code', None,
                                    new_start + offset + 1))
                continue
            for index in range(old_start, old_end):
                rows.append(Row(old[index], 'remove', None, index + 1))
                removed += 1
            for index in range(new_start, new_end):
                rows.append(Row(new[index], 'add', None, index + 1))
                added += 1
    if len(rows) > limit:
        hidden = len(rows) - limit
        rows = rows[:limit] + [Row('… %d more rows' % hidden, 'note')]
    return rows, added, removed


def summary(added, removed):
    return '+%d line%s, −%d line%s' % (added, '' if added == 1 else 's',
                                       removed, '' if removed == 1 else 's')
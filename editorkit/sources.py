"""Sources: what a query_list searches.

A source is any object with:

    title           the heading over its rows ('' for none)
    search(term)    a list of Row; must be quick unless slow is True
    slow            optional; True runs search on a Job thread, after a
                    pause in typing, so it must not touch ui

Rows mirror tiles.Results.row: a short label (an emoji, a line number), the
text, the item handed to on_pick when the row is tapped, and dim for a
quieter row.

    tools = sources.ListSource('Tools', TOOLS,
                               lambda tool: sources.Row(tool['emoji'], tool['name'], tool))
    layouts.query_list(window, 'Find anything', sources=[tools], on_pick=opened)

Pure Python: no ui, no Pythonista imports, so it is tested headless.
"""
from collections import namedtuple


Row = namedtuple('Row', 'label text item dim')
Row.__new__.__defaults__ = (False,)      # dim is optional


class ListSource:
    """A source over a list. items is a list, or a function returning one
    (read again on every search, so it can change, like open windows).
    describe(item) gives the item's Row. A row matches when every typed
    word appears in its label or text, in any case; an empty term matches
    everything. At most limit rows, in the list's own order."""

    slow = False

    def __init__(self, title, items, describe, limit=50):
        self.title = title
        self.items = items
        self.describe = describe
        self.limit = limit

    def search(self, term):
        words = term.lower().split()
        found = []
        items = self.items() if callable(self.items) else self.items
        for item in items:
            row = self.describe(item)
            haystack = ('%s %s' % (row.label, row.text)).lower()
            if all(word in haystack for word in words):
                found.append(row)
                if len(found) >= self.limit:
                    break
        return found
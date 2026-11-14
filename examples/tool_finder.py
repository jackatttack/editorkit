"""Finder: search every script under a folder as you type; tap a hit to open it.

The finished tool from Lesson 5 (Work in the background): a search field,
an ek.Job that searches on a thread and cancels itself when you type again,
the hits as cards, ek.Opener to open one at its line, and ek.store to
remember the last search. Change FOLDER to search somewhere else.

ek.run_tool(main) keeps this script's names alive after it ends, so the
window's callbacks (Finder's methods) can use them.
"""
import os

import editorkit as ek
from editorkit import files, layouts
from editorkit.web import cards, tiles

# --- Settings ------------------------------------------------------------------

FOLDER = '~/Documents'          # where to search
TYPING_PAUSE = 0.35             # seconds of quiet before a search starts
HITS_SHOWN = 80                 # cards drawn at most
KEY = 'example-finder'


class Finder:

    def __init__(self):
        self.folder = os.path.expanduser(FOLDER)
        self.memory = ek.store('example_finder')
        self.hits = []
        self.window = ek.Window('Finder', emoji='🔎', key=KEY)
        self.opener = ek.Opener(self.window)
        self.board = tiles.Cards(self.window, on_pick=self.open_hit, zoom_key=KEY)
        self.job = ek.Job(self.window, self.work, on_items=self.arrived,
                          on_done=self.done, on_error=self.failed)
        layouts.query_list(self.window, 'Search your scripts', on_change=self.typed,
                           body=self.board)

    # --- Drawing ----------------------------------------------------------------

    def draw(self, note):
        page = cards.Page()
        page.note(note)
        page.grid([cards.Card('%s · %d' % (os.path.basename(hit.path), hit.line), item=hit,
                              body=cards.code(hit.text.strip(), lines=2))
                   for hit in self.hits[:HITS_SHOWN]])
        self.board.show(page)

    def open_hit(self, hit):
        self.opener.go(hit.path, hit.line)

    # --- Searching (work runs on the Job's thread; the rest on the clock) -------

    def typed(self, field, text):
        term = text.strip()
        self.memory['last_term'] = term
        del self.hits[:]
        if term:
            self.job.start_later(TYPING_PAUSE, term)
        else:
            self.job.cancel()
            self.draw('Type to search %s.' % FOLDER)

    def work(self, run, term):
        for hit in files.search(term, self.folder):
            if run.cancelled:           # you typed again: a newer search runs
                return None
            run.put(hit)
        return term

    def arrived(self, batch):
        self.hits.extend(batch)
        self.draw('Searching...')

    def done(self, term):
        if term is not None:
            self.draw('%d hits for %s' % (len(self.hits), term))

    def failed(self, error):
        self.draw('Could not search: %s' % error.strip().splitlines()[-1])


def main():
    finder = Finder()
    last = finder.memory.get('last_term')
    finder.draw('Type to search %s.%s' % (FOLDER, ' Last time: %s' % last if last else ''))
    finder.window.show()


ek.run_tool(main)

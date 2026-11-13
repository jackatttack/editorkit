"""Finder: search every script under a folder as you type; tap a hit to open it.

The finished tool from Lesson 5 (Work in the background): a search field,
an ek.Job that searches on a thread and cancels itself when you type again,
the hits as cards, ek.Opener to open one at its line, and ek.store to
remember the last search. Change FOLDER to search somewhere else.
"""
FOLDER = '~/Documents'          # where to search
TYPING_PAUSE = 0.35             # seconds of quiet before a search starts
HITS_SHOWN = 80                 # cards drawn at most


def main():
    # Pythonista clears a script's names when it ends, but this window lives
    # on: everything its callbacks use is local to main(), so they keep it.
    import os

    import editorkit as ek
    from editorkit import files, layouts
    from editorkit.web import cards, tiles

    folder_name, pause, shown = FOLDER, TYPING_PAUSE, HITS_SHOWN
    folder = os.path.expanduser(folder_name)
    memory = ek.store('example_finder')
    window = ek.Window('Finder', emoji='🔎', key='example-finder')
    opener = ek.Opener(window)
    board = tiles.Cards(window, on_pick=lambda hit: opener.go(hit.path, hit.line),
                        zoom_key='example-finder')
    hits = []

    def draw(note):
        page = cards.Page()
        page.note(note)
        page.grid([cards.Card('%s · %d' % (os.path.basename(hit.path), hit.line), item=hit,
                              body=cards.code(hit.text.strip(), lines=2))
                   for hit in hits[:shown]])
        board.show(page)

    def work(run, term):
        for hit in files.search(term, folder):
            if run.cancelled:           # you typed again: a newer search runs
                return None
            run.put(hit)
        return term

    def arrived(batch):
        hits.extend(batch)
        draw('Searching...')

    def done(term):
        if term is not None:
            draw('%d hits for %s' % (len(hits), term))

    def failed(error):
        draw('Could not search: %s' % error.strip().splitlines()[-1])

    job = ek.Job(window, work, on_items=arrived, on_done=done, on_error=failed)

    def typed(field, text):
        term = text.strip()
        memory['last_term'] = term
        del hits[:]
        if term:
            job.start_later(pause, term)
        else:
            job.cancel()
            draw('Type to search %s.' % folder_name)

    layouts.query_list(window, 'Search your scripts', on_change=typed, body=board)
    last = memory.get('last_term')
    draw('Type to search %s.%s' % (folder_name, ' Last time: %s' % last if last else ''))
    window.show()


main()
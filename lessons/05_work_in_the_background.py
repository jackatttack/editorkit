"""Lesson 5: Work in the background.

Run this script. Over its steps you build a small finder: it searches every
lesson and example for a word on a background thread, shows the hits as
cards as they arrive, opens one at its line, and remembers between runs.
"""
import os

import editorkit as ek
from editorkit import files
from editorkit.web import cards, tiles
from editorkit.lessons import Lesson

lesson = Lesson('Work in the background', __file__)
FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Toolbox: lessons, examples
SIZE = (360, 420)
HITS_SHOWN = 60
state = {}


def draw(note):
    """The finder's page: a note, then a card per hit. The card's item is
    the hit itself, so a tap hands it straight back."""
    page = cards.Page()
    page.note(note)
    page.grid([cards.Card('%s · %d' % (os.path.basename(hit.path), hit.line), item=hit,
                          body=cards.code(hit.text.strip(), lines=2))
               for hit in state['hits'][:HITS_SHOWN]])
    state['board'].show(page)


@lesson.step('A window for the hits')
def finder_window():
    """The finder: a cards board whose items will be search hits. A tap
    hands back the hit, and ek.Opener opens its file at its line, waiting
    for the tab to switch when it has to.

    Try it: an empty finder opens. The next step fills it."""
    window = ek.Window('Finder', emoji='🔎', key='lesson-finder', size=SIZE, owner=lesson.window)
    opener = ek.Opener(window)
    board = tiles.Cards(window, on_pick=lambda hit: opener.go(hit.path, hit.line),
                        zoom_key='lesson-finder')
    window.add_page('Hits', board)
    state.update(window=window, board=board, hits=[])
    draw('Nothing searched yet.')
    window.show()


@lesson.step('Search on a thread')
def search_on_a_thread():
    """Searching files takes a moment, and the screen must never freeze.
    ek.Job runs work(run, ...) on a thread; each run.put(item) arrives back
    on the window's clock, in batches, where changing views is safe.

    Try it: hits for ek.show fill in as the thread finds them. Tap one."""
    if 'board' not in state:
        return 'Try step 1 first: it opens the finder.'

    def work(run, term):
        for hit in files.search(term, FOLDER):
            if run.cancelled:          # a newer search has started
                return None
            run.put(hit)
        return term

    def arrived(hits):
        state['hits'].extend(hits)
        draw('Searching...')

    def done(term):
        if term is not None:
            draw('%d hits for %s' % (len(state['hits']), term))

    state['job'] = ek.Job(state['window'], work, on_items=arrived, on_done=done)
    state['hits'] = []
    state['job'].start('ek.show')


@lesson.step('A new search cancels the old')
def search_again():
    """start() again cancels the run before it: its run.cancelled turns
    True and anything it puts afterwards is dropped, so a stale search
    never shows. That is how search-as-you-type stays right.

    Try it: two searches start back to back, and only the second shows."""
    if 'job' not in state:
        return 'Try step 2 first: it makes the search job.'
    state['hits'] = []
    state['job'].start('def ')
    state['hits'] = []
    state['job'].start('lesson.step')
    return 'Started def, then lesson.step: the finder shows only lesson.step.'


@lesson.step('Remember between runs')
def remember():
    """ek.store(name) is a small dict that survives quitting Pythonista:
    one JSON file per name, saved shortly after each change. Assign at the
    top level (memory['key'] = value) and it saves itself.

    Try it a few times, then quit Pythonista and come back: the count goes on."""
    memory = ek.store('lesson_finder')
    memory['tries'] = memory.get('tries', 0) + 1
    return 'This step has run %d times, ever (Documents/.editorkit/store).' % memory['tries']


@lesson.step('Tidy up')
def tidy_up():
    """Stop anything still running, and forget what the lesson saved.
    Done ✓ closes the finder, because the lesson owns it.

    Try it, then Done ✓."""
    if 'job' in state:
        state.pop('job').cancel()
    memory = ek.store('lesson_finder')
    memory.pop('tries', None)
    memory.save()
    return 'Search stopped, and the saved count forgotten.'


lesson.run()
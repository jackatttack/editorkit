"""Lesson 8: The feed.

tiles.Feed is the Console's page: a history of entries, each a card. Run
this script and step through.
"""
import editorkit as ek
from editorkit.lessons import Lesson
from editorkit.web.tiles import Feed

lesson = Lesson('The feed', __file__)
state = {}                       # the feed and its window, for later steps


@lesson.step('A feed of cards')
def feed_window():
    """A Feed holds entries, newest at the end. Each is a card with a title,
    the time, and 📋 copy, ▾ fold and ✕ remove in its header.

    feed.add(title, thing) makes one. Try it, then try the card's buttons."""
    window = ek.Window('Feed', emoji='📟', key='lesson-feed', size=(360, 440))
    feed = Feed(window)
    window.add_page('Feed', feed)
    window.show()
    feed.add('Hello', 'A first entry: just some text.')
    state['window'], state['feed'] = window, feed


@lesson.step('Anything can be an entry')
def anything():
    """Entries draw whatever editorkit.render takes: text, a list of dicts as
    a table, a dict as JSON, a PIL image or matplotlib figure, an exception
    as its traceback, a file path as a preview.

    status='error' marks a card with ✗. (Needs step 1's window.)"""
    feed = state.get('feed')
    if feed is None:
        return 'Try step 1 first: it opens the feed.'
    from PIL import Image, ImageDraw
    feed.add('A table', [{'fruit': 'apple', 'count': 4}, {'fruit': 'pear', 'count': 1}])
    feed.add('A dict', {'lesson': 4, 'cards': True, 'history': 'this session'})
    picture = Image.new('RGB', (200, 80), (40, 44, 52))
    ImageDraw.Draw(picture).rectangle((20, 20, 180, 60), fill=(98, 210, 111))
    feed.add('A picture', picture)
    try:
        1 / 0
    except ZeroDivisionError as error:
        feed.add('An error', error, status='error')


@lesson.step('Streaming into an entry')
def streaming():
    """An entry can grow while you watch: entry.append(thing) adds to it in
    place (the page is not redrawn), and entry.finish(status, note) ticks it
    off with ✓, ✗ or ■.

    Here window.after() appends a line every 0.3 seconds. The Console streams
    a running script's output exactly like this."""
    feed, window = state.get('feed'), state.get('window')
    if feed is None:
        return 'Try step 1 first: it opens the feed.'
    entry = feed.add('Counting', status='running')
    numbers = iter(range(1, 11))

    def next_line(*_args):
        try:
            number = next(numbers)
        except StopIteration:
            entry.finish('done', 'counted to 10')
            return
        entry.append('%d squared is %d' % (number, number * number))
        window.after(0.3, next_line)

    next_line()


@lesson.step('Keeping history tidy')
def tidy_history():
    """Old entries can fold down to their header (▾), so the latest stays in
    view while the history stays one tap away. A feed keeps its last 50
    entries.

    From code: set entry.folded and call feed.redraw(). Try it: every entry
    but the newest folds."""
    feed = state.get('feed')
    if feed is None:
        return 'Try step 1 first: it opens the feed.'
    for entry in feed.entries[:-1]:
        entry.folded = True
    feed.redraw()
    return 'Folded %d entries.' % max(0, len(feed.entries) - 1)


lesson.run()

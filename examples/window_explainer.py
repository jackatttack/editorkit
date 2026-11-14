"""Explainer: a page that reads like Pythonista's own docs, then explainer
cards that mix words and code.

editorkit.web.prose borrows the documentation's look: headings, words with
`code` chips, signatures, code blocks that wrap, and notes. page.prose()
adds them as a full-width article; prose.article() makes a card body.
Resize the window and pinch: everything reflows.
"""

ui.view
import editorkit as ek
from editorkit.web import cards, prose

KEY = 'example-explainer'


def explainer_page():
    page = cards.Page()
    page.prose(
        prose.heading('Show anything in a window', 1),
        prose.text('`ek.show` puts a window over your code in one line. Give it text, '
                   'HTML, an image, a figure, a `ui.View` or a page of cards.'),
        prose.member(
            prose.signature('show', 'thing, title=None, key=None, on_pick=None, **options',
                            prefix='ek.', kind='function'),
            prose.text('Opens a window with one page showing **thing**. With a '
                       '`cards.Page`, `on_pick(item)` gets the item of whatever is tapped.'),
            prose.code("import editorkit as ek\n\n"
                       "ek.show('Hello from a window over your code')\n"
                       "ek.show(page, title='Colours', on_pick=print)"),
        ),
        prose.note('Showing again under the same key swaps the content in place and '
                   'leaves the window where it is, so `ek.show` can run in a loop.',
                   'Tip', 'tip'),
        prose.heading('What a page can be', 2),
        prose.terms([('str', 'Text: a short line shows big, longer text as a label.'),
                     ('HTML', 'A fragment in the theme\'s colours, or a full page.'),
                     ('ui.View', 'Any view; lay it out with `flex` or `layout()`.'),
                     ('cards.Page', 'Cards, chips and buttons; taps hand back your items.')]),
        prose.note("A tool's window outlives its script. End a tool with "
                   '`ek.run_tool(main)` so its callbacks keep their names.',
                   'Good to know', 'warning'),
        prose.heading('Explainer cards', 2),
    )
    page.grid([
        cards.Card('select', body=prose.article(
            prose.text('Select characters `start` to `end` in the open script.'),
            prose.code('ek.select(*ek.line_range(12, 14))'))),
        cards.Card('annotate', body=prose.article(
            prose.text('A note beside a line, in a style: ok, warning, error or note.'),
            prose.code("ek.annotate(12, 'Look here', style='note')"))),
        cards.Card('run_tool', body=prose.article(
            prose.text('Keeps a tool\'s names alive after its script ends.'),
            prose.code('ek.run_tool(main)'))),
    ], min_width=220)
    return page


ek.show(explainer_page(), title='Explainer', key=KEY)

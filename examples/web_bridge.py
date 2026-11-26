"""A page that talks to Python: messages with a payload, patches, ek.data.

Role: run · Part of: editorkit/examples · Entry

Tap a fruit: the page sends ekSend('picked', {...}) and Python counts it,
then patches only the tally line (tile.patch): the page does not redraw or
scroll. The fruit buttons are page-handled (ekTouch.buttons) in extra_js,
which runs after the shell, so it needs no waiting. Resize the window: the
patched tally comes back. The last line says where ek.data finds a file.
"""
import editorkit as ek
from editorkit.web import cards
from editorkit.web import tiles

ek.require('0.7.0', 'This example')

FRUIT = ('Apple', 'Pear', 'Plum', 'Fig')

# The page's own script: runs after the shell, so ekTouch and ekSend are ready.
PAGE_JS = r"""
ekTouch.buttons('data-fruit', function (node) {
  node.classList.add('picked');
  ekSend('picked', {fruit: node.getAttribute('data-fruit'), at: Date.now()});
});
"""
PAGE_CSS = """
.fruit { display: inline-block; padding: 12px 18px; margin: 4px; border-radius: 12px;
    background: var(--wash-strong); cursor: pointer; font: 17px -apple-system, sans-serif; }
.fruit.picked { box-shadow: inset 0 0 0 2px var(--accent); }
.tally { font: 600 17px -apple-system, sans-serif; margin: 12px 4px; }
"""


def main():
    window = ek.Window('Bridge', emoji='\U0001f309', key='example-bridge')
    counts = {name: 0 for name in FRUIT}
    tile = tiles.Cards(window, extra_css=PAGE_CSS, extra_js=PAGE_JS)

    def tally():
        return ' · '.join('%s %d' % (name, counts[name]) for name in FRUIT)

    def picked(data):
        counts[data['fruit']] += 1
        tile.patch('.tally', tally())

    tile.on_message('picked', picked)
    page = cards.Page()
    page.heading('Tap a fruit')
    page.parts.append(''.join('<span class="fruit" data-fruit="%s">%s</span>' % (name, name) for name in FRUIT))
    page.parts.append('<div class="tally">%s</div>' % tally())
    page.note('ek.data: library/datasets/pokemon.csv is %s' % ek.data.status('datasets/pokemon.csv'))
    tile.show(page)
    window.add_page('Bridge', tile)
    window.show()
    return window


if __name__ == '__main__':
    ek.run_tool(main)

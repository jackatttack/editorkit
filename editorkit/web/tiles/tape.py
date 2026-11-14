"""Tape: a history of entries (asked, answered) with a live draft line.

    tape = tiles.Tape(window, on_pick=picked)    # picked('input'|'output', n)
    tape.add({'input': '7÷2', 'output': '7/2', 'decimal': '3.5'})
    tape.set_draft('3+4', preview='= 7')
    entry = tape.undo()                          # takes the last entry back

Entries are dicts: input, output (may be several lines, drawn as is),
decimal and error are shown; anything else rides along for the tool. Drawn
by tapeview in a Code tile and kept scrolled to the end. Not only for
calculators: any asked-and-answered log fits (a REPL, a run log).
"""
import json

from .. import tapeview
from ...native.base import Tile
from .code import Code


class Tape(Tile):

    def __init__(self, window, on_pick=None, on_draft=None):
        Tile.__init__(self, window)
        self.on_pick = on_pick
        self.on_draft = on_draft          # a tap on the draft line (summon keys)
        self.entries = []
        self.draft = None
        self.code = Code(window, on_go=self.went, extra_css=tapeview.tape_css(self.palette),
                         dismiss_keyboard=False)
        self.add_subview(self.code)
        self.render()

    def add(self, entry):
        self.entries.append(dict(entry))
        self.render()

    def undo(self):
        if not self.entries:
            return None
        entry = self.entries.pop()
        self.render()
        return entry

    def clear(self):
        self.entries = []
        self.render()

    def set_entries(self, entries):
        self.entries = [dict(entry) for entry in entries]
        self.render()

    def set_draft(self, text, preview='', error=False):
        self.draft = {'text': text, 'preview': preview, 'error': error}
        self.render()

    def render(self):
        html = tapeview.tape_html(self.entries, self.draft)
        self.code.run('setAndEnd(%s)' % json.dumps(html))

    def went(self, payload):
        kind, _, number = payload.partition('/')
        if kind == 'draft':
            if self.on_draft:
                self.on_draft()
            return
        try:
            index = int(number)
        except ValueError:
            return
        if self.on_pick and 0 <= index < len(self.entries):
            self.on_pick(kind, index)

    def layout(self):
        self.code.frame = (0, 0, self.width, self.height)

    def tick(self, now):
        self.code.tick(now)              # the page's taps arrive through it
        Tile.tick(self, now)
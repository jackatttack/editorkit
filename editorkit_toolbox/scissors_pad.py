"""✂️ Scissors pad: select code quickly and do things with it, in the keyboard's place.

    “greet” · line 4
    ◀  ▲  ▼  ▶   ⊕  ⊖  ⟲
    📋  ✂️  📥  ▶  ⋯

The arrows have two modes (scissors_moves.mode):
    word mode    a cursor or a selection inside one line: ◀ ▶ hop to the
                 word before or after, ▲ ▼ to the word above or below
    line mode    a whole line or more: ⇧ ⇩ move the lines past their
                 neighbours, ⇤ ⇥ dedent and indent
⊕ grows the selection (word, then the line, then one more line a tap), ⊖
walks it back, ⟲ resets to the word at the cursor. Hold an arrow, ⊕ or ⊖
to repeat. 📋 copies, ✂️ cuts, 📥 pastes (several lines re-indented to fit),
▶ runs the selection (or the cursor's line) in the Console. ⋯ swaps the
row for ⧉ duplicate, # comment, 🧩 save as snippet and 📜 the script as a
window. Edits go through ek.replace as the smallest change, so Pythonista's
undo covers them.

    from editorkit_toolbox import scissors_pad
    scissors_pad.open_scissors_pad()
"""
import time
import traceback

import ui
import editorkit as ek
from editorkit import clip
from editorkit.native.base import (BUTTON_FONT, CORNER_RADIUS, RULE, WASH, Tile,
                                   palette_for, wash)

from . import console, lineops
from . import scissors_moves as moves


# --- Settings -------------------------------------------------------------

TITLE = 'Scissors'
EMOJI = '✂️'
WINDOW_KEY = 'deck-scissors-pad'
PADDING = 8
GAP = 6
READOUT_HEIGHT = 22
READOUT_FONT = ('<system>', 13)
MIN_KEY_HEIGHT = 40
MAX_KEY_HEIGHT = 46
PAD_HEIGHT = 2 * PADDING + READOUT_HEIGHT + 2 * GAP + 2 * MAX_KEY_HEIGHT   # the keys' own height
IPAD_SIZE = (440, PAD_HEIGHT + 60)     # on an iPad: a compact window over the code
IPAD_SCREEN = 700                      # a screen at least this wide on its short side is an iPad
HOLD_DELAY = 0.4             # a held key starts repeating after this long...
REPEAT_SECONDS = 0.09        # ...then repeats this often
RECHECK_SECONDS = 0.3        # how often to notice a selection made by hand
FLASH_SECONDS = 1.5          # how long "Copied 3 lines" shows
PRESSED_STRENGTH = 0.35      # a pressed key: the accent at this strength
WORD_SHOWN = 24              # a selected word is shown cut to this many characters

WORD_ARROWS = {'left': '◀', 'up': '▲', 'down': '▼', 'right': '▶'}
LINE_ARROWS = {'left': '⇤', 'up': '⇧', 'down': '⇩', 'right': '⇥'}
ROW_ONE = (('left', '◀'), ('up', '▲'), ('down', '▼'), ('right', '▶'),
           ('grow', '⊕'), ('shrink', '⊖'), ('reset', '⟲'))
ROW_TWO = (('copy', '📋'), ('cut', '✂️'), ('paste', '📥'), ('run', '▶︎'), ('snippet', '🧩'),
           ('explain', '?'), ('more', '⋯'))
MORE_ROW = (('duplicate', '⧉'), ('comment', '#'), ('view', '📜'), ('more', '↩'))
REPEATS = ('left', 'up', 'down', 'right', 'grow', 'shrink')


def clipboard_text():
    getter = getattr(clip, 'get_text', None)
    if getter is not None:
        return getter() or ''
    import clipboard
    return clipboard.get() or ''


def reveal(start, end):
    """Bring the selection into view, however this editorkit's reveal is called."""
    for args in ((start, end), (start,)):
        try:
            ek.reveal(*args)
            return
        except Exception:
            continue


# --- A key ------------------------------------------------------------------

class Key(ui.View):
    """A pad key: fires on touch down, lights while held, and (repeats=True)
    fires again and again while held, on the pad's clock."""

    def __init__(self, pad, name, label, repeats=False):
        self.pad = pad
        self.name = name
        self.repeats = repeats
        self.held_since = None
        self.next_repeat = 0.0
        self.label = ui.Label(font=BUTTON_FONT, alignment=ui.ALIGN_CENTER)
        self.label.text = label
        self.label.touch_enabled = False
        self.add_subview(self.label)
        self.corner_radius = CORNER_RADIUS
        self.border_width = 0.5
        self.multitouch_enabled = False

    def layout(self):
        self.label.frame = self.bounds

    def paint(self, palette, pressed=False):
        self.background_color = (wash(palette.accent, PRESSED_STRENGTH) if pressed
                                 else wash(palette.text, WASH))
        self.border_color = wash(palette.text, RULE)
        self.label.text_color = palette.text

    def touch_began(self, touch):
        self.paint(self.pad.palette, pressed=True)
        self.held_since = time.time()
        self.next_repeat = self.held_since + HOLD_DELAY
        self.pad.press(self.name)

    def touch_ended(self, touch):
        self.held_since = None
        self.paint(self.pad.palette)

    def repeat(self, now):
        if self.repeats and self.held_since is not None and now >= self.next_repeat:
            self.next_repeat = now + REPEAT_SECONDS
            self.pad.press(self.name)


# --- The pad ----------------------------------------------------------------

class ScissorsPad(Tile):

    def __init__(self, window):
        Tile.__init__(self, window)
        self.history = []            # selections before each ⊕, for ⊖ to walk back
        self.seen = None             # the editor's selection as last read or set
        self.more = False            # row two shows the ⋯ actions
        self.flash_until = 0.0
        self.next_check = 0.0
        self.readout = ui.Label(font=READOUT_FONT)
        self.add_subview(self.readout)
        self.row_one = [self.make_key(name, label) for name, label in ROW_ONE]
        self.arrow_keys = dict((key.name, key) for key in self.row_one if key.name in WORD_ARROWS)
        self.row_two = [self.make_key(name, label) for name, label in ROW_TWO]
        self.more_row = [self.make_key(name, label) for name, label in MORE_ROW]
        self.restyle()
        self.every(self.watch)

    def make_key(self, name, label):
        key = Key(self, name, label, repeats=name in REPEATS)
        self.add_subview(key)
        return key

    def restyle(self):
        self.palette = palette_for(self.window)
        for key in self.row_one + self.row_two + self.more_row:
            key.paint(self.palette)
        self.readout.text_color = self.palette.dim

    def layout(self):
        self.readout.frame = (PADDING + 2, PADDING, self.width - 2 * PADDING, READOUT_HEIGHT)
        top = PADDING + READOUT_HEIGHT + GAP
        room = (self.height - top - PADDING - GAP) / 2.0
        height = max(MIN_KEY_HEIGHT, min(MAX_KEY_HEIGHT, room))
        self.place_row(self.row_one, top, height)
        shown, hidden = ((self.more_row, self.row_two) if self.more
                         else (self.row_two, self.more_row))
        for key in hidden:
            key.hidden = True
        for key in shown:
            key.hidden = False
        self.place_row(shown, top + height + GAP, height)

    def place_row(self, keys, top, height):
        each = (self.width - 2 * PADDING - GAP * (len(keys) - 1)) / float(len(keys))
        for index, key in enumerate(keys):
            key.frame = (PADDING + index * (each + GAP), top, each, height)

    # --- The selection ------------------------------------------------------

    def current(self):
        """(text, start, end): the script and its selection, in order."""
        text = ek.text() or ''
        chosen = ek.selection() or (0, 0)
        start, end = sorted(chosen[:2])
        return text, max(0, min(start, len(text))), max(0, min(end, len(text)))

    def select(self, start, end, text, keep_history=False):
        if not keep_history:
            self.history = []
        ek.select(start, end)
        reveal(start, end)
        self.seen = ek.selection()
        self.show(text, start, end)

    def show(self, text, start, end):
        """The arrows for the mode, and the readout."""
        lines = moves.mode(text, start, end) == 'lines'
        for name, key in self.arrow_keys.items():
            key.label.text = (LINE_ARROWS if lines else WORD_ARROWS)[name]
        if time.time() < self.flash_until:
            return
        first, last = moves.lines_of(text, start, end)
        if lines:
            count = last - first + 1
            words = 'line %d' % first if count == 1 else 'lines %d–%d · %d' % (first, last, count)
        elif end > start:
            piece = text[start:end]
            if len(piece) > WORD_SHOWN:
                piece = piece[:WORD_SHOWN - 1] + '…'
            words = '“%s” · line %d' % (piece, first)
        else:
            words = 'line %d · cursor' % first
        self.readout.text = words

    def refresh(self):
        self.show(*self.current())

    def flash(self, words):
        self.readout.text = words
        self.flash_until = time.time() + FLASH_SECONDS

    def begin(self):
        """On open: read the editor's selection."""
        self.seen = None
        self.next_check = 0.0
        self.restyle()
        self.refresh()

    def watch(self, now):
        """Repeat held keys; end a flash; follow a selection made by hand."""
        for key in self.row_one:
            key.repeat(now)
        if self.flash_until and now >= self.flash_until:
            self.flash_until = 0.0
            self.refresh()
        if now < self.next_check:
            return
        self.next_check = now + RECHECK_SECONDS
        chosen = ek.selection()
        if chosen is not None and chosen != self.seen:
            self.seen = chosen
            self.history = []
            self.refresh()

    # --- Keys ---------------------------------------------------------------

    def press(self, name):
        try:
            getattr(self, 'do_' + name)()
        except Exception as problem:
            traceback.print_exc()
            self.flash(str(problem))

    def arrow(self, way):
        text, start, end = self.current()
        if moves.mode(text, start, end) == 'lines':
            step = {'up': (lineops.move, -1), 'down': (lineops.move, 1),
                    'left': (lineops.dedent,), 'right': (lineops.indent,)}[way]
            self.apply(text, start, end, *step)
        else:
            new_start, new_end = moves.hop(text, start, end, way)
            self.select(new_start, new_end, text)

    def do_left(self):
        self.arrow('left')

    def do_right(self):
        self.arrow('right')

    def do_up(self):
        self.arrow('up')

    def do_down(self):
        self.arrow('down')

    def do_grow(self):
        text, start, end = self.current()
        new = moves.grow(text, start, end)
        if new == (start, end):
            self.flash('No more lines')
            return
        self.history.append((start, end))
        self.select(new[0], new[1], text, keep_history=True)

    def do_shrink(self):
        text, start, end = self.current()
        new = self.history.pop() if self.history else moves.shrink(text, start, end)
        new = (min(new[0], len(text)), min(new[1], len(text)))
        self.select(new[0], new[1], text, keep_history=True)

    def do_reset(self):
        text, start, _ = self.current()
        new = moves.word_at(text, start)
        self.select(new[0], new[1], text)

    # --- Actions ------------------------------------------------------------

    def apply(self, text, start, end, operation, *args):
        """A lineops operation on the selection's lines, written as the
        smallest change; the same lines stay selected."""
        first, last = moves.lines_of(text, start, end)
        new_text, (new_first, new_last) = operation(text, first, last, *args)
        if new_text == text:
            return False
        edit_start, edit_end, piece = lineops.changed_span(text, new_text)
        if not ek.replace(edit_start, edit_end, piece):
            self.flash("Couldn't edit the script")
            return False
        span_start, span_end = moves.line_span(new_text, new_first, new_last)
        self.select(span_start, span_end, new_text)
        return True

    def chunk(self, text, start, end):
        """(piece to copy, words for the flash): whole lines (with a final
        newline) in line mode or at a bare cursor, else the selection."""
        if end == start or moves.mode(text, start, end) == 'lines':
            first, last = moves.lines_of(text, start, end)
            span_start, span_end = moves.line_span(text, first, last)
            count = last - first + 1
            return text[span_start:span_end] + '\n', '%d line%s' % (count, '' if count == 1 else 's')
        return text[start:end], '%d chars' % (end - start)

    def do_copy(self):
        text, start, end = self.current()
        piece, words = self.chunk(text, start, end)
        clip.set_text(piece)
        self.flash('Copied ' + words)

    def do_cut(self):
        text, start, end = self.current()
        piece, words = self.chunk(text, start, end)
        clip.set_text(piece)
        if end == start or moves.mode(text, start, end) == 'lines':
            if not self.apply(text, start, end, lineops.delete):
                return
        elif ek.replace(start, end, ''):
            self.select(start, start, text[:start] + text[end:])
        else:
            self.flash("Couldn't edit the script")
            return
        self.flash('Cut ' + words)

    def do_paste(self):
        piece = clipboard_text()
        if not piece:
            self.flash('The clipboard is empty')
            return
        text, start, end = self.current()
        edit_start, edit_end, new, (new_start, new_end) = moves.paste(text, start, end, piece)
        if not ek.replace(edit_start, edit_end, new):
            self.flash("Couldn't edit the script")
            return
        self.select(new_start, new_end, text[:edit_start] + new + text[edit_end:])

    def do_run(self):
        path = ek.current_file()
        if not path:
            self.flash('No open script')
            return
        text, start, end = self.current()
        if end == start or moves.mode(text, start, end) == 'lines':
            start, end = moves.line_span(text, *moves.lines_of(text, start, end))
        console.run_part(path, start, end)

    def do_explain(self):
        """?: Explain on the selection (a name: its docs; lines: what is in them)."""
        text, start, end = self.current()
        from . import explain
        tool = explain.open_explain()
        tool.explain_here(text, start, end)

    def do_more(self):
        self.more = not self.more
        self.layout()

    def do_duplicate(self):
        self.apply(*self.current(), lineops.duplicate)

    def do_comment(self):
        self.apply(*self.current(), lineops.toggle_comment)

    def do_snippet(self):
        """🧩: the selection (or the cursor's line) goes to Snippets' New snippet form."""
        text, start, end = self.current()
        if end == start:
            start, end = moves.line_span(text, *moves.lines_of(text, start, end))
            self.select(start, end, text)
        from . import snippets
        snippets.open_snippets().new_snippet()

    def do_view(self):
        path = ek.current_file()
        if not path:
            return
        text, start, end = self.current()
        from . import scriptview
        scriptview.open_script_window(path, moves.lines_of(text, start, end)[0])


def on_ipad():
    return min(ui.get_screen_size()) >= IPAD_SCREEN


def open_scissors_pad():
    """Open the Scissors pad (or bring it back): in the keyboard's place on a
    phone, as a compact window over the code on an iPad."""
    if on_ipad():
        window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY + '-ipad', size=IPAD_SIZE)
    else:
        window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, home='dock',
                           size=(0, PAD_HEIGHT))
    pad = ScissorsPad(window)
    window.scissors_pad = pad
    window.add_page('Scissors', pad)
    window.on('open', lambda _window: pad.begin())
    window.show()
    return window
"""Scissors bar: a range of lines over the top of the script, and what to do with it.

    [ 12 ] – [ 18 ]  7 lines           ⌂  ▣  ⤓
    📋  ✂️  ⧉  ↑  ↓  ⇥  ⇤  #  🧩  ▶

A slim bar at the top of the code (home='top_bar', like Find in script), so
the keyboard is always there. The range is the editor's selection: type the
first and last lines, or select by hand in the code and the fields follow.
With no range (a bare cursor) everything works on the cursor's line. After
an action the same lines stay selected, so pressing again carries on
(↑ ↑ ↑ walks a block up). The text work is lineops.py (pure, tested); edits
go through ek.replace as the smallest change, so Pythonista's undo covers
them.

    ⌂  the cursor's line      ▣  the block around it (again: the one around that)
    ⤓  one more line below

    📋 copy  ✂️ cut  ⧉ duplicate below  ↑ ↓ move past the neighbours
    ⇥ ⇤ indent, dedent  # comment or uncomment  🧩 save as a snippet
    ▶ run the lines in the Console          header 📜: the script as a window

    from editorkit_toolbox import scissors_bar
    scissors_bar.open_scissors_bar()
"""
import time

import ui
import editorkit as ek
from editorkit import clip

from . import console, lineops


# --- Settings -------------------------------------------------------------

TITLE = 'Scissors'
EMOJI = '✂️'
WINDOW_KEY = 'deck-scissors-bar'
BAR_HEIGHT = 150             # header plus the range row and the action row
ROW_HEIGHT = 36
GAP = 6
FIELD_WIDTH = 58             # the line fields at full width...
MIN_FIELD_WIDTH = 44         # ...and as narrow as they get
DASH_WIDTH = 14
MIN_COUNT_WIDTH = 44         # narrower than this, the line count hides
MIN_BUTTON_WIDTH = 30        # buttons wrap onto another row rather than get narrower
ROW1_FULL_WIDTH = 280        # narrower than this, ⌂ ▣ ⤓ join the action grid
MIN_WIDTH = 200              # the window is never narrower
RECHECK_SECONDS = 0.3        # how often to notice a selection made by hand
FLASH_SECONDS = 1.5          # how long "Copied 7 lines" shows in place of the count
VIEW_ICON = '📜'             # header: the script as a window, at the range

# Row 1, right: (label, method).
RANGE_BUTTONS = (('⌂', 'to_cursor_line'), ('▣', 'to_block'), ('⤓', 'extend'))

# Row 2: (label, method), left to right.
ACTIONS = (('📋', 'copy'), ('✂️', 'cut'), ('⧉', 'duplicate'), ('↑', 'move_up'),
           ('↓', 'move_down'), ('⇥', 'indent'), ('⇤', 'dedent'), ('#', 'comment'),
           ('🧩', 'to_snippet'), ('▶', 'run'))


class ScissorsBar(ui.View):

    def __init__(self, window):
        self.window = window
        self.range = None            # (first, last) lines; None: the cursor's line
        self.seen_selection = None   # the editor's selection last seen or set by us
        self.typing = False          # a line field has the keyboard
        self.next_check = 0.0
        self.flash_until = 0.0

        self.first_field = self.make_field('from')
        self.last_field = self.make_field('to')
        self.dash = ui.Label(text='–', alignment=ui.ALIGN_CENTER, font=('<system>', 15))
        self.add_subview(self.dash)
        self.count_label = ui.Label(font=('<system>', 13))
        self.add_subview(self.count_label)
        # The buttons wrap into a grid, which scrolls when the window is too
        # short for all its rows (pull the window taller to see them all).
        self.grid = ui.ScrollView()
        self.grid.shows_horizontal_scroll_indicator = False
        self.grid.background_color = (0, 0, 0, 0)
        self.add_subview(self.grid)
        self.range_buttons = [self.make_button(label, name) for label, name in RANGE_BUTTONS]
        self.action_buttons = [self.make_button(label, name) for label, name in ACTIONS]
        self.restyle()

    # --- Building ---------------------------------------------------------

    def palette(self):
        from editorkit.native.base import palette_for
        return palette_for(self.window)

    def make_field(self, placeholder):
        from editorkit.native.base import style_field
        from editorkit.native.field import tint_placeholder
        field = style_field(ui.TextField(placeholder=placeholder), self.palette())
        tint_placeholder(field, self.palette().dim)
        field.keyboard_type = ui.KEYBOARD_NUMBER_PAD
        field.alignment = ui.ALIGN_CENTER
        field.delegate = self
        self.add_subview(field)
        return field

    def make_button(self, label, name):
        button = ui.Button(title=label, font=('<system-bold>', 16))
        button.corner_radius = 8
        button.action = lambda sender, name=name: getattr(self, name)()
        self.add_subview(button)
        return button

    def restyle(self):
        """The theme changed: re-apply the palette's colours."""
        from editorkit.native.field import tint_placeholder
        palette = self.palette()
        for field in (self.first_field, self.last_field):
            field.background_color = palette.background
            field.text_color = palette.text
            field.tint_color = palette.accent
            tint_placeholder(field, palette.dim)
        for button in self.range_buttons + self.action_buttons:
            button.background_color = palette.background
            button.tint_color = palette.text
        self.dash.text_color = palette.dim
        self.count_label.text_color = palette.dim

    def layout(self):
        """Row 1: the line fields, the count and (when wide) ⌂ ▣ ⤓. Below it,
        a grid of buttons that wraps onto more rows as the window narrows."""
        width, size = self.width, ROW_HEIGHT
        wide = width >= ROW1_FULL_WIDTH
        right = width
        if wide:
            for button in reversed(self.range_buttons):
                self.put(button, self)
                right -= size
                button.frame = (right, 0, size, size)
                right -= GAP
        field = max(MIN_FIELD_WIDTH, min(FIELD_WIDTH, (right - DASH_WIDTH - GAP) / 2.0))
        self.first_field.frame = (0, 0, field, size)
        self.dash.frame = (field, 0, DASH_WIDTH, size)
        self.last_field.frame = (field + DASH_WIDTH, 0, field, size)
        count_x = 2 * field + DASH_WIDTH + GAP
        room = right - count_x
        self.count_label.hidden = room < MIN_COUNT_WIDTH
        self.count_label.frame = (count_x, 0, max(0, room), size)

        buttons = ([] if wide else self.range_buttons) + self.action_buttons
        for button in buttons:
            self.put(button, self.grid)
        top = size + GAP
        self.grid.frame = (0, top, width, max(0, self.height - top))
        per_row = max(1, min(len(buttons), int((width + GAP) // (MIN_BUTTON_WIDTH + GAP))))
        each = (width - (per_row - 1) * GAP) / float(per_row)
        for index, button in enumerate(buttons):
            row, column = divmod(index, per_row)
            button.frame = (column * (each + GAP), row * (size + GAP), each, size)
        rows = (len(buttons) + per_row - 1) // per_row
        self.grid.content_size = (width, rows * (size + GAP) - GAP)

    def put(self, view, parent):
        """view into parent (the range buttons move between row 1 and the grid)."""
        if view.superview is not parent:
            parent.add_subview(view)

    # --- The range ----------------------------------------------------------

    def text(self):
        return ek.text() or ''

    def lines(self, text):
        """(first, last) of the range, or the cursor's line when there is none."""
        if self.range is not None:
            return lineops.clamp(text, *self.range)
        chosen = ek.selection() or (0, 0)
        line = lineops.line_of(text, chosen[0])
        return lineops.clamp(text, line, line)

    def set_range(self, first, last, text=None):
        """first..last as the range: selected in the editor, shown in the fields."""
        text = self.text() if text is None else text
        first, last = lineops.clamp(text, first, last)
        self.range = (first, last)
        start, end = lineops.span(text, first, last)
        ek.select(start, end)
        self.seen_selection = ek.selection()      # don't follow our own change back
        self.show_range(text)

    def show_range(self, text=None, skip=None):
        """The fields and the count, from the range (skip: the field being typed in)."""
        text = self.text() if text is None else text
        first, last = self.lines(text)
        for field, value in ((self.first_field, first), (self.last_field, last)):
            if field is not skip:
                field.text = str(value)
        if time.time() < self.flash_until:
            return
        if self.range is None:
            self.count_label.text = 'line %d · cursor' % first
        else:
            count = last - first + 1
            self.count_label.text = '%d line%s' % (count, '' if count == 1 else 's')

    def flash(self, words):
        self.count_label.text = words
        self.flash_until = time.time() + FLASH_SECONDS

    def begin(self):
        """On open: take the editor's selection as the range."""
        self.seen_selection = None
        self.next_check = 0.0
        self.tick(time.time())

    def tick(self, now):
        """Follow a selection made by hand; put the count back after a flash."""
        if self.flash_until and now >= self.flash_until:
            self.flash_until = 0.0
            self.show_range()
        if now < self.next_check:
            return
        self.next_check = now + RECHECK_SECONDS
        chosen = ek.selection()
        if chosen is None or chosen == self.seen_selection:
            return
        self.seen_selection = chosen
        if self.typing:
            return                   # the fields lead while they are being typed in
        text = self.text()
        if chosen[1] > chosen[0]:
            self.range = (lineops.line_of(text, chosen[0]),
                          lineops.line_of(text, max(chosen[0], chosen[1] - 1)))
        else:
            self.range = None
        self.show_range(text)

    # --- Typing line numbers ------------------------------------------------

    def textfield_did_begin_editing(self, field):
        self.typing = True

    def textfield_did_end_editing(self, field):
        self.typing = False

    def textfield_did_change(self, field):
        try:
            value = int(field.text)
        except ValueError:
            return
        text = self.text()
        first, last = self.lines(text)
        if field is self.first_field:
            first, last = value, max(last, value)
        else:
            first, last = min(first, value), value
        first, last = lineops.clamp(text, first, last)
        self.range = (first, last)
        start, end = lineops.span(text, first, last)
        ek.select(start, end)
        self.seen_selection = ek.selection()
        self.show_range(text, skip=field)

    def textfield_should_return(self, field):
        field.end_editing()
        return True

    # --- Range buttons --------------------------------------------------------

    def to_cursor_line(self):
        text = self.text()
        chosen = ek.selection() or (0, 0)
        line = lineops.line_of(text, chosen[0])
        self.set_range(line, line, text)

    def to_block(self):
        """The block around the range; when it already is one, the block
        around that."""
        text = self.text()
        first, last = self.lines(text)
        for outer in (False, True):
            found = lineops.block_around(text, first, outer=outer)
            if found[0] <= first and found[1] >= last and found != (first, last):
                self.set_range(found[0], found[1], text)
                return
        self.flash('No wider block')

    def extend(self):
        text = self.text()
        first, last = self.lines(text)
        self.set_range(first, last + 1, text)

    # --- Actions --------------------------------------------------------------

    def apply(self, operation, *args):
        """Run a lineops operation on the range and write the smallest change.
        The same lines stay selected (on the cursor's line, the cursor moves
        with it)."""
        text = self.text()
        first, last = self.lines(text)
        new_text, (new_first, new_last) = operation(text, first, last, *args)
        if new_text == text:
            return False
        start, end, piece = lineops.changed_span(text, new_text)
        if not ek.replace(start, end, piece):
            self.flash("Couldn't edit the script")
            return False
        if self.range is None and new_first == new_last:
            ek.select(lineops.span(new_text, new_first, new_first)[0])
            self.seen_selection = ek.selection()
            self.show_range(new_text)
        else:
            self.set_range(new_first, new_last, new_text)
        return True

    def part(self):
        """(text, first, last, the lines' text with a final newline)."""
        text = self.text()
        first, last = self.lines(text)
        start, end = lineops.span(text, first, last)
        return text, first, last, text[start:end] + '\n'

    def copy(self):
        _, first, last, piece = self.part()
        clip.set_text(piece)
        count = last - first + 1
        self.flash('Copied %d line%s' % (count, '' if count == 1 else 's'))

    def cut(self):
        _, first, last, piece = self.part()
        clip.set_text(piece)
        if self.apply(lineops.delete):
            count = last - first + 1
            self.flash('Cut %d line%s' % (count, '' if count == 1 else 's'))

    def duplicate(self):
        self.apply(lineops.duplicate)

    def move_up(self):
        self.apply(lineops.move, -1)

    def move_down(self):
        self.apply(lineops.move, 1)

    def indent(self):
        self.apply(lineops.indent)

    def dedent(self):
        self.apply(lineops.dedent)

    def comment(self):
        self.apply(lineops.toggle_comment)

    def to_snippet(self):
        """🧩: the lines selected, then Snippets' own New snippet form takes
        them (a title, then saved in the shown group)."""
        text, first, last, _ = self.part()
        start, end = lineops.span(text, first, last)
        ek.select(start, end)
        self.seen_selection = ek.selection()
        from . import snippets
        snippets.open_snippets().new_snippet()

    def run(self):
        path = ek.current_file()
        if not path:
            self.flash('No open script')
            return
        text, first, last, _ = self.part()
        start, end = lineops.span(text, first, last)
        console.run_part(path, start, end)

    def view(self):
        path = ek.current_file()
        if not path:
            return
        _, first, _, _ = self.part()
        from . import scriptview
        scriptview.open_script_window(path, first)


def open_scissors_bar():
    """Open the Scissors bar over the top of the code (or bring it back)."""
    # Tinted so code shows through; a top bar insets the code by default.
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, home='top_bar',
                       size=(0, BAR_HEIGHT), min_size=(MIN_WIDTH, BAR_HEIGHT),
                       backdrop='tinted')
    bar = ScissorsBar(window)
    window.scissors_bar = bar
    window.add_page('Scissors', bar)
    window.add_button(VIEW_ICON, lambda _window: bar.view(), name='view')
    window.on('open', lambda _window: bar.begin())
    window.show()
    return window
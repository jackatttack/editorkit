"""Lens: a look at the value under the cursor, and a control that fits it.

    number 0.35 · line 28
    [−0.1] [−0.01]   0.35   [+0.01] [+0.1]
    ──────────────●───────────────

A slim bar at the top of the code (home='top_bar', like Find and Scissors).
lens_detect.py works out what the cursor touches (or the selection holds);
a lens shows the control for it:

    number   steps of its last digit (0.35 steps by 0.01) and ten of them,
             and a slider over the value either side (re-centred for each
             new number), snapping to the step
    colour   a swatch and R G B sliders, for '#E8365A', (0.2, 0.4, 1.0) or
             (255, 128, 0)

Values are written the way they were (decimals, case, form). Step buttons
write at once; sliders write when you pause (WRITE_PAUSE_SECONDS), so one
drag is one undo. Adding a lens: a view with show(thing, fresh) and
restyle(palette), registered in LensBar.lenses under its kind.

    from editorkit_toolbox import lens
    lens.open_lens()
"""
import importlib
import importlib.util
import inspect
import sys
import time

import ui
import editorkit as ek
import codesense
from codesense import units

from . import lens_detect as detect


# --- Settings -------------------------------------------------------------

TITLE = 'Lens'
EMOJI = '🔬'
WINDOW_KEY = 'deck-lens'
BAR_HEIGHT = 200             # header, the status row and the tallest lens (colour)
MIN_WIDTH = 220
ROW_HEIGHT = 36
SLIDER_ROW = 28
GAP = 6
STEP_BUTTON_WIDTH = 64
WATCH_SECONDS = 0.25         # how often to look at what is under the cursor
WRITE_PAUSE_SECONDS = 0.4    # a slider writes once it has been still this long
NUMBER_SPAN_STEPS = 20       # a number's slider reaches at least this many steps either side
MEMBER_ROW_HEIGHT = 32
MEMBER_NAME_SHARE = 0.6      # a member's name takes at most this share of the row
DOCS_BUTTON_WIDTH = 44       # the row's 📖: the member in Docs
DESCRIPTION_LENGTH = 90      # a docstring's first line is cut here
VALUE_LENGTH = 40            # a value's repr is cut here
KIND_MARKS = {'function': 'ƒ', 'class': 'C', 'module': 'M', 'keyword': 'k'}   # anything else: ·
HINT = 'Put the cursor on a number, a colour, or just after a dot.'
CHANNEL_TINTS = ((0.92, 0.30, 0.30), (0.30, 0.78, 0.40), (0.35, 0.55, 0.95))


def palette_of(window):
    from editorkit.tiles.base import palette_for
    return palette_for(window)


def make_button(parent, action):
    button = ui.Button(font=('<system-bold>', 14))
    button.corner_radius = 8
    button.action = action
    parent.add_subview(button)
    return button


# --- The number lens ----------------------------------------------------------

class NumberLens(ui.View):

    def __init__(self, bar):
        self.bar = bar
        self.value = 0
        self.form = detect.number_form('0')
        self.step = 1
        self.low, self.high = -1.0, 1.0
        self.buttons = []
        for factor in (-10, -1, 1, 10):
            button = make_button(self, lambda sender, factor=factor: self.nudge(factor))
            self.buttons.append((factor, button))
        self.value_label = ui.Label(font=('<system-bold>', 22), alignment=ui.ALIGN_CENTER)
        self.add_subview(self.value_label)
        self.slider = ui.Slider()
        self.slider.continuous = True
        self.slider.action = self.slid
        self.add_subview(self.slider)

    def restyle(self, palette):
        for _, button in self.buttons:
            button.background_color = palette.background
            button.tint_color = palette.text
        self.value_label.text_color = palette.text
        self.slider.tint_color = palette.accent

    def layout(self):
        width, size = self.width, ROW_HEIGHT
        places = {-10: 0, -1: STEP_BUTTON_WIDTH + GAP,
                  1: width - 2 * STEP_BUTTON_WIDTH - GAP, 10: width - STEP_BUTTON_WIDTH}
        for factor, button in self.buttons:
            button.frame = (places[factor], 0, STEP_BUTTON_WIDTH, size)
        middle = 2 * (STEP_BUTTON_WIDTH + GAP)
        self.value_label.frame = (middle, 0, max(0, width - 2 * middle), size)
        self.slider.frame = (0, size + GAP, width, SLIDER_ROW)

    def show(self, thing, fresh):
        self.form = thing.form
        self.value = thing.value
        self.step = detect.number_step(thing.form)
        if fresh:
            span = max(abs(self.value), self.step * NUMBER_SPAN_STEPS)
            self.low, self.high = self.value - span, self.value + span
        self.value_label.text = thing.text
        for factor, button in self.buttons:
            amount = detect.format_number(abs(factor) * self.step, self.form)
            button.title = ('+' if factor > 0 else '−') + amount
        self.place_slider()

    def snap(self, value):
        """value on the step (0.35's steps are 0.01), an int for whole numbers."""
        value = round(value / self.step) * self.step
        return value if self.form['float'] else int(round(value))

    def place_slider(self):
        if not self.low <= self.value <= self.high:
            span = (self.high - self.low) / 2.0
            self.low, self.high = self.value - span, self.value + span
        width = self.high - self.low
        self.slider.value = (self.value - self.low) / width if width else 0.5

    def shown(self):
        self.value_label.text = detect.format_number(self.value, self.form)

    def nudge(self, factor):
        self.value = self.snap(self.value + factor * self.step)
        self.shown()
        self.place_slider()
        self.bar.set_value(self.value, now=True)

    def slid(self, slider):
        self.value = self.snap(self.low + slider.value * (self.high - self.low))
        self.shown()
        self.bar.set_value(self.value)


# --- The colour lens ------------------------------------------------------------

class ColourLens(ui.View):

    def __init__(self, bar):
        self.bar = bar
        self.rgba = (0.0, 0.0, 0.0, 1.0)
        self.swatch = ui.View()
        self.swatch.corner_radius = 10
        self.swatch.border_width = 1
        self.add_subview(self.swatch)
        self.channels = []
        for name in ('R', 'G', 'B'):
            label = ui.Label(text=name, font=('<system-bold>', 13), alignment=ui.ALIGN_CENTER)
            slider = ui.Slider()
            slider.continuous = True
            slider.action = self.slid
            self.add_subview(label)
            self.add_subview(slider)
            self.channels.append((label, slider))

    def restyle(self, palette):
        self.swatch.border_color = palette.edge
        for (label, slider), tint in zip(self.channels, CHANNEL_TINTS):
            label.text_color = palette.dim
            slider.tint_color = tint

    def layout(self):
        size = min(self.height, 3 * SLIDER_ROW)
        self.swatch.frame = (0, 0, size, size)
        left = size + GAP
        for index, (label, slider) in enumerate(self.channels):
            y = index * SLIDER_ROW
            label.frame = (left, y, 18, SLIDER_ROW)
            slider.frame = (left + 20, y, max(0, self.width - left - 20), SLIDER_ROW)

    def show(self, thing, fresh):
        self.rgba = tuple(thing.value)
        self.swatch.background_color = self.rgba
        for (_, slider), part in zip(self.channels, self.rgba[:3]):
            slider.value = part

    def slid(self, sender):
        red, green, blue = (slider.value for _, slider in self.channels)
        self.rgba = (red, green, blue, self.rgba[3])
        self.swatch.background_color = self.rgba
        self.bar.set_value(self.rgba)


# --- The member lens --------------------------------------------------------------

def suggestion_parts(item):
    """(name, kind) from a codesense Suggestion."""
    fields = tuple(item) if isinstance(item, tuple) else ()
    name = getattr(item, 'name', None) or (fields[0] if fields else str(item))
    kind = fields[1] if len(fields) > 1 else getattr(item, 'kind', '')
    return str(name), str(kind or '')


def first_doc_line(thing):
    doc = inspect.getdoc(thing) or ''
    for line in doc.splitlines():
        if line.strip():
            return line.strip()[:DESCRIPTION_LENGTH]
    return ''


def reachable(base):
    """The object a dotted base names ('sys', 'os.path', 'ui.Button'), when
    Python can reach it without running your own code: a module already
    loaded, or one importable from outside Documents (the standard library,
    Pythonista's modules, site-packages). None otherwise."""
    if not base:
        return None
    parts = base.split('.')
    found = sys.modules.get(parts[0])
    if found is None:
        try:
            spec = importlib.util.find_spec(parts[0])
        except Exception:
            return None
        origin = (getattr(spec, 'origin', None) or '') if spec is not None else ''
        if spec is None or ('/Documents/' in origin and 'site-packages' not in origin):
            return None              # one of your scripts: importing it would run it
        try:
            found = importlib.import_module(parts[0])
        except Exception:
            return None
    for part in parts[1:]:
        try:
            found = getattr(found, part)
        except Exception:
            return None
    return found


def short_signature(member):
    """'(hook, /)' when a member has no docstring (builtins on device often
    do not), cut like a description; '' when there is none."""
    try:
        text = str(inspect.signature(member))
    except (TypeError, ValueError):
        return ''
    return text if len(text) <= DESCRIPTION_LENGTH else text[:DESCRIPTION_LENGTH - 1] + '…'


def describe(owner, name, kind):
    """One line about owner.name: a docstring's first line for functions,
    classes and modules, a short repr for values, else the kind."""
    if owner is None:
        return kind
    try:
        member = getattr(owner, name)
    except Exception:
        return kind
    if callable(member) or inspect.ismodule(member):
        return first_doc_line(member) or short_signature(member) or kind
    text = repr(member)
    return text if len(text) <= VALUE_LENGTH else text[:VALUE_LENGTH - 1] + '…'


class MemberLens(ui.View):
    """After a dot: what can follow (jedi, through codesense), one compact
    row each: a kind mark, the name, and a description looked up from the
    real object (only for rows on screen, then kept). A tap completes the
    name in the code. A solid panel behind it, so code never shows through."""

    def __init__(self, bar):
        self.bar = bar
        self.items = []              # [(name, kind)]
        self.owner = None            # the object the dot follows, when reachable
        self.descriptions = {}       # name -> its line, once looked up
        self.palette = None
        self.table = ui.TableView()
        self.table.row_height = MEMBER_ROW_HEIGHT
        self.table.data_source = self
        self.table.delegate = self
        self.add_subview(self.table)
        self.note = ui.Label(font=('<system>', 13), text='Looking…')
        self.add_subview(self.note)

    def restyle(self, palette):
        self.palette = palette
        self.background_color = palette.panel
        self.table.background_color = palette.panel
        self.note.text_color = palette.dim
        self.table.reload()

    def layout(self):
        self.table.frame = (0, 0, self.width, self.height)
        self.note.frame = (8, 0, self.width - 8, ROW_HEIGHT)

    def show(self, thing, fresh):
        if fresh:                    # a new dot: clear; more letters keep the old list till the answer
            self.items = []
            self.descriptions = {}
            self.owner = reachable(thing.value)
            self.table.reload()
            self.note.text = 'Looking…'
            self.note.hidden = False

    def fill(self, answer):
        if answer.error:
            self.items = []
            self.note.text = 'No members here (%s)' % answer.error[:60]
        else:
            self.items = [suggestion_parts(item) for item in answer.items]
            self.note.text = 'Nothing follows this dot'
        self.note.hidden = bool(self.items)
        self.table.reload()
        bar = self.bar
        capped = len(self.items) >= codesense.assist.MAX_COMPLETIONS
        bar.status.text = 'after %s. · %d%s · line %d' % (
            bar.thing.value or '…', len(self.items), '+' if capped else '', bar.line)

    def description(self, name, kind):
        if name not in self.descriptions:
            self.descriptions[name] = describe(self.owner, name, kind)
        return self.descriptions[name]

    def tableview_number_of_rows(self, tableview, section):
        return len(self.items)

    def tableview_cell_for_row(self, tableview, section, row):
        name, kind = self.items[row]
        palette = self.palette
        width, height = tableview.width, MEMBER_ROW_HEIGHT
        cell = ui.TableViewCell()
        cell.background_color = palette.panel if palette else (0, 0, 0, 0)
        width -= DOCS_BUTTON_WIDTH
        mark = ui.Label(frame=(8, 0, 16, height), text=KIND_MARKS.get(kind, '·'),
                        font=('<system-bold>', 12), alignment=ui.ALIGN_CENTER)
        name_font = ('<system-bold>', 14)
        name_width = min(ui.measure_string(name, font=name_font)[0] + 8,
                         width * MEMBER_NAME_SHARE)
        label = ui.Label(frame=(28, 0, name_width, height), text=name, font=name_font)
        left = 28 + name_width + 4
        detail = ui.Label(frame=(left, 0, max(0, width - left - 8), height),
                          text=self.description(name, kind), font=('<system>', 12))
        if palette is not None:
            mark.text_color = palette.accent
            label.text_color = palette.text
            detail.text_color = palette.dim
        for view in (mark, label, detail):
            cell.content_view.add_subview(view)
        docs_button = ui.Button(title='📖', font=('<system>', 16))
        docs_button.frame = (tableview.width - DOCS_BUTTON_WIDTH, 0, DOCS_BUTTON_WIDTH, height)
        docs_button.action = lambda sender, name=name: self.open_docs(name)
        cell.content_view.add_subview(docs_button)
        return cell

    def tableview_did_select(self, tableview, section, row):
        self.bar.complete(self.items[row][0])

    def open_docs(self, name):
        """📖: this member in Docs. Tries base.name, then the member on each
        class the base inherits from (the docs describe add_subview once, on
        ui.View); with no match, Docs searches for the name."""
        base = self.bar.thing.value or ''
        names = ['%s.%s' % (base, name)] if base else []
        root = base.split('.', 1)[0]
        if inspect.isclass(self.owner):
            for klass in self.owner.__mro__[1:]:
                if klass is not object:
                    names.append('%s.%s.%s' % (root, klass.__name__, name))
        from . import docs
        docs.open_docs(names, name)


# --- The bar ----------------------------------------------------------------------

class LensBar(ui.View):

    def __init__(self, window):
        self.window = window
        self.thing = detect.NOTHING
        self.line = 0
        self.seen = None             # (selection, text length, text hash) last looked at
        self.pending = None          # a value waiting to be written
        self.write_at = 0.0
        self.next_check = 0.0
        self.status = ui.Label(font=('<system-bold>', 14))
        self.add_subview(self.status)
        self.hint = ui.Label(font=('<system>', 13), text=HINT)
        self.hint.number_of_lines = 0
        self.add_subview(self.hint)
        self.lenses = {'number': NumberLens(self), 'colour': ColourLens(self),
                       'member': MemberLens(self)}
        # Members after a dot come from codesense's jedi on its own thread;
        # answers carry a version, so a stale one is never shown.
        self.ledger = codesense.Ledger()
        self.assistant = codesense.Assistant(self.ledger)
        self.assistant.start()
        self.version = 0
        for view in self.lenses.values():
            view.hidden = True
            self.add_subview(view)
        self.restyle()

    def restyle(self):
        """The theme changed: re-apply the palette's colours."""
        palette = palette_of(self.window)
        self.status.text_color = palette.text
        self.hint.text_color = palette.dim
        for view in self.lenses.values():
            view.restyle(palette)

    def layout(self):
        width = self.width
        self.status.frame = (0, 0, width, ROW_HEIGHT)
        top = ROW_HEIGHT + GAP
        body = (0, top, width, max(0, self.height - top))
        self.hint.frame = body
        for view in self.lenses.values():
            view.frame = body

    # --- Looking ------------------------------------------------------------

    def begin(self):
        self.seen = None
        self.next_check = 0.0
        self.tick(time.time())

    def tick(self, now):
        """Write a value the sliders have paused on; otherwise look at what
        the cursor touches (not while a write is waiting)."""
        if self.pending is not None:
            if now >= self.write_at:
                self.write()
            return
        if self.thing.kind == 'member':
            answer = self.assistant.take('complete', self.version)
            if answer is not None:
                self.lenses['member'].fill(answer)
        if now < self.next_check:
            return
        self.next_check = now + WATCH_SECONDS
        text = ek.text() or ''
        chosen = ek.selection() or (0, 0)
        key = (tuple(chosen), len(text), hash(text))
        if key == self.seen:
            return
        self.seen = key
        thing = detect.what_is_here(text, chosen[0], chosen[1])
        if thing.kind is None and chosen[0] == chosen[1]:
            thing = self.member_at(text, chosen[0])
        fresh = thing.kind != self.thing.kind or thing.start != self.thing.start
        self.thing = thing
        self.line = text.count('\n', 0, thing.start) + 1
        self.show(fresh)

    def show(self, fresh):
        kind = self.thing.kind
        for name, view in self.lenses.items():
            view.hidden = name != kind
        self.hint.hidden = kind is not None
        if kind is None:
            self.status.text = TITLE
            return
        self.lenses[kind].show(self.thing, fresh)
        self.say(self.thing.text)

    def member_at(self, text, caret):
        """Just after a dot (ui. or ui.Bu): the name being typed, as a Thing
        whose value is what the dot follows, and a completion request for it.
        NOTHING anywhere else."""
        try:
            context = codesense.context_at(text, units.to_utf16(text, caret))
        except Exception:
            return detect.NOTHING
        if context.kind != 'attribute':
            return detect.NOTHING
        prefix = context.prefix or ''
        start = caret - len(prefix)
        end = caret                  # letters after the caret go too, so a tap leaves a clean name
        while end < len(text) and (text[end].isalnum() or text[end] == '_'):
            end += 1
        self.version += 1
        self.assistant.request('complete', self.version, text, units.to_utf16(text, caret))
        return detect.Thing('member', start, end, text[start:end],
                            context.details.get('base', ''), {'prefix': prefix})

    def complete(self, name):
        """A tapped member replaces the name being typed after the dot."""
        thing = self.thing
        if thing.kind != 'member':
            return
        if ek.replace(thing.start, thing.end, name):
            ek.select(thing.start + len(name))
            self.seen = None         # look again at once

    def stop(self):
        self.assistant.stop()

    def say(self, written):
        if self.thing.kind == 'member':
            self.status.text = 'after %s. · line %d' % (self.thing.value or '…', self.line)
            return
        self.status.text = '%s %s · line %d' % (self.thing.kind, written, self.line)

    # --- Writing --------------------------------------------------------------

    def written(self, value):
        if self.thing.kind == 'number':
            return detect.format_number(value, self.thing.form)
        return detect.format_colour(value, self.thing.form)

    def set_value(self, value, now=False):
        """A lens moved the value: shown at once, written now (a step) or
        once the slider has been still for WRITE_PAUSE_SECONDS."""
        self.pending = value
        self.write_at = time.time() + WRITE_PAUSE_SECONDS
        self.say(self.written(value))
        if now:
            self.write()

    def write(self):
        """The waiting value into the code, as the smallest replace (one undo)."""
        value, self.pending = self.pending, None
        thing = self.thing
        if thing.kind is None or value is None:
            return
        new = self.written(value)
        if new == thing.text:
            return
        if not ek.replace(thing.start, thing.end, new):
            self.say(thing.text)
            return
        self.thing = thing._replace(end=thing.start + len(new), text=new, value=value)
        ek.select(thing.start + len(new))      # still touching it: the lens stays
        text = ek.text() or ''
        self.seen = (tuple(ek.selection() or (0, 0)), len(text), hash(text))


def open_lens():
    """Open Lens over the top of the code (or bring it back)."""
    # Tinted so code shows through; a top bar insets the code by default.
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY, home='top_bar',
                       size=(0, BAR_HEIGHT), min_size=(MIN_WIDTH, BAR_HEIGHT),
                       backdrop='tinted')
    bar = LensBar(window)
    window.lens_bar = bar
    window.add_page('Lens', bar)
    window.on('open', lambda _window: bar.begin())
    window.on('close', lambda _window: bar.stop())
    window.show()
    return window
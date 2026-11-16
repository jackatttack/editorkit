# -*- coding: utf-8 -*-
"""Composer: a writing box for tools, after a chat app's input.

    from editorkit.native import Composer, ComposerSheet
    composer = Composer(window, placeholder='Your answer…',
                        context='Did the pin rest at the edge?',
                        on_send=save, draft_key='anvil-ask-3')
    window.show_sheet(ComposerSheet(composer))
    window.when_still(lambda w: w.focus(composer.text_view))

One rounded field that grows from one line to MAX_TEXT_HEIGHT as you write,
then scrolls. Along its bottom edge, inside it: 🔤 (spellcheck and
autocorrect), ⋯ (shows ⇥ ⇤ ↶ ↷ beside it) and the round send button ↑, lit
once there is text. on_send(text) gets the stripped text; the box empties
and its draft is cleared. An optional context line sits above the field,
quoted: what the words are for.

Height follows the text: wanted_height(width) says how tall the composer
wants to be, and on_height(height) fires when that changes. ComposerSheet
holds a composer at the top of a window sheet and follows it, so in the
console the box stays clear of the keyboard, which covers the lower part.

Drafts: with a draft_key the text is kept in ek.store('textbox') as you
type (TextBox's store), and a composer opened with no text starts from its
draft.

Prose, not code: a proportional font and spellcheck on by default. For
code, use TextBox.
"""
import math

import ui

from .. import textops
from ..stores import store
from .base import GAP, PADDING, RULE, WASH, Tile, palette_for, wash
from .textbox import DRAFTS_STORE, apply_keyboard_comfort, apply_readability


# --- Settings -------------------------------------------------------------

FONT = ('<system>', 16)
CONTEXT_FONT = ('<system>', 13)
TOOL_FONT = ('<system>', 15)
SEND_FONT = ('<system-bold>', 18)
FIELD_CORNER = 20
FIELD_PAD = 6                  # inside the field, around the text and the tool row
MIN_TEXT_HEIGHT = 40           # one line
MAX_TEXT_HEIGHT = 160          # about six lines; past this the text scrolls
CONTEXT_MAX_HEIGHT = 36        # two lines of context
TOOL_ROW_HEIGHT = 34
TOOL_WIDTH = 38
TOOL_CORNER = 8
SEND_SIZE = 32
QUOTE_BAR_WIDTH = 3
SHEET_ALPHA = 0.94             # ComposerSheet's fill: the page shows faintly behind
SPELL_TITLE = '🔤'
MORE_TITLE = '⋯'
SEND_TITLE = '↑'
CLEAR = (0, 0, 0, 0)


class Composer(Tile):
    """A growing, rounded writing field with its tools and send inside."""

    def __init__(self, window, text='', placeholder='Write…', context=None,
                 on_send=None, draft_key=None, spellcheck=True):
        Tile.__init__(self, window)
        self.on_send = on_send
        self.on_height = None            # on_height(height) when the wanted height changes
        self.draft_key = draft_key
        self.spellcheck = bool(spellcheck)
        self.tools_open = False
        self.last_height = None
        self.has_context = bool(context)

        self.quote_bar = ui.View()
        self.context_label = ui.Label()
        self.context_label.font = CONTEXT_FONT
        self.context_label.number_of_lines = 2
        self.context_label.text = context or ''
        self.quote_bar.hidden = not self.has_context
        self.context_label.hidden = not self.has_context
        self.add_subview(self.quote_bar)
        self.add_subview(self.context_label)

        self.field = ui.View()
        self.field.corner_radius = FIELD_CORNER
        self.field.border_width = 0.5
        self.add_subview(self.field)

        view = ui.TextView()
        view.font = FONT
        view.background_color = CLEAR
        view.autocapitalization_type = ui.AUTOCAPITALIZE_SENTENCES
        view.text = text or self.saved_draft()
        view.delegate = self
        apply_readability(view)
        apply_keyboard_comfort(view)
        self.text_view = view
        self.field.add_subview(view)

        self.placeholder = ui.Label()
        self.placeholder.font = FONT
        self.placeholder.text = placeholder
        self.placeholder.touch_enabled = False
        self.field.add_subview(self.placeholder)

        self.tools = ui.ScrollView()
        self.tools.shows_horizontal_scroll_indicator = False
        self.field.add_subview(self.tools)
        self.spell_button = self.add_tool(SPELL_TITLE, self.toggle_spellcheck)
        self.more_button = self.add_tool(MORE_TITLE, self.toggle_tools)
        self.edit_buttons = [self.add_tool(title, action) for title, action in (
            ('⇥', self.indent), ('⇤', self.outdent), ('↶', self.undo), ('↷', self.redo))]
        for button in self.edit_buttons:
            button.hidden = True

        self.send_button = ui.Button(title=SEND_TITLE, font=SEND_FONT)
        self.send_button.corner_radius = SEND_SIZE / 2.0
        self.send_button.action = lambda sender: self.send()
        self.field.add_subview(self.send_button)

        self.set_spellcheck(self.spellcheck)
        self.restyle()

    # --- Colours ------------------------------------------------------------

    def restyle(self):
        """Apply the window's palette (the manager calls this on a theme change)."""
        self.palette = palette_for(self.window)
        palette = self.palette
        self.quote_bar.background_color = palette.accent
        self.context_label.text_color = palette.dim
        self.field.background_color = palette.background
        self.field.border_color = wash(palette.text, RULE)
        self.text_view.text_color = palette.text
        self.text_view.tint_color = palette.accent
        self.placeholder.text_color = palette.dim
        self.paint_tools()
        self.refresh()

    def paint_tools(self):
        palette = self.palette
        for button in [self.spell_button, self.more_button] + self.edit_buttons:
            lit = ((button is self.spell_button and self.spellcheck)
                   or (button is self.more_button and self.tools_open))
            button.background_color = palette.accent if lit else CLEAR
            button.tint_color = palette.on_accent if lit else palette.text

    def refresh(self):
        """Placeholder and send button follow the text."""
        text = self.text_view.text
        has_words = bool(text.strip())
        palette = self.palette
        self.placeholder.hidden = bool(text)
        self.send_button.background_color = palette.accent if has_words else wash(palette.text, WASH)
        self.send_button.tint_color = palette.on_accent if has_words else palette.dim
        self.send_button.enabled = has_words

    # --- Tools --------------------------------------------------------------

    def add_tool(self, title, action):
        button = ui.Button(title=title, font=TOOL_FONT)
        button.corner_radius = TOOL_CORNER
        button.action = lambda sender: action()
        self.tools.add_subview(button)
        return button

    def toggle_tools(self):
        self.tools_open = not self.tools_open
        for button in self.edit_buttons:
            button.hidden = not self.tools_open
        self.paint_tools()
        self.layout()

    def set_spellcheck(self, on):
        """Spellcheck and autocorrect together."""
        self.spellcheck = bool(on)
        view = self.text_view
        view.spellchecking_type = self.spellcheck
        view.autocorrection_type = self.spellcheck
        try:
            view.objc_instance.reloadInputViews()
        except Exception:
            pass
        self.paint_tools()

    def toggle_spellcheck(self):
        self.set_spellcheck(not self.spellcheck)

    def select(self, start, end):
        """Set the selection, kept inside the view's actual text."""
        length = len(self.text_view.text)
        self.text_view.selected_range = (min(max(0, start), length), min(max(0, end), length))

    def shift(self, edit):
        """Indent or outdent through textops (as TextBox does)."""
        view = self.text_view
        old = view.text
        start, end = view.selected_range
        new, new_start, new_end = edit(old, start, end)
        if new == old:
            return
        block_start, block_end = textops.line_block(old, start, end)
        replaced_end = len(new) - (len(old) - block_end)
        view.replace_range((block_start, block_end), new[block_start:replaced_end])
        if view.text != new:
            view.text = new
        self.select(new_start, new_end)
        self.changed()

    def indent(self):
        self.shift(textops.indent)

    def outdent(self):
        self.shift(textops.outdent)

    def undo(self):
        try:
            self.text_view.objc_instance.undoManager().undo()
        except Exception:
            pass
        self.changed()

    def redo(self):
        try:
            self.text_view.objc_instance.undoManager().redo()
        except Exception:
            pass
        self.changed()

    # --- Sending ------------------------------------------------------------

    def send(self):
        text = self.text_view.text.strip()
        if not text:
            return
        self.clear_draft()
        self.text_view.text = ''
        self.changed()
        if self.on_send is not None:
            self.on_send(text)

    @property
    def text(self):
        return self.text_view.text

    # --- Drafts -------------------------------------------------------------

    def saved_draft(self):
        if not self.draft_key:
            return ''
        return store(DRAFTS_STORE).get(self.draft_key, '') or ''

    def save_draft(self):
        if self.draft_key:
            store(DRAFTS_STORE)[self.draft_key] = self.text_view.text

    def clear_draft(self):
        if self.draft_key:
            store(DRAFTS_STORE)[self.draft_key] = ''

    # --- Following the text -------------------------------------------------

    def textview_did_change(self, text_view):
        self.changed()

    def changed(self):
        self.save_draft()
        self.refresh()
        self.follow_height()

    def follow_height(self):
        """Tell the holder when the wanted height changes, and lay out only
        then: laying out on every keystroke shook the text."""
        if not self.width:
            return
        height = self.wanted_height(self.width)
        if height == self.last_height:
            return
        self.last_height = height
        if self.on_height is not None:
            self.on_height(height)
        self.layout()

    # --- Sizes --------------------------------------------------------------

    def text_height(self, field_width):
        """The text's height at this field width, rounded up to a whole point,
        between one line and MAX_TEXT_HEIGHT."""
        width = max(40, field_width - 2 * FIELD_PAD)
        try:
            from objc_util import CGSize
            measured = self.text_view.objc_instance.sizeThatFits_(CGSize(width, 100000)).height
        except Exception:
            measured = MIN_TEXT_HEIGHT + 22 * self.text_view.text.count('\n')
        return max(MIN_TEXT_HEIGHT, min(MAX_TEXT_HEIGHT, math.ceil(measured)))

    def settle_text(self, text_height):
        """While the text fits, the text view must not scroll: UITextView
        nudges its content as lines are typed (the top line shook). Scrolling
        comes back once the text passes MAX_TEXT_HEIGHT."""
        fits = text_height < MAX_TEXT_HEIGHT
        try:
            self.text_view.objc_instance.setScrollEnabled_(not fits)
        except Exception:
            pass
        if fits:
            self.text_view.content_offset = (0, 0)

    def context_height(self, width):
        if not self.has_context:
            return 0
        try:
            measured = ui.measure_string(self.context_label.text,
                                         max_width=width - 2 * PADDING - 15 - QUOTE_BAR_WIDTH,
                                         font=CONTEXT_FONT)[1]
        except Exception:
            measured = 18
        return min(CONTEXT_MAX_HEIGHT, max(18, measured))

    @staticmethod
    def field_height(text_height):
        return FIELD_PAD + text_height + TOOL_ROW_HEIGHT + FIELD_PAD

    def wanted_height(self, width):
        height = PADDING
        if self.has_context:
            height += self.context_height(width) + GAP
        height += self.field_height(self.text_height(width - 2 * PADDING)) + PADDING
        return height

    def layout(self):
        width = self.width
        y = PADDING
        if self.has_context:
            context_height = self.context_height(width)
            self.quote_bar.frame = (PADDING + 4, y, QUOTE_BAR_WIDTH, context_height)
            label_x = PADDING + 4 + QUOTE_BAR_WIDTH + 8
            self.context_label.frame = (label_x, y, width - label_x - PADDING, context_height)
            y += context_height + GAP
        field_width = width - 2 * PADDING
        text_height = self.text_height(field_width)
        self.field.frame = (PADDING, y, field_width, self.field_height(text_height))
        inner = field_width - 2 * FIELD_PAD
        self.text_view.frame = (FIELD_PAD, FIELD_PAD, inner, text_height)
        self.settle_text(text_height)
        self.placeholder.frame = (FIELD_PAD + 13, FIELD_PAD + 6, max(0, inner - 26), 24)
        row_y = FIELD_PAD + text_height
        self.send_button.frame = (field_width - FIELD_PAD - SEND_SIZE,
                                  row_y + (TOOL_ROW_HEIGHT - SEND_SIZE) / 2.0,
                                  SEND_SIZE, SEND_SIZE)
        self.tools.frame = (FIELD_PAD, row_y, max(0, inner - SEND_SIZE - GAP), TOOL_ROW_HEIGHT)
        x = 0
        for button in [self.spell_button, self.more_button] + self.edit_buttons:
            if button.hidden:
                continue
            button.frame = (x, 2, TOOL_WIDTH, TOOL_ROW_HEIGHT - 4)
            x += TOOL_WIDTH + 2
        self.tools.content_size = (x, TOOL_ROW_HEIGHT)


class ComposerSheet(ui.View):
    """A window sheet holding a composer at its top, following its height.
    The rest of the sheet is a faint fill, so the page shows behind."""

    def __init__(self, composer, alpha=SHEET_ALPHA):
        self.composer = composer
        self.fill_alpha = alpha
        self.add_subview(composer)
        composer.on_height = lambda height: self.layout()
        self.restyle()

    def restyle(self):
        self.background_color = wash(self.composer.palette.panel, self.fill_alpha)
        self.composer.restyle()

    def layout(self):
        width = self.width
        self.composer.frame = (0, 0, width, min(self.height, self.composer.wanted_height(width)))
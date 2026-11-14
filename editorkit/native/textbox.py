"""TextBox: a multi-line writing surface for tools, riding the keyboard.

    ek.edit_text('def f():\\n    pass', title='Snippet', name='f',
                 chips=('${cursor}', '${date}'), draft_key='snippets',
                 on_done=lambda text, name: save(name, text))

edit_text opens a window above the keyboard holding a TextBox: an optional
name field, a monospaced text view, and a bar of ⇥ ⇤ ↶ ↷ plus any chips
(tap one to type it at the cursor). ✓ in the header calls on_done(text,
name) (name is None without a name field) and clears the draft. ✕, or
closing the window, cancels: on_cancel() is called and the draft is kept.
🔤 in the bar toggles spellcheck and autocorrect (spellcheck= sets the start).
Pythonista's key row does not appear over a TextBox (seen on device).

Drafts: with a draft_key, the text is saved to ek.store('textbox') as you
type, so a crash or an accidental close loses nothing. When a saved draft
differs from the text a box opens with, the bar offers ↺ Restore.

The text view gets Jot's readability (inset, line spacing) and keyboard
comfort (dark keyboard; smart dashes and quotes off, so -- survives).
"""
import ui

from .. import textops
from ..stores import store
from .base import GAP, PADDING, Tile, style_field


# --- Settings -------------------------------------------------------------

WINDOW_KEY = 'ek-textbox'
EMOJI = '✍️'
FONT = ('Menlo', 15)
BAR_FONT = ('<system>', 15)
NAME_HEIGHT = 36
BAR_HEIGHT = 36
BAR_BUTTON_MIN = 44
CORNER_RADIUS = 8
TEXT_INSET = (8, 6, 8, 6)        # top, left, bottom, right inside the text view
LINE_SPACING = 3.0
DRAFTS_STORE = 'textbox'
RESTORE_TITLE = '↺ Restore'
SPELL_TITLE = '🔤'

KEYBOARD_APPEARANCE_DARK = 1     # UIKeyboardAppearanceDark
SMART_PUNCTUATION_OFF = 1        # UITextSmartDashesTypeNo / SmartQuotesTypeNo


# --- The text view's comfort settings (from Jot) ---------------------------

def apply_readability(text_view):
    """Inset and line spacing ui.TextView does not expose. Line spacing goes
    through a copy of typingAttributes: replacing them wholesale drops the
    font and colour (typed text turned black on black in Jot)."""
    try:
        from objc_util import ObjCClass, UIEdgeInsets
        instance = text_view.objc_instance
        instance.setTextContainerInset_(UIEdgeInsets(*TEXT_INSET))
        style = ObjCClass('NSMutableParagraphStyle').alloc().init()
        style.setLineSpacing_(LINE_SPACING)
        attributes = instance.typingAttributes().mutableCopy()
        attributes.setObject_forKey_(
            style, ObjCClass('NSString').stringWithString_('NSParagraphStyle'))
        instance.setTypingAttributes_(attributes)
    except Exception as error:
        print('[editorkit.textbox] readability unavailable: %s' % error)


def apply_keyboard_comfort(text_view):
    """A dark keyboard, and smart dashes and quotes off."""
    try:
        instance = text_view.objc_instance
        instance.setKeyboardAppearance_(KEYBOARD_APPEARANCE_DARK)
        instance.setSmartDashesType_(SMART_PUNCTUATION_OFF)
        instance.setSmartQuotesType_(SMART_PUNCTUATION_OFF)
        instance.reloadInputViews()
    except Exception as error:
        print('[editorkit.textbox] keyboard settings unavailable: %s' % error)


# --- The tile -------------------------------------------------------------

class TextBox(Tile):

    def __init__(self, window, text='', name=None, name_placeholder='Name',
                 chips=(), draft_key=None, spellcheck=False):
        Tile.__init__(self, window)
        palette = self.palette
        self.draft_key = draft_key
        self.opened_text = text

        self.name_field = None
        if name is not None:
            self.name_field = style_field(ui.TextField(), palette, monospace=False)
            self.name_field.placeholder = name_placeholder
            from .field import tint_placeholder
            tint_placeholder(self.name_field, palette.dim)
            self.name_field.text = name
            self.add_subview(self.name_field)

        view = ui.TextView()
        view.font = FONT
        view.background_color = palette.background
        view.text_color = palette.text
        view.tint_color = palette.accent
        view.corner_radius = CORNER_RADIUS
        view.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        view.text = text
        view.delegate = self
        apply_readability(view)
        apply_keyboard_comfort(view)
        self.text_view = view
        self.add_subview(view)

        self.bar = ui.ScrollView()
        self.bar.shows_horizontal_scroll_indicator = False
        self.add_subview(self.bar)
        self.bar_buttons = []
        for title, action in (('⇥', self.indent), ('⇤', self.outdent),
                              ('↶', self.undo), ('↷', self.redo)):
            self.add_bar_button(title, action)
        self.spell_button = self.add_bar_button(SPELL_TITLE, self.toggle_spellcheck)
        self.set_spellcheck(spellcheck)
        for chip in chips:
            self.add_bar_button(chip, lambda chip=chip: self.insert(chip))
        draft = self.saved_draft()
        if draft and draft != text:
            self.restore_button = self.add_bar_button(RESTORE_TITLE, self.restore)

    # --- The bar ------------------------------------------------------------

    def add_bar_button(self, title, action):
        palette = self.palette
        button = ui.Button(title=title, font=BAR_FONT)
        button.background_color = palette.edge
        button.tint_color = palette.text
        button.corner_radius = CORNER_RADIUS
        button.action = lambda sender: action()
        self.bar.add_subview(button)
        self.bar_buttons.append(button)
        return button

    def insert(self, text):
        """Type text at the cursor, over any selection."""
        start, end = self.text_view.selected_range
        self.text_view.replace_range((start, end), text)
        self.select(start + len(text), start + len(text))
        self.save_draft()

    def select(self, start, end):
        """Set the selection, kept inside the view's actual text."""
        length = len(self.text_view.text)
        self.text_view.selected_range = (min(max(0, start), length), min(max(0, end), length))

    def shift(self, edit):
        """Indent or outdent through textops, replacing only the touched
        lines. If the view's text then differs from what textops computed
        (its ranges can disagree with Python's), the whole text is set."""
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
        self.save_draft()

    def set_spellcheck(self, on):
        """Spellcheck and autocorrect together: off for code, on for prose."""
        self.spellcheck = bool(on)
        view = self.text_view
        view.spellchecking_type = self.spellcheck
        view.autocorrection_type = self.spellcheck
        try:
            view.objc_instance.reloadInputViews()
        except Exception:
            pass
        palette = self.palette
        lit = self.spellcheck
        self.spell_button.background_color = palette.accent if lit else palette.edge
        self.spell_button.tint_color = palette.on_accent if lit else palette.text

    def toggle_spellcheck(self):
        self.set_spellcheck(not self.spellcheck)

    def indent(self):
        self.shift(textops.indent)

    def outdent(self):
        self.shift(textops.outdent)

    def undo(self):
        try:
            self.text_view.objc_instance.undoManager().undo()
        except Exception:
            pass

    def redo(self):
        try:
            self.text_view.objc_instance.undoManager().redo()
        except Exception:
            pass

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

    def restore(self):
        draft = self.saved_draft()
        if draft:
            self.text_view.text = draft

    def textview_did_change(self, text_view):
        self.save_draft()

    # --- Reading ------------------------------------------------------------

    @property
    def text(self):
        return self.text_view.text

    @property
    def name(self):
        return self.name_field.text if self.name_field is not None else None

    def layout(self):
        width = self.width
        y = PADDING
        if self.name_field is not None:
            self.name_field.frame = (PADDING, y, width - 2 * PADDING, NAME_HEIGHT)
            y += NAME_HEIGHT + GAP
        bar_y = self.height - PADDING - BAR_HEIGHT
        self.text_view.frame = (PADDING, y, width - 2 * PADDING, max(0, bar_y - GAP - y))
        self.bar.frame = (PADDING, bar_y, width - 2 * PADDING, BAR_HEIGHT)
        x = 0
        for button in self.bar_buttons:
            button_width = max(BAR_BUTTON_MIN, 14 + 10 * len(button.title))
            button.frame = (x, 0, button_width, BAR_HEIGHT)
            x += button_width + GAP
        self.bar.content_size = (x, BAR_HEIGHT)


# --- Opening --------------------------------------------------------------

def edit_text(text='', title='Edit', name=None, name_placeholder='Name', chips=(),
              on_done=None, on_cancel=None, draft_key=None, spellcheck=False,
              key=WINDOW_KEY, emoji=EMOJI):
    """Open a TextBox above the keyboard. ✓ calls on_done(text, name); ✕ or
    closing calls on_cancel(). spellcheck starts spellcheck and autocorrect
    on (🔤 in the bar toggles them). Returns the TextBox."""
    from ..windows import Window
    window = Window(title, emoji=emoji, key=key)
    box = TextBox(window, text, name, name_placeholder, chips, draft_key, spellcheck)
    window.add_page(title, box)
    finished = []

    def done(_window=None):
        if finished:
            return
        finished.append('done')
        result = (box.text, box.name)
        box.clear_draft()
        window.close()
        if on_done is not None:
            on_done(*result)

    def cancelled(_window=None, *details):
        if finished:
            return
        finished.append('cancel')
        if on_cancel is not None:
            on_cancel()

    window.add_button('✓', done, name='done')
    window.on('close', cancelled)
    window.show()
    window.move_to('above_dock', keyboard=False)
    window.when_still(lambda w: w.focus(box.text_view))
    return box
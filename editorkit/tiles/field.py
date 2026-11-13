"""Field: one line to type into, with an optional note and buttons at its end.

    field = tiles.Field(window, 'Search', on_change=typed, on_return=typed)
    field.add_button('⇡', widen)       # a tap calls widen(field)
    field.say('12')                    # a dim note before the buttons
    field.value(); field.set_value('x'); field.focus()

on_change(field, text) runs on every keystroke; on_return(field, text) when
Return is pressed, which also puts the keyboard away.
"""
import ui

from .base import GAP, PADDING, ROW_HEIGHT, Tile, make_button, style_field


# --- Settings -------------------------------------------------------------

NOTE_WIDTH = 64
NOTE_FONT = ('<system>', 12)


def tint_placeholder(text_field, colour):
    """Draw text_field's placeholder in colour. iOS draws it light grey,
    nearly invisible on a light theme's field (RELEASE.txt 1.2)."""
    try:
        from objc_util import ObjCClass, ObjCInstance, ns, sel
        inner = None
        for view in ObjCInstance(text_field).subviews():
            if view.respondsToSelector_(sel('setAttributedPlaceholder:')):
                inner = view
                break
        if inner is None:
            return
        red, green, blue, alpha = ui.parse_color(colour)
        tint = ObjCClass('UIColor').colorWithRed_green_blue_alpha_(red, green, blue, alpha)
        words = ObjCClass('NSAttributedString').alloc().initWithString_attributes_(
            ns(text_field.placeholder or ''), ns({'NSColor': tint}))
        inner.setAttributedPlaceholder_(words)
    except Exception:
        pass                         # the plain placeholder still shows


class Field(Tile):
    HEIGHT = ROW_HEIGHT + 2 * PADDING      # what a layout gives it

    def __init__(self, window, placeholder='', on_change=None, on_return=None,
                 monospace=True):
        Tile.__init__(self, window)
        self.on_change = on_change
        self.on_return = on_return
        self.buttons = []                  # [(button, width)], left to right

        self.text_field = style_field(ui.TextField(placeholder=placeholder),
                                      self.palette, monospace)
        tint_placeholder(self.text_field, self.palette.dim)
        self.text_field.delegate = self
        self.add_subview(self.text_field)

        self.note = ui.Label(font=NOTE_FONT, alignment=ui.ALIGN_RIGHT)
        self.note.text_color = self.palette.dim
        self.note.touch_enabled = False
        self.note.hidden = True
        self.add_subview(self.note)

    def restyle(self):
        """The theme changed: re-apply the field's colours and placeholder."""
        palette = self.palette
        self.text_field.background_color = palette.background
        self.text_field.text_color = palette.text
        self.text_field.tint_color = palette.accent
        tint_placeholder(self.text_field, palette.dim)

    # --- Using it ---------------------------------------------------------

    def value(self):
        return self.text_field.text or ''

    def set_value(self, text):
        self.text_field.text = text

    def focus(self):
        """Give the field the keyboard (once the window has stopped moving)."""
        self.window.focus(self.text_field)

    def unfocus(self):
        """Put the field's keyboard away."""
        self.text_field.end_editing()

    def textfield_should_begin_editing(self, textfield):
        """A field cannot take typing while its window sits in the keyboard's
        place (iOS swaps the window out for the keyboard), so a tap there
        brings the window back over the code first, then focuses."""
        if getattr(self.window, 'place', None) == 'dock':
            self.window.to_panel()
            self.focus()
            return False
        return True

    def add_button(self, title, action, width=None):
        button = make_button(title, lambda sender: action(self), self.palette)
        self.add_subview(button)
        self.buttons.append((button, width or ROW_HEIGHT))
        self.layout()
        return button

    def say(self, words):
        self.note.text = words or ''
        self.layout()

    # --- Drawing ----------------------------------------------------------

    def layout(self):
        top = (self.height - ROW_HEIGHT) / 2.0
        right = self.width - PADDING
        for button, width in reversed(self.buttons):
            right -= width
            button.frame = (right, top, width, ROW_HEIGHT)
            right -= GAP
        self.note.hidden = not self.note.text
        if self.note.text:
            right -= NOTE_WIDTH
            self.note.frame = (right, top, NOTE_WIDTH, ROW_HEIGHT)
            right -= GAP
        self.text_field.frame = (PADDING, top, max(40, right - PADDING), ROW_HEIGHT)

    # --- Text field delegate ----------------------------------------------

    def textfield_did_change(self, textfield):
        if self.on_change:
            self.on_change(self, self.value())

    def textfield_should_return(self, textfield):
        if self.on_return:
            self.on_return(self, self.value())
        textfield.end_editing()
        return True
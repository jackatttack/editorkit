"""The tab a window is about to become, shown in Pythonista's tab row while
the window is dragged up past the tab line (gestures.py), so letting go is
never a surprise. It slides in where the new tab will land, outlined in the
accent colour, and fades away when the window is dragged back down or let
go (the real tab then appears in its place).

It lives on the app's root view: the code area clips at its top edge, so a
view there could never reach the tab row.
"""
import ui

from .. import _app
from .. import tabs as editor_tabs
from . import look


# --- Settings -------------------------------------------------------------

FONT = ('<system-bold>', 13)
MIN_WIDTH = 90
PADDING = 24                 # space either side of the words
SLIDE = 8                    # it slides down into place from this far above
BORDER = 1.5
CORNER = 6


class TabPreview:

    def __init__(self, palette):
        self.palette = palette
        self.view = None
        self.label = None
        self.showing = False

    def _build(self):
        palette = self.palette
        view = ui.View()
        view.touch_enabled = False
        view.corner_radius = CORNER
        view.border_width = BORDER
        view.border_color = palette.accent
        view.background_color = palette.panel
        label = ui.Label(font=FONT, alignment=ui.ALIGN_CENTER)
        label.text_color = palette.text
        label.flex = 'WH'
        label.touch_enabled = False
        view.add_subview(label)
        self.view, self.label = view, label

    @_app.on_main
    def show(self, text):
        if self.showing:
            return
        if self.view is None:
            self._build()
        root = _app.root().view()
        width = max(MIN_WIDTH, ui.measure_string(text, font=FONT)[0] + PADDING)
        slot = editor_tabs.new_tab_slot(root, width)
        if slot is None:
            return
        x, y, width, height = slot
        view, label = self.view, self.label
        label.text = text
        view.frame = (x, y - SLIDE, width, height)
        label.frame = (0, 0, width, height)
        view.alpha = 0.0
        if view.objc_instance.superview() is None:
            root.addSubview_(view.objc_instance)
        self.showing = True

        def slide_in():
            view.alpha = 1.0
            view.y = y
        ui.animate(slide_in, look.LIFT_SECONDS)

    @_app.on_main
    def hide(self):
        if not self.showing or self.view is None:
            return
        self.showing = False
        view = self.view
        ui.animate(lambda: setattr(view, 'alpha', 0.0), look.LIFT_SECONDS)

        def remove():
            if not self.showing:
                view.objc_instance.removeFromSuperview()
        ui.delay(remove, look.LIFT_SECONDS + 0.05)
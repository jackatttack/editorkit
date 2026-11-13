"""Full screen for windows: a window's page presented as a Pythonista sheet.

＋ in a window's header (look.FULL_BUTTON) folds the window to its pin and
presents its current page with Pythonista's own present(), so it covers the
title bar and tabs (look.FULL_STYLE: 'fullscreen' by default, which no swipe
can dismiss; 'sheet' for a card). The page goes with its window's accessory
strip (Search's field, Files' path) and any window sheet (show_sheet), laid
out as the panel lays them: header, accessory, page, sheet over the page.
win.show_sheet while full screen shows here.

⤡ in the header, − on the window, or closing the sheet gives every part
back to its window: the same objects, so their state (scroll, a game in
progress, typed text) is just as it was.

Pythonista's own title bar is hidden: this draws the window's header
(Panel's button style and sizes, windows/views.py), ⤡ first, then the
window's own buttons, the title and emoji on the right, below the safe
area; the page keeps clear of the home indicator.
"""
import time

import ui

from . import look, places


TITLE_FONT = ('<system-bold>', 17)
EMOJI_FONT = ('<system>', 22)
BUTTON_FONT = ('<system-bold>', 15)       # as Panel._button

# A 'fullscreen' presentation takes the editor off screen, and the windows
# clock (driven from the editor's views) stops with it: taps on a web page
# (links the tile handles on its clock) were queued and never run, while
# the page's own script (the pinch) kept working. So the sheet drives the
# window's page clock itself, on the same schedule (window.next_page_tick):
# whichever clock comes first ticks, so nothing runs twice.
CLOCK_SECONDS = 1.0 / 30


class FullSheet(ui.View):

    def __init__(self, window, page_view, accessory=None, overlay=None):
        self.window = window
        self.page_view = page_view
        self.accessory = accessory       # the window's (view, height) strip, or None
        self.overlay = None              # the window's sheet over the page, or None
        self.leaving = False             # set when the window closes the sheet itself
        self.palette = window.palette
        self.background_color = self.palette.panel

        self.header = ui.View(background_color=self.palette.panel)
        self.add_subview(self.header)
        self.buttons = []
        self.add_header_button(look.FULL_EXIT_ICON, self.back_tapped)
        for spec in window.app_buttons:
            if spec['name'] != 'full':
                self.add_header_button(spec['icon'], self.action_for(spec))
        self.heading = ui.Label(font=TITLE_FONT, alignment=ui.ALIGN_RIGHT,
                                text_color=self.palette.text)
        self.emoji = ui.Label(font=EMOJI_FONT, alignment=ui.ALIGN_CENTER)
        self.header.add_subview(self.heading)
        self.header.add_subview(self.emoji)

        self.add_subview(page_view)
        if accessory is not None:
            self.add_subview(accessory[0])
        self.set_overlay(overlay)
        self.refresh()
        self.update_interval = CLOCK_SECONDS

    # --- Parts ------------------------------------------------------------

    def add_header_button(self, icon, action):
        """A header button in the window's style (Panel._button)."""
        button = ui.Button(title=icon, font=BUTTON_FONT)
        button.background_color = self.palette.background
        button.tint_color = self.palette.accent
        button.corner_radius = 8
        button.action = action
        self.header.add_subview(button)
        self.buttons.append(button)

    def action_for(self, spec):
        def tapped(sender):
            spec['action'](self.window)
        return tapped

    def set_overlay(self, view):
        """The window's sheet over the page (Window.show_sheet routes here
        while full screen); None takes it away."""
        if self.overlay is not None and self.overlay is not view:
            places.take_away(self.overlay)
        self.overlay = view
        if view is not None:
            if view.objc_instance.superview() is None:
                self.add_subview(view)
            view.bring_to_front()
        self.layout()                    # ui.View has no set_needs_layout

    def parts(self):
        """Every view the window lent: given back by leave_full."""
        views = [self.page_view]
        if self.accessory is not None:
            views.append(self.accessory[0])
        if self.overlay is not None:
            views.append(self.overlay)
        return views

    def refresh(self):
        """Title and emoji from the window (set_title calls this)."""
        self.heading.text = self.window.title
        self.emoji.text = self.window.emoji

    # --- Clock and layout -------------------------------------------------

    def update(self):
        """The page clock while the sheet is up (see CLOCK_SECONDS)."""
        window = self.window
        now = time.time()
        if now < window.next_page_tick:
            return
        window.next_page_tick = now + look.FULL_PAGE_TICK_SECONDS
        window._tick_pages(now)

    def safe_insets(self):
        """(top, bottom) the screen keeps for the status bar and the home
        indicator; 0 where there is none (a 'sheet' card)."""
        try:
            insets = self.objc_instance.safeAreaInsets(restype=places.UIEdgeInsets,
                                                        argtypes=[])
            return float(insets.top), float(insets.bottom)
        except Exception:
            return 0.0, 0.0

    def layout(self):
        width = self.width
        top, bottom = self.safe_insets()
        header_height = look.HEADER_HEIGHT
        size, gap = look.HEADER_BUTTON_SIZE, look.HEADER_BUTTON_GAP

        self.header.frame = (0, top, width, header_height)
        x = look.EDGE
        y = (header_height - size) / 2.0
        for button in self.buttons:
            button.frame = (x, y, size, size)
            x += size + gap
        emoji_width = look.EMOJI_GRIP_WIDTH
        self.emoji.frame = (width - look.EDGE - emoji_width, 0, emoji_width, header_height)
        self.heading.frame = (x + gap, 0,
                              max(0, width - look.EDGE - emoji_width - x - 2 * gap),
                              header_height)

        y = top + header_height
        if self.accessory is not None:
            view, height = self.accessory
            view.frame = (0, y, width, height)
            y += height
        page_frame = (0, y, width, max(0, self.height - bottom - y))
        self.page_view.frame = page_frame
        if self.overlay is not None:
            self.overlay.frame = page_frame

    # --- Leaving ------------------------------------------------------------

    def back_tapped(self, sender):
        self.window.leave_full()

    def will_close(self):
        # Closed by Pythonista itself (a 'sheet' card swiped away): give the
        # parts back.
        if not self.leaving:
            self.window.leave_full(sheet_closing=True)
"""The window's views: the pin, the panel shell and its grips.

They read touches and lay themselves out; every decision is the Window's
(window.py). Touch rules: library/guides/pythonista-ui-stability.md,
Gestures over the editor.
"""
import time

import ui

from . import look


def view_for(thing, window):
    """Moved to content.py; kept so older imports keep working."""
    from .content import view_for as make_view
    return make_view(thing, window)


class Pin(ui.View):
    """A window at rest: its emoji (and words, if any) in a small pill.
    A tap opens the window; a still hold lifts the pin to drag it."""

    def __init__(self, window, palette):
        self.window = window
        self.background_color = look.CLEAR      # the clear rim widens the touch target
        soft = look.PIN_STYLE == 'soft'
        self.pill = ui.View(background_color=palette.panel if soft else palette.accent)
        if soft:
            self.pill.border_width = 1
            self.pill.border_color = palette.edge
        self.pill.touch_enabled = False
        self.add_subview(self.pill)
        self.label = ui.Label(font=look.PIN_FONT,
                              text_color=palette.text if soft else palette.on_accent,
                              alignment=ui.ALIGN_CENTER, text=window.emoji)
        self.label.touch_enabled = False
        self.pill.add_subview(self.label)
        self.pressed_at = None    # set while a touch may still become a tap or a hold
        self.travel = 0.0
        self.dragging = False

    def set_text(self, text):
        self.label.text = text

    def restyle(self, palette):
        """Re-apply palette's colours (the theme changed)."""
        soft = look.PIN_STYLE == 'soft'
        self.pill.background_color = palette.panel if soft else palette.accent
        if soft:
            self.pill.border_color = palette.edge
        self.label.text_color = palette.text if soft else palette.on_accent

    def layout(self):
        width = max(0, self.width - 2 * look.TOUCH_PAD)
        height = max(0, self.height - 2 * look.TOUCH_PAD)
        self.pill.frame = (look.TOUCH_PAD, look.TOUCH_PAD, width, height)
        self.pill.corner_radius = height / 2.0
        self.label.frame = (0, 0, width, height)

    def touch_began(self, touch):
        self.pressed_at = time.time()
        self.travel = 0.0
        self.speed_x = 0.0            # sideways speed while dragged, for throws
        self.last_time = touch.timestamp

    def touch_moved(self, touch):
        step_x = touch.location.x - touch.prev_location.x
        step_y = touch.location.y - touch.prev_location.y
        if self.dragging:
            elapsed = max(0.001, touch.timestamp - self.last_time)
            self.last_time = touch.timestamp
            self.speed_x = 0.6 * (step_x / elapsed) + 0.4 * self.speed_x
            self.window._drag_pin(step_x, step_y)
            return
        self.travel += abs(step_x) + abs(step_y)
        if self.travel > look.SLOP:
            self.pressed_at = None            # moved first: neither a tap nor a hold

    def touch_ended(self, touch):
        if self.dragging:
            self.window._drop_pin(getattr(self, 'speed_x', 0.0))
        elif self.pressed_at is not None and time.time() - self.pressed_at < look.HOLD_SECONDS:
            self.window.show()
        self.pressed_at = None


class Grip(ui.View):
    """A grab area on the panel.

    job 'move': a still hold picks the panel up to drag it (or, in the
    keyboard's place, to pull it back out); the windows clock notices the
    hold. The header's emoji also minimises on a tap (taps_minimise); the
    backdrop behind every control ignores taps.
    job 'resize': the bottom-right corner, which pulls straight away.
    """

    def __init__(self, window, job, glyph=None, colour='white',
                 font=('<system>', 15), alignment=ui.ALIGN_RIGHT, taps_minimise=False):
        self.window = window
        self.job = job
        self.taps_minimise = taps_minimise
        self.background_color = look.CLEAR
        self.pressed_at = None
        self.travel = 0.0
        self.mark = None
        if glyph:
            self.mark = ui.Label(text=glyph, font=font, text_color=colour, alignment=alignment)
            self.mark.touch_enabled = False
            self.add_subview(self.mark)

    def layout(self):
        if self.mark is None:
            return
        if self.job == 'resize':
            self.mark.frame = (0, self.height - 24, self.width - 6, 20)
        else:
            self.mark.frame = (0, 0, self.width, self.height)

    def touch_began(self, touch):
        self.speed_x = 0.0            # sideways speed while held, for flings
        self.last_time = touch.timestamp
        if self.job == 'resize':
            self.window._grab('resize')
            return
        self.pressed_at = time.time()
        self.travel = 0.0

    def touch_moved(self, touch):
        step_x = touch.location.x - touch.prev_location.x
        step_y = touch.location.y - touch.prev_location.y
        if self.window.grabbing == self.job:
            elapsed = max(0.001, touch.timestamp - self.last_time)
            self.last_time = touch.timestamp
            # Smoothed, so one jittery step does not decide a throw.
            self.speed_x = 0.6 * (step_x / elapsed) + 0.4 * self.speed_x
            self.window._pull(self.job, step_x, step_y)
            return
        self.travel += abs(step_x) + abs(step_y)
        if self.travel > look.SLOP:
            self.pressed_at = None

    def touch_ended(self, touch):
        if self.window.grabbing == self.job:
            self.window._release(self.job, getattr(self, 'speed_x', 0.0))
        elif (self.taps_minimise and self.pressed_at is not None
                and time.time() - self.pressed_at < look.HOLD_SECONDS):
            self.window.minimise()
        self.pressed_at = None


# Header buttons, from the window's outside edge inward. When a narrow
# window cannot fit them all, the last ones drop out first.
BUTTON_ORDER = ('close', 'minimise', 'console', 'dock')


class Panel(ui.View):
    """The window's shell: header (emoji, title, Keyboard, ✕), tabs when there
    is more than one page, the page, and the resize corner. Everything sits on
    .content so it can fade as one while the panel grows or shrinks."""

    def __init__(self, window, palette):
        self.window = window
        self.palette = palette
        self.place = 'float'
        self.side = 'left'            # which end of the header the emoji sits at
        self.last_layout = None
        self.page_view = None
        self.tabs = []
        self.background_color = palette.panel
        self.border_color = palette.edge
        self.border_width = 1
        self.corner_radius = look.CORNER_RADIUS
        self.content = ui.View(background_color=look.CLEAR)
        self.add_subview(self.content)
        # Behind every control: hold any empty part of the panel to drag it.
        self.backdrop = Grip(window, 'move')
        self.content.add_subview(self.backdrop)
        self.heading = ui.Label(font=('<system-bold>', 15), text_color=palette.text)
        self.heading.touch_enabled = False
        self.content.add_subview(self.heading)
        # The standard header buttons, from the outside edge inward. Which show
        # depends on where the window is (wanted_buttons) and how wide it is.
        self.buttons = {}
        for name in BUTTON_ORDER:
            self.buttons[name] = self._button()
        self.buttons['close'].title = '✕'
        self.buttons['close'].action = lambda sender: window.close()
        self.buttons['minimise'].title = '–'
        self.buttons['minimise'].action = lambda sender: window.minimise()
        self.emoji = Grip(window, 'move', glyph=window.emoji, colour=palette.text,
                          font=('<system>', 22), alignment=ui.ALIGN_CENTER, taps_minimise=True)
        self.content.add_subview(self.emoji)
        self.resizer = Grip(window, 'resize', glyph='◢', colour=palette.dim)
        self.content.add_subview(self.resizer)
        # Set by the window: a strip under the tabs, and a sheet over the pages.
        self.accessory = None
        self.accessory_height = 0
        self.sheet = None
        # Behind the header, tabs and accessory: their own fill, so a tinted
        # or clear window (Window(backdrop=...)) keeps them readable over code.
        self.header_fill = ui.View(background_color=look.CLEAR)
        self.header_fill.touch_enabled = False
        self.content.add_subview(self.header_fill)
        self.header_fill.send_to_back()
        # The app's own header buttons (win.add_button), kept as 'app:<name>'.
        self.app_names = []
        self.sync_app_buttons()
        self.apply_backdrop()

    def _button(self):
        button = ui.Button(title='', font=('<system-bold>', 15))
        button.background_color = self.palette.background
        button.tint_color = self.palette.accent
        button.corner_radius = 8
        self.content.add_subview(button)
        return button

    def restyle(self):
        """Re-apply the palette's colours (the theme changed): frame, header,
        buttons, tabs, grips and backdrop."""
        palette = self.palette
        self.background_color = palette.panel
        self.border_color = palette.edge
        self.heading.text_color = palette.text
        for name, button in self.buttons.items():
            if not name.startswith('app:'):
                button.background_color = palette.background
                button.tint_color = palette.accent
        for grip, colour in ((self.emoji, palette.text), (self.resizer, palette.dim)):
            if hasattr(grip, 'colour'):
                grip.colour = colour
            for view in grip.subviews:
                if isinstance(view, ui.Label):
                    view.text_color = colour
            grip.set_needs_display()
        self.sync_app_buttons()           # app buttons, lit or not
        self.set_tabs(self.window.page_names(), self.window.page)
        self.apply_backdrop()

    def sync_app_buttons(self):
        """Match the header's app buttons to window.app_buttons, in the order
        added: create, restyle (lit when on) and remove as needed."""
        specs = self.window.app_buttons
        keys = ['app:' + spec['name'] for spec in specs]
        for key in [key for key in self.buttons if key.startswith('app:') and key not in keys]:
            self.content.remove_subview(self.buttons.pop(key))
        for key, spec in zip(keys, specs):
            button = self.buttons.get(key)
            if button is None:
                button = self._button()
                self.buttons[key] = button
            button.title = spec['icon']
            button.action = self._app_action(spec['action'])
            lit = bool(spec['on'])
            button.background_color = self.palette.accent if lit else self.palette.background
            button.tint_color = self.palette.panel if lit else self.palette.accent
        self.app_names = keys
        self.resizer.bring_to_front()
        self.last_layout = None
        self.layout()

    def _app_action(self, action):
        """A button action that calls action(window) and never raises."""
        window = self.window

        def tapped(sender):
            try:
                action(window)
            except Exception as error:
                print('editorkit windows: header button failed: %r' % (error,))
        return tapped

    # ---- Set by the window ----

    def show_place(self, place):
        """'float' (over the code), 'console' (over the console) or 'dock'
        (in the keyboard's place): the console and keyboard buttons say where
        they would send the window from here."""
        self.place = place
        window = self.window
        keyboard, console = self.buttons['dock'], self.buttons['console']
        if place == 'dock':
            keyboard.title = '⇡'
            keyboard.action = lambda sender: window.to_panel()
        else:
            keyboard.title = '⌨'
            keyboard.action = lambda sender: window.to_dock()
        if place == 'console':
            console.title = '{ }'
            console.action = lambda sender: window.to_panel()
        else:
            console.title = '>_'
            console.action = lambda sender: window.to_console()
        self.corner_radius = 0 if place == 'dock' else look.CORNER_RADIUS
        resizable = place != 'dock'
        self.resizer.touch_enabled = resizable
        self.resizer.hidden = not resizable
        self.last_layout = None
        self.layout()

    def wanted_buttons(self):
        """The header buttons that make sense where the window is, from the
        outside edge in: close, minimise, the app's own (as added), console,
        keyboard. A narrow window drops them from the inner end first."""
        window = self.window
        wanted = []
        if window.closable:
            wanted.append('close')
        wanted.append('minimise')
        wanted.extend(self.app_names)
        if self.place != 'dock' and window.can_use_console():
            wanted.append('console')
        # Keyboard is opt-in (dragging past the dock line still docks), but in
        # the keyboard's place it is the way back out, so it always shows there.
        if (self.place != 'console' and window.allows_dock
                and (window.dock_button or self.place == 'dock')):
            wanted.append('dock')
        return wanted

    def set_side(self, side):
        """Put the emoji at the 'left' or 'right' end of the header."""
        if side != self.side:
            self.side = side
            self.last_layout = None
            self.layout()

    def set_tabs(self, names, current):
        names = list(names)
        wanted = names if len(names) > 1 else []
        if [tab.title for tab in self.tabs] != wanted:
            for tab in self.tabs:
                self.content.remove_subview(tab)
            self.tabs = []
            for name in wanted:
                tab = ui.Button(title=name, font=('<system>', 13))
                tab.corner_radius = 8
                tab.action = self.tab_tapped
                self.content.add_subview(tab)
                self.tabs.append(tab)
            self.resizer.bring_to_front()
            self.last_layout = None
            self.layout()
        for tab in self.tabs:
            chosen = tab.title == current
            tab.tint_color = self.palette.accent if chosen else self.palette.dim
            tab.background_color = self.palette.background if chosen else look.CLEAR

    def tab_tapped(self, sender):
        self.window.set_page(sender.title)

    def show_page(self, view):
        if view is self.page_view:
            return
        if self.page_view is not None:
            self.content.remove_subview(self.page_view)
        self.page_view = view
        if view is not None:
            self.content.add_subview(view)
            self.resizer.bring_to_front()
        self.last_layout = None
        self.layout()

    def set_accessory(self, view, height):
        """A strip under the tabs, shared by every page; None removes it."""
        if self.accessory is not None and self.accessory is not view:
            self.content.remove_subview(self.accessory)
        self.accessory = view
        self.accessory_height = height if view is not None else 0
        if view is not None and view.objc_instance.superview() is None:
            self.content.add_subview(view)
        self.resizer.bring_to_front()
        self.last_layout = None
        self.layout()

    def show_sheet(self, view):
        """Lay view over the page area; None takes the sheet away."""
        if self.sheet is not None and self.sheet is not view:
            self.content.remove_subview(self.sheet)
        self.sheet = view
        if view is not None:
            if view.objc_instance.superview() is None:
                self.content.add_subview(view)
            view.bring_to_front()
            self.resizer.bring_to_front()
        self.last_layout = None
        self.layout()

    def apply_backdrop(self):
        """Fill the panel for Window(backdrop=...): 'solid'; 'tinted' (the page
        area at backdrop_alpha, code showing through); or 'clear' (no fill in
        the page area). Tinted and clear keep a fill behind the header, tabs
        and accessory, and the thin border."""
        mode = getattr(self.window, 'backdrop', 'solid')
        red, green, blue, _ = ui.parse_color(self.palette.panel)
        if mode == 'solid':
            self.background_color = (red, green, blue, 1.0)
            self.header_fill.hidden = True
            return
        alpha = self.window.backdrop_alpha if mode == 'tinted' else 0.0
        self.background_color = (red, green, blue, alpha)
        self.header_fill.background_color = (red, green, blue, look.HEADER_FILL_ALPHA)
        self.header_fill.hidden = False
        # Keep the header fill inside the rounded corners.
        self.objc_instance.layer().setMasksToBounds_(True)

    def refresh(self):
        self.heading.text = self.window.title

    # ---- Layout ----

    def layout(self):
        # UIKit calls layout() whenever subviews change, so only lay out when
        # something that matters changed (stability guide: snaps cut animations).
        width, height = self.width, self.height
        wanted = self.wanted_buttons()
        key = (width, height, self.side, self.place, len(self.tabs),
               self.page_view is not None, tuple(wanted),
               id(self.accessory), self.accessory_height, id(self.sheet))
        if key == self.last_layout:
            return
        self.last_layout = key
        self.content.frame = (0, 0, width, height)
        self.backdrop.frame = (0, 0, width, height)
        inset, grip = look.EDGE - 6, look.EMOJI_GRIP_WIDTH
        size, gap = look.HEADER_BUTTON_SIZE, look.HEADER_BUTTON_GAP
        # As many buttons as fit beside the emoji; the last ones drop out first.
        room = width - look.EDGE - (inset + grip + 2)
        shown = wanted[:max(0, int((room + gap) // (size + gap)))]
        for name, button in self.buttons.items():
            button.hidden = name not in shown
        button_y = (look.HEADER_HEIGHT - size) / 2.0
        if self.side == 'left':
            self.emoji.frame = (inset, 0, grip, look.HEADER_HEIGHT)
            right = width - look.EDGE
            for name in shown:
                self.buttons[name].frame = (right - size, button_y, size, size)
                right -= size + gap
            left = inset + grip + 2
            self.heading.alignment = ui.ALIGN_LEFT
        else:
            self.emoji.frame = (width - inset - grip, 0, grip, look.HEADER_HEIGHT)
            left = look.EDGE
            for name in shown:
                self.buttons[name].frame = (left, button_y, size, size)
                left += size + gap
            right = self.emoji.x - 2
            self.heading.alignment = ui.ALIGN_RIGHT
        self.heading.frame = (left, 0, max(0, right - left), look.HEADER_HEIGHT)
        self.heading.hidden = right - left < 40
        top = look.HEADER_HEIGHT
        if self.tabs:
            tab_width = (width - 2 * look.EDGE) / float(len(self.tabs))
            tab_font = ('<system>', 13 if tab_width >= 72 else 11)
            for number, tab in enumerate(self.tabs):
                tab.frame = (look.EDGE + number * tab_width, top, max(0, tab_width - 4), look.TAB_HEIGHT)
                tab.font = tab_font
            top += look.TAB_HEIGHT
        if self.accessory is not None:
            self.accessory.frame = (look.EDGE, top + 4, max(0, width - 2 * look.EDGE),
                                    self.accessory_height)
            self.accessory.hidden = height - top < self.accessory_height + 8
            top += 4 + self.accessory_height
        self.header_fill.frame = (0, 0, width, top + 4)
        # The page and the sheet share the page area; the sheet lies on top.
        page_height = height - top - 4 - look.EDGE
        page_frame = (look.EDGE, top + 4, max(0, width - 2 * look.EDGE), max(0, page_height))
        for view in (self.page_view, self.sheet):
            if view is not None:
                view.frame = page_frame
                view.hidden = page_height < 8
        # Big enough for a fingertip pushed into a screen corner, but never
        # more than half the space under the header, so short windows (the
        # Find bar) keep their bottom-right controls tappable.
        handle = max(look.HANDLE_MIN_SIZE,
                     min(look.HANDLE_SIZE, (height - look.HEADER_HEIGHT) / 2.0))
        self.resizer.frame = (width - handle, height - handle, handle, handle)
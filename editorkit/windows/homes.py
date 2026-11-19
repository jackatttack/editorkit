"""Homes Part of Window: see window.py."""
import ui

from .. import _app
from . import look, places, rules
from .state import FRAME_HOMES, KEYBOARD_RETRY_SECONDS, _remembered


class Homes(object):
    """Where a window lives: its home and its frames over the code and the
    console, the pin's place, moving there by code (move_to, go_home),
    following a tab switch, and waiting for a move to land (when_still,
    focus)."""

    # --- Homes ----------------------------------------------------------

    @staticmethod
    def _current_name(name):
        """A place, home or event name as given; frames (x, y, w, h) pass
        through. The one place to map names if they ever change again."""
        return name

    @_app.on_main
    def move_to(self, frame, keyboard=None):
        """Over the code at frame: 'top_bar', 'above_dock', 'panel' or an
        (x, y, w, h). Already over the code, it glides there; from a pin or
        the keyboard's place, it travels there. The frame is remembered.
        keyboard=True brings the editor's keyboard up once it lands, False
        leaves it; None does so only for 'above_dock', where Pythonista's
        key row is hidden too unless Window(keyboard_row='keep'). A window
        sent 'above_dock' then rides the real keyboard (key row
        included) until grabbed by hand."""
        frame = self._current_name(frame)
        target = self._clamp(self._frame_for(frame))
        _remembered('frames')[self.key] = target
        self.riding = frame == 'above_dock'
        if self.place == 'panel' and not self._busy():
            panel = self.panel
            ui.animate(lambda: setattr(panel, 'frame', target), look.GROW_SECONDS)
        else:
            self.open_exact = True
            self.to_panel()
        if keyboard is None:
            keyboard = frame == 'above_dock'
        if keyboard:
            self.hide_row_next = (frame == 'above_dock' and self.keyboard_row == 'hide')
            self._raise_keyboard_when_still()
        return self

    def ride_dock(self, fill=False):
        """Sit just above whatever is in the keyboard's place (the keyboard,
        or a window docked there), over the code or in the console, until
        grabbed by hand or stop_riding(). fill=True also grows the window to
        fill the space above it, below the status bar. The Manager's clock
        keeps it there as the keyboard comes, goes or changes height."""
        if self.place in ('hidden', 'closed', 'pin', 'tray'):
            self.show()
        self.ride_fill = fill
        self.riding = True
        return self

    def stop_riding(self):
        """Stay where it is now, whatever the keyboard does."""
        self.riding = False
        self.ride_fill = False
        return self

    def _raise_keyboard_when_still(self):
        """Bring the editor's keyboard up once no move is running (leaving the
        keyboard's place hands the key row back first), hiding Pythonista's
        key row first when move_to asked for it."""
        if self.manager is None or self.place in ('hidden', 'closed'):
            return
        if self._busy():
            self.manager.timeline.book(KEYBOARD_RETRY_SECONDS, 'keyboard up',
                                       self._raise_keyboard_when_still, self)
            return
        if self.hide_row_next:
            self.hide_row_next = False
            self.manager.dock.hide_key_row(self)
        places.bring_keyboard_up()

    def go_home(self):
        """Back to the window's home: the keyboard's place, its home frame
        over the code, or (with no home) simply open."""
        if self.home == 'dock':
            return self.to_dock()
        if self.home in FRAME_HOMES:
            return self.move_to(self.home)
        return self.show()

    # --- Full screen (2026-11-12) ---------------------------------------

    def is_full(self):
        """True while the window fills the code area (to_full)."""
        return getattr(self, 'full', False)

    @_app.on_main
    @_app.on_main
    @_app.on_main
    def to_full(self):
        """Show the current page full screen as a Pythonista view (see
        fullsheet.py), with the window's accessory strip and any window
        sheet; the window folds to its pin meanwhile, its page clock still
        running. leave_full (⤡, −, or closing it) brings them all back."""
        if self.is_full() or self._busy():
            return self
        entry = self._entry(self.page)
        view = entry[2] if entry is not None else None
        if view is None:
            return self                  # no page on screen to lift
        from .fullsheet import FullSheet
        accessory = self.accessory       # (view, height) or None
        overlay = self.sheet
        self.minimise()                  # before self.full is set: minimise would leave_full
        for part in (view, accessory[0] if accessory else None, overlay):
            if part is not None:
                places.take_away(part)
        if self.panel is not None and getattr(self.panel, 'page_view', None) is view:
            self.panel.page_view = None
        try:
            sheet = FullSheet(self, view, accessory, overlay)
            self.full = True
            self.full_sheet = sheet
            self.full_view = view
            sheet.present(look.FULL_STYLE, hide_title_bar=True)
        except Exception as error:
            # Never leave a window half taken apart: give everything back.
            print('editorkit windows: full screen failed: %r' % (error,))
            self.full = False
            self.full_sheet = None
            self.full_view = None
            for part in (view, accessory[0] if accessory else None, overlay):
                if part is not None:
                    places.take_away(part)
            if self.panel is not None:
                self.panel.page_view = None
            self.show()
            self._reattach_parts()
            self.when_still(self._relayout_after_full)
            return self
        self._show_full_button()
        return self

    @_app.on_main
    @_app.on_main
    @_app.on_main
    def leave_full(self, sheet_closing=False):
        """Give the page, accessory strip and window sheet back to the window
        and open it where it was. sheet_closing: Pythonista is already
        closing the full-screen view."""
        if not self.is_full():
            return self
        sheet = getattr(self, 'full_sheet', None)
        view = getattr(self, 'full_view', None)
        self.full = False
        self.full_sheet = None
        self.full_view = None
        parts = sheet.parts() if sheet is not None else [view]
        for part in parts:
            if part is not None:
                places.take_away(part)
        if sheet is not None and not sheet_closing:
            sheet.leaving = True
            sheet.close()
        if self.panel is not None and getattr(self.panel, 'page_view', None) is view:
            self.panel.page_view = None  # so the panel adds the view again
        self.show()
        self._reattach_parts()
        self._show_full_button()
        self.when_still(self._relayout_after_full)
        return self

    def _reattach_parts(self):
        """The accessory strip and window sheet back into the panel: Panel's
        set_accessory and show_sheet re-add a view that has no superview."""
        panel = self.panel
        if panel is None:
            return
        if self.accessory is not None:
            panel.set_accessory(*self.accessory)
        try:
            panel.show_sheet(self.sheet)
        except Exception as error:
            print('editorkit windows: sheet back from full screen failed: %r' % (error,))

    @staticmethod
    def _relayout_after_full(window):
        """Panel.layout skips a layout whose key has not changed, and the key
        coming back from a sheet matched the folded one: the header stayed
        unlaid until a resize. Forget the key and lay out again."""
        panel = window.panel
        if panel is None:
            return
        panel.last_layout = None
        panel.sync_app_buttons()
        panel.refresh()
        panel.layout()

    def toggle_full(self, *sender):
        return self.leave_full() if self.is_full() else self.to_full()

    def _show_full_button(self):
        try:
            self.set_button('full', icon=look.FULL_EXIT_ICON if self.is_full() else look.FULL_ICON)
        except Exception:
            pass        # a window without the ＋ button

    def when_still(self, callback):
        """Call callback(window) once no move is running: at once if none
        is. For work that must wait for a move to land, such as focusing a
        field in a window that is still travelling."""
        if self.manager is None or not self._busy():
            callback(self)
            return self
        self.manager.timeline.book(KEYBOARD_RETRY_SECONDS, 'when still',
                                   lambda: self.when_still(callback), self)
        return self

    def focus(self, view):
        """Give view (a text field or text view in this window) the keyboard,
        once no move is running: the editor's keyboard is put away first, so
        typing goes to view and not into the code, and the keyboard is the
        plain one (no Pythonista key row, before and after focusing)."""
        def hand_over(window):
            places.put_keyboard_away()
            places.plain_keyboard(view)
            view.begin_editing()
            places.plain_keyboard(view)
        return self.when_still(hand_over)

    def _pin_frame(self):
        """The pin's whole frame in its home (editor or console), touch rim
        included. pin_place holds the pill's side, inset and top, so words that
        change keep its outer edge still."""
        text_width = ui.measure_string(self.pin.label.text or self.emoji, font=look.PIN_FONT)[0]
        width = min(look.PIN_MAX_WIDTH, max(look.PIN_HEIGHT, text_width + 24))
        area_width, area_height = self._home_size()
        side, inset, top = self.pin_place
        x = area_width - inset - width if side == 'right' else inset
        x = max(look.EDGE, min(x, area_width - look.EDGE - width))
        top = max(look.EDGE, min(top, area_height - look.EDGE - look.PIN_HEIGHT))
        pad = look.TOUCH_PAD
        return (x - pad, top - pad, width + 2 * pad, look.PIN_HEIGHT + 2 * pad)

    def _clamp(self, frame, area=None):
        """frame kept to min_size and inside area (width, height; default the editor)."""
        return rules.clamp(frame, area or places.editor_size(), self.min_size, look.EDGE)

    def _float_frame(self):
        """Where it was left over the code; else its home's frame; else its
        first size under the top edge."""
        stored = _remembered('frames').get(self.key)
        if stored:
            return self._clamp(stored)
        if self.home in FRAME_HOMES:
            return self._clamp(self._frame_for(self.home))
        return self._clamp(self._frame_for('panel'))

    def _frame_for(self, frame):
        """A frame over the code from a home name or an (x, y, w, h)."""
        if not isinstance(frame, str):
            return tuple(frame)
        editor_width, editor_height = places.editor_size()
        width = editor_width - 2 * look.EDGE
        if frame == 'top_bar':
            height = self.size[1] if self.size else look.TOP_BAR_HEIGHT
            return (look.EDGE, look.EDGE, width, height)
        if frame == 'above_dock':
            height = self.size[1] if self.size else look.ABOVE_KEYBOARD_HEIGHT
            keyboard = places.keyboard_top()
            if keyboard is None:
                keyboard = editor_height - look.KEYBOARD_HEIGHT
            top = keyboard - height - look.EDGE
            return (look.EDGE, max(look.EDGE, top), width, height)
        if frame == 'panel':
            width, height = self.size or (
                min(width, look.DEFAULT_MAX_WIDTH),
                min(round(editor_height * look.DEFAULT_HEIGHT_SHARE), look.DEFAULT_MAX_HEIGHT))
            return (look.EDGE, look.EDGE, width, height)
        raise ValueError('unknown home %r: use %s, panel or (x, y, w, h)'
                         % (frame, ', '.join(FRAME_HOMES)))

    def _dock_frame(self):
        editor_width, editor_height = places.editor_size()
        return (0, editor_height - look.KEYBOARD_HEIGHT, editor_width, look.KEYBOARD_HEIGHT)

    def _emoji_offset(self):
        """Where the pin's pill sits from the panel's top corner so it covers
        the header's emoji (Panel.layout puts the emoji grip at EDGE - 6)."""
        return (look.EDGE - 6 + (look.EMOJI_GRIP_WIDTH - look.PIN_HEIGHT) / 2.0,
                (look.HEADER_HEIGHT - look.PIN_HEIGHT) / 2.0)

    def _emoji_place(self):
        """The pin place that puts the pill over the panel's emoji now, in the
        panel's area (editor or console)."""
        x, y, width, _ = places.frame_of(self.panel)
        offset_x, offset_y = self._emoji_offset()
        if self.panel.side == 'right':
            area_width, _ = self._home_size(self._host_of_panel())
            return ('right', area_width - (x + width) + offset_x, y + offset_y)
        return ('left', x + offset_x, y + offset_y)

    def _open_frame(self):
        """Its remembered size for the pin's home, placed so its emoji lands
        where the pin is (kept inside that area). A frame-home window, or one
        sent by move_to, opens exactly on its stored frame instead."""
        home = self.pin_home
        if home == 'editor' and (self.open_exact or self.home in FRAME_HOMES):
            self.open_exact = False
            return self._float_frame()
        base = self._console_frame() if home == 'console' else self._float_frame()
        _, _, width, height = base
        pin_x, pin_y, pin_width, _ = self._pin_frame()
        offset_x, offset_y = self._emoji_offset()
        top = pin_y + look.TOUCH_PAD - offset_y
        if self.pin_place[0] == 'right':
            left = pin_x + pin_width - look.TOUCH_PAD + offset_x - width
        else:
            left = pin_x + look.TOUCH_PAD - offset_x
        return self._clamp((left, top, width, height), self._home_size(home))

    def _set_pin_place(self, place):
        self.pin_place = place
        _remembered('pins')[self.key] = place
        self.under_key = None
        self.pin.set_text(self.pin_text())

    def _home_size(self, home=None):
        """(width, height) of the pin's home, or of the home given."""
        home = home or self.pin_home
        return places.console_size() if home == 'console' else places.editor_size()

    def _put_in(self, view, home):
        if home == 'console':
            places.over_console(view)
        else:
            places.over_editor(view)

    def _host_of_panel(self):
        return 'console' if self.place == 'console' else 'editor'

    def follow_editor(self):
        """Move what rests over the code (pin, panel, dock line) into the
        editor view showing now; frames carry over, as every tab is the same
        size. Views in the console or the keyboard's place are left alone."""
        for view in (self.pin, self.panel, self.dock_line):
            if view is None:
                continue
            parent = view.objc_instance.superview()
            if parent is not None and _app.class_name(parent) == 'OMTextEditorView':
                places.over_editor(view)

    def _set_pin_home(self, home):
        self.pin_home = home
        _remembered('pin_homes')[self.key] = home
        self.under_key = None

    def _place_from_frame(self, frame, area_width, snap):
        """A pin place (side, inset, top) from a pin's whole frame in an area."""
        return rules.place_from_frame(frame, area_width, look.PIN_HEIGHT, snap, look.EDGE)

    def _console_frame(self):
        """Where it was left over the console, or its editor size near the top."""
        area = places.console_size()
        stored = _remembered('console_frames').get(self.key)
        if stored:
            return self._clamp(stored, area)
        _, _, width, height = self._float_frame()
        return self._clamp((look.EDGE, look.EDGE + 60, width, height), area)

    def _crossing_frame(self, side):
        """Its frame as it crosses into side ('console' or 'editor'): the size
        it has now, at the spot it was last left on that side (kept inside
        the area). Remembered there, so opening from a pin on that side
        matches. Jack: a window keeps its size between console and editor."""
        _, _, width, height = places.frame_of(self.panel)
        if side == 'console':
            x, y, _, _ = self._console_frame()
            frame = self._clamp((x, y, width, height), places.console_size())
            _remembered('console_frames')[self.key] = frame
        else:
            x, y, _, _ = self._float_frame()
            frame = self._clamp((x, y, width, height))
            _remembered('frames')[self.key] = frame
        return frame

    def _fling_side(self, speed_x):
        """'right' or 'left' for a fling; a fling lines a pin or panel up with the
        edge it was flung at, and never crosses over (_check_edge does that)."""
        return rules.fling_side(speed_x, look.FLING_SPEED)

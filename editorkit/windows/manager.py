"""The Manager: the one clock for every window, and what they share:
the timeline, the keyboard's place, the side-swipe switch. Each tick
it runs booked steps, follows tab switches, keeps the code inset and
the key row right, ticks every window, keeps pins clear and keeps
windows riding the keyboard. Restoring shared state is the clock's
job, never each exit path's."""
import time

import ui

from .. import _app
from . import look, places, rules
from .motion import Timeline
from .state import EDITOR_CHECK_SECONDS, _store, _remembered


FILL_MIN_HEIGHT = 100        # riding with fill: below this, leave the window be
class Manager(ui.View):
    """The one clock for every window, and what they share: the timeline,
    the keyboard's place and the side-swipe switch. Invisible."""

    def __init__(self):
        self.background_color = look.CLEAR
        self.frame = (0, 0, 1, 1)
        self.touch_enabled = False
        self.timeline = Timeline()
        self.dock = places.DockPlace()
        self.swipes = places.SwipeBlock()
        self.windows = {}             # key -> Window
        self.tray = []                # keys of minimised windows, most recent first
        self.palette = look.palette()
        self.failures = 0
        self.editor_pointer = None    # the editor view windows last rested in
        self.next_editor_check = 0.0
        self.inset_pointer = None     # the text view whose top inset we manage
        self.base_inset = 0.0         # its own top inset before ours
        self.update_interval = look.TICK_SECONDS

    def update(self):
        if self.objc_instance.superview() is None:
            return
        self._guard('theme', self.check_theme)
        try:
            self.tick()
        except Exception as error:
            self.failures += 1
            if self.failures <= 5:
                import traceback
                print('editorkit windows: tick failed: %r' % (error,))
                traceback.print_exc()

    def tick(self):
        """One beat of the clock. Each stage runs under its own guard, so a
        stage that fails (say, during a tab switch, while the editor view is
        briefly missing) never stops the others: above all, windows and
        their pages keep ticking."""
        for _, name, step, _owner in self.timeline.due():
            self._guard('step %s' % name, step)
        now = time.time()
        if now >= self.next_editor_check:
            self.next_editor_check = now + EDITOR_CHECK_SECONDS
            self._guard('follow_editor', self.follow_editor)
            self._guard('follow_tabs', self.follow_tabs)
            self._guard('check_code_inset', self.check_code_inset)
        self._guard('check_key_row', self.check_key_row)
        self._guard('keyboard_row', self.dock.keep_row_off)
        dragging = False
        for window in list(self.windows.values()):
            self._guard('window %s' % window.key, window.tick, now)
            dragging = dragging or window.is_dragging()
        self._guard('arrange_pins', self.arrange_pins)
        self._guard('keep_riders_on_dock', self.keep_riders_on_dock)
        if self.swipes.active and not dragging:
            self._guard('release_swipes', self.swipes.release)   # never leave the side swipes off

    def follow_tabs(self):
        """Windows resting in the tab row (Window.to_tab): out over the code
        while their stand-in tab is selected, back into the row when another
        tab is, closed when their tab is closed. Reads only the selected
        tab's path: during a switch the editor's text can lag behind it."""
        resting = [window for window in self.windows.values()
                   if getattr(window, 'tab_path', None)]
        if not resting:
            return
        from .. import tabs as editor_tabs
        from . import tabrow
        selected = editor_tabs.selected_tab()
        open_paths = editor_tabs.open_tabs()
        now = time.time()
        for window in resting:
            if window._busy():
                continue
            path = window.tab_path
            if not any(tabrow.same_path(other, path) for other in open_paths):
                if now - getattr(window, 'tab_since', 0) > tabrow.OPEN_GRACE_SECONDS:
                    window.tab_path = None           # its tab is already gone
                    window.close()
                continue
            mine = tabrow.same_path(selected, path)
            if mine and window.place == 'tab':
                window._tab_to_panel()
            elif not mine and window.place == 'panel' and getattr(window, 'tab_showing', False):
                window._panel_to_tab()

    def _guard(self, stage, function, *args):
        """Run one stage; on failure print its traceback (the first 3 times
        per stage) and carry on with the rest of the beat."""
        try:
            function(*args)
        except Exception:
            failures = getattr(self, 'stage_failures', None)
            if failures is None:
                failures = self.stage_failures = {}
            failures[stage] = failures.get(stage, 0) + 1
            if failures[stage] <= 3:
                import traceback
                print('editorkit windows: %s failed (%d):' % (stage, failures[stage]))
                traceback.print_exc()

    def check_theme(self):
        """Every THEME_CHECK_SECONDS: when the editor's theme has changed
        (by hand, or Pythonista's automatic dark and light), take its
        colours into the shared palette and repaint every window."""
        import time
        from .. import themes
        now = time.time()
        if now < getattr(self, 'next_theme_check', 0.0):
            return
        self.next_theme_check = now + look.THEME_CHECK_SECONDS
        name = themes.current_theme()
        if getattr(self, 'theme_name', None) is None:
            self.theme_name = name
            return
        if name == self.theme_name:
            return
        self.theme_name = name
        self.palette.update(themes.theme_colours(), themes.syntax_colours())
        for window in list(self.windows.values()):
            self._guard('restyle %s' % getattr(window, 'key', '?'), window.restyle)

    # --- The tray: minimised windows waiting in the tray home's bar ------

    def tray_windows(self, holder=None):
        """Windows in the tray, most recently minimised first; with holder,
        only those folded into its box (window.holder() is holder)."""
        windows = [self.windows[key] for key in self.tray if key in self.windows]
        if holder is None:
            return windows
        return [window for window in windows if window.holder() is holder]

    def tray_home(self):
        """The window that holds the tray (Window(tray_home=True)), if any."""
        for window in self.windows.values():
            if window.tray_home:
                return window
        return None

    def tray_add(self, window):
        if window.key in self.tray:
            self.tray.remove(window.key)
        self.tray.insert(0, window.key)
        self.tray_changed()

    def tray_remove(self, window):
        if window.key in self.tray:
            self.tray.remove(window.key)
            self.tray_changed()

    def tray_changed(self):
        """Tell every holder (the tray home, and owners of pieces) what is in
        its box, so each redraws its row."""
        windows = list(self.windows.values())
        for window in windows:
            holds = window.tray_home or any(getattr(other, 'owner', None) is window
                                            for other in windows)
            if not holds:
                continue
            window.emit('tray', self.tray_windows(window))
            refresh = getattr(window, '_refresh_box', None)
            if callable(refresh):
                self._guard('box %s' % getattr(window, 'key', '?'), refresh)

    def keep_riders_on_dock(self):
        """Keep windows riding the dock (win.ride_dock, or move_to
        'above_dock') just above the keyboard or whatever is docked in
        its place, key row included, over the code or in the console. A
        window riding with fill also grows to fill the space above it, below
        the status bar."""
        riders = [window for window in self.windows.values()
                  if window.riding and window.place in ('panel', 'console')
                  and window.panel is not None and window.grabbing is None
                  and not window._busy()]
        for window in riders:
            host = places.console_container() if window.place == 'console' else places.editor()
            if host is None:
                continue
            keyboard = places.keyboard_top(host)
            if keyboard is None:
                continue
            panel = window.panel
            frame = places.frame_of(panel)
            x, y, width, height = frame
            if window.ride_fill:
                top = places.safe_top(host)
                target = (look.EDGE, top, float(host.bounds().size.width) - 2 * look.EDGE,
                          keyboard - top - look.EDGE)
                if target[3] < FILL_MIN_HEIGHT:
                    continue
            else:
                target = (x, max(look.EDGE, keyboard - height - look.EDGE), width, height)
            if max(abs(a - b) for a, b in zip(frame, target)) > 1:
                if window.place == 'panel':
                    _remembered('frames')[window.key] = target
                ui.animate(lambda panel=panel, target=target: setattr(panel, 'frame', target),
                           look.PIN_FADE_SECONDS)

    def check_code_inset(self):
        """While a window with inset_code sits open at the top of the code,
        push the code down by its bottom edge; put the text view's own inset
        back once none does. Skipped while any window is moving."""
        if any(window._busy() for window in self.windows.values()):
            return
        view = places.text_view()
        if view is None:
            return
        wanted = 0.0
        for window in self.windows.values():
            if window.inset_code and window.place == 'panel' and window.panel is not None:
                _, y, _, height = places.frame_of(window.panel)
                if y <= look.INSET_TOP_REACH:
                    wanted = max(wanted, y + height)
        pointer = getattr(view.ptr, 'value', view.ptr)
        if pointer != self.inset_pointer:
            # First look, or a tab switch gave us a new text view: its own
            # inset is the base (ours, if any, went with the old view).
            if not wanted and self.inset_pointer is None:
                return
            self.inset_pointer = pointer
            self.base_inset = places.code_inset_top(view)
        target = self.base_inset + wanted
        if abs(places.code_inset_top(view) - target) > 0.5:
            places.set_code_inset_top(view, target)

    def arrange_pins(self):
        """Keep resting pins over the code clear of open panels and of each
        other: a pin that would overlap glides to the first clear spot below,
        and back to its own place once clear. Its remembered place is never
        changed, only where it shows. Dragged pins and moving windows are
        left alone (but still count as taken)."""
        resting = [window for window in self.windows.values()
                   if window.place == 'pin' and window.pin_home == 'editor'
                   and window.pin is not None]
        if not resting:
            return
        panels = [places.frame_of(window.panel) for window in self.windows.values()
                  if window.place == 'panel' and window.panel is not None]
        _, editor_height = places.editor_size()
        pad = look.TOUCH_PAD
        resting.sort(key=lambda window: (window._pin_frame()[1], window.key))
        taken = []
        for window in resting:
            pin = window.pin
            if pin.dragging or window._busy():
                taken.append(rules.inset(places.frame_of(pin), pad))
                continue
            # A pin lands where its window's emoji was (so the fold looks
            # continuous), which from the full-width keyboard's place is
            # nearer the edge than a resting pin: settle it into the column.
            side, inset, top = window.pin_place
            if abs(inset - look.EDGE) > 0.5:
                window.pin_place = (side, look.EDGE, top)
                _remembered('pins')[window.key] = window.pin_place
            home = window._pin_frame()
            pill = rules.inset(home, pad)
            top = rules.clear_top(pill, panels + taken, look.PIN_STACK_GAP, editor_height)
            taken.append((pill[0], top, pill[2], pill[3]))
            target = (home[0], top - pad, home[2], home[3])
            shown = places.frame_of(pin)
            if max(abs(a - b) for a, b in zip(shown, target)) > 1:
                ui.animate(lambda pin=pin, target=target: setattr(pin, 'frame', target),
                           look.PIN_FADE_SECONDS)

    def check_key_row(self):
        """Give Pythonista's key row back once the window that hid it is no
        longer over the code, is closed, or the keyboard went down."""
        owner = self.dock.hidden_for
        if owner is None or owner._busy():
            return
        view = places.text_view()
        if (owner.place != 'panel' or owner.manager is not self
                or view is None or not view.isFirstResponder()):
            self.dock.restore_key_row(owner)

    def follow_editor(self):
        """A tab switch shows another script's editor view: move every window
        resting over the code into it. Called every EDITOR_CHECK_SECONDS."""
        view = places.editor()
        if view is None:
            return
        pointer = getattr(view.ptr, 'value', view.ptr)
        if pointer == self.editor_pointer:
            return
        first_look = self.editor_pointer is None
        self.editor_pointer = pointer
        if first_look:
            return
        for window in list(self.windows.values()):
            window.follow_editor()


def _manager():
    store = _store()
    current = store.get('manager')
    if current is not None and type(current) is not Manager:
        # A Manager from an older editorkit: the store outlives module
        # reloads, so without this a library update never reaches the clock.
        _retire(current)
        current = None
    if current is not None and current.objc_instance.superview() is not None:
        return current
    current = Manager()
    _app.prepare(current)
    _app.root().detailViewController().view().addSubview_(current.objc_instance)
    store['manager'] = current
    return current


def _retire(old):
    """Remove an outdated Manager and every window it ran, at once. Never
    raises: an old object may lack anything the new code expects."""
    for window in list(getattr(old, 'windows', {}).values()):
        try:
            window._dismantle()
        except Exception as error:
            print('editorkit windows: retiring a window failed: %r' % (error,))
    try:
        old.windows.clear()
        if old.swipes.active:
            old.swipes.release()
    except Exception:
        pass
    try:
        old.objc_instance.removeFromSuperview()
    except Exception:
        pass

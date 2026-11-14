"""Moves Part of Window: see window.py."""
import ui

from .. import _app
from . import look, places


class Moves(object):
    """The moves between places: pin, panel over the code, the keyboard's
    place and the console. Each is a recipe of snapshot hand-offs (a
    picture on the ghost), ui.animate on frame and alpha, and later steps
    booked on the timeline (never ui.delay)."""

    # ==== Pieces of moves ====

    def _fade_pin_in(self):
        pin = self.pin
        pin.frame = self._pin_frame()
        self._put_in(pin, self.pin_home)
        pin.touch_enabled = True
        ui.animate(lambda: setattr(pin, 'alpha', 1.0), look.PIN_FADE_SECONDS)

    def _float_panel(self, frame, faded):
        panel = self.panel
        places.ready_to_move(panel)
        panel.show_place('float')
        panel.refresh()
        panel.frame = frame
        panel.alpha = 0.0 if faded else 1.0
        panel.content.alpha = 0.0 if faded else 1.0
        places.over_editor(panel)

    def _hold_picture(self, frame, layer='editor', source=None):
        """A snapshot of the panel (or source) on the ghost at frame: over the
        code, or in the root view (layer 'root') to travel between editor and
        console."""
        self._clear_picture()
        ghost = self.ghost
        ghost.frame = frame
        ghost.alpha = 1.0
        picture = places.picture_of(source if source is not None else self.panel, frame)
        if picture is not None:
            ghost.objc_instance.addSubview_(picture)
        self._raise_ghost(layer)

    def _clear_picture(self):
        if self.ghost is None:
            return
        for picture in self.ghost.objc_instance.subviews() or []:
            picture.removeFromSuperview()
        places.take_away(self.ghost)

    def _raise_ghost(self, layer):
        if layer == 'root':
            places.root_view().addSubview_(self.ghost.objc_instance)
        else:
            places.over_editor(self.ghost)

    def _land(self, layer):
        """The real panel shows under the picture; the picture fades off it."""
        panel, ghost = self.panel, self.ghost
        panel.alpha = 1.0
        panel.content.alpha = 1.0
        self._raise_ghost(layer)
        ui.animate(lambda: setattr(ghost, 'alpha', 0.0), look.GHOST_FADE_SECONDS)
        self._book(look.GHOST_FADE_SECONDS, 'clear picture', self._clear_picture)

    # ==== Moves ====

    def _pin_to_panel(self):
        """The panel grows out of the pin in the pin's home (over the code, or
        over the console), then its page fades in."""
        manager = self.manager
        home = self.pin_home
        if home == 'console' and places.console_container() is None:
            home = 'editor'
            self._set_pin_home(home)
        self._hold(look.GROW_SECONDS + look.CONTENT_FADE_SECONDS)
        if home == 'console':
            places.slide_console(True, look.CONSOLE_SLIDE_SECONDS)
        elif look.CLOSE_KEYBOARD_ON_OPEN and manager.dock.window is None:
            places.put_keyboard_away()
        pin, panel = self.pin, self.panel
        pin.touch_enabled = False
        panel.set_side(self.pin_place[0])          # the emoji opens where the pin was
        places.ready_to_move(panel)
        panel.show_place('console' if home == 'console' else 'float')
        panel.refresh()
        panel.frame = places.frame_of(pin)
        panel.alpha = 0.0
        panel.content.alpha = 0.0
        self._put_in(panel, home)
        self._ensure_page()
        target = self._open_frame()

        def grow():
            panel.frame = target
            panel.alpha = 1.0
            pin.alpha = 0.0
        ui.animate(grow, look.GROW_SECONDS)
        self._book(look.GROW_SECONDS, 'page in',
                   lambda: ui.animate(lambda: setattr(panel.content, 'alpha', 1.0),
                                      look.CONTENT_FADE_SECONDS))
        if home == 'console':
            self.place = 'console'
            self._emit('console')
        else:
            self.place = 'panel'
            self._emit('open')

    def _panel_to_pin(self):
        """The page fades, then the panel shrinks into a pin where its emoji is,
        in the same area (over the code, or over the console)."""
        host = self._host_of_panel()
        self._hold(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS)
        place = self._emoji_place()
        self._set_pin_home(host)
        self._set_pin_place(place)
        pin, panel = self.pin, self.panel
        ui.animate(lambda: setattr(panel.content, 'alpha', 0.0), look.CONTENT_FADE_SECONDS)

        def shrink():
            target = self._pin_frame()
            pin.frame = target
            self._put_in(pin, host)
            self._put_in(panel, host)              # the panel shrinks over the pin

            def move():
                panel.frame = target
                panel.alpha = 0.0
                pin.alpha = 1.0
            ui.animate(move, look.SHRINK_SECONDS)

        def finish():
            places.take_away(panel)
            pin.touch_enabled = True
        self._book(look.CONTENT_FADE_SECONDS, 'shrink to pin', shrink)
        self._book(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS, 'panel away', finish)
        self.place = 'pin'
        self._emit('minimise')

    def _panel_to_dock(self):
        """A picture of the panel drops while the real one rises from below."""
        manager = self.manager
        self._hold(look.HANDOFF_SECONDS)
        panel = self.panel
        self._hold_picture(places.frame_of(panel))
        places.take_away(panel)
        panel.show_place('dock')
        editor_width, _ = places.editor_size()
        panel.frame = (0, 0, editor_width, look.KEYBOARD_HEIGHT)
        panel.alpha = 1.0
        panel.content.alpha = 1.0
        if not manager.dock.take(self, panel, host=self.dock_host):
            self._clear_picture()
            self._float_panel(self._float_frame(), faded=False)
            return
        ghost, target = self.ghost, self._dock_frame()

        def drop():
            ghost.frame = target
            ghost.alpha = 0.0
        ui.animate(drop, look.HANDOFF_SECONDS)
        self._book(look.HANDOFF_SECONDS, 'clear picture', self._clear_picture)
        self.place = 'dock'
        self._emit('dock')

    def _pin_to_dock(self):
        """Straight from the pin into the keyboard's place: the pin fades while
        the window rises from below as the keyboard (iOS slides it in)."""
        if self.place in ('hidden', 'closed'):
            self._build()
        manager = self.manager
        pin, panel = self.pin, self.panel
        places.ready_to_move(panel)
        panel.show_place('dock')
        panel.refresh()
        editor_width, _ = places.editor_size()
        panel.frame = (0, 0, editor_width, look.KEYBOARD_HEIGHT)
        panel.alpha = 1.0
        panel.content.alpha = 1.0
        self._ensure_page()
        if not manager.dock.take(self, panel, host=self.dock_host):
            self._pin_to_panel()             # no script to type into: open over the code
            return
        self._hold(look.HANDOFF_SECONDS)
        pin.touch_enabled = False
        ui.animate(lambda: setattr(pin, 'alpha', 0.0), look.PIN_FADE_SECONDS)
        self.place = 'dock'
        self._emit('dock')

    def _dock_to_panel(self):
        """The keyboard's place slides away while a picture rises over the code;
        the real panel lands under it."""
        self._hold(look.HANDOFF_SECONDS + look.GHOST_FADE_SECONDS)
        self._hold_picture(self._dock_frame())
        self.manager.dock.give_back(self)
        ghost, target = self.ghost, self._float_frame()
        ui.animate(lambda: setattr(ghost, 'frame', target), look.HANDOFF_SECONDS)

        def land():
            self._float_panel(target, faded=False)
            places.over_editor(ghost)             # picture on top, fading off the panel
            ui.animate(lambda: setattr(ghost, 'alpha', 0.0), look.GHOST_FADE_SECONDS)
        self._book(look.HANDOFF_SECONDS, 'land over the code', land)
        self._book(look.HANDOFF_SECONDS + look.GHOST_FADE_SECONDS, 'clear picture',
                   self._clear_picture)
        self.place = 'panel'
        self._emit('open')

    def _dock_to_pin(self):
        """The keyboard's place slides away while a picture shrinks into the pin."""
        self._hold(look.HANDOFF_SECONDS)
        self._set_pin_home('editor')               # the keyboard's place is the editor's
        self._hold_picture(self._dock_frame())
        self.manager.dock.give_back(self)
        ghost, pin, target = self.ghost, self.pin, self._pin_frame()
        pin.frame = target

        def shrink():
            ghost.frame = target
            ghost.alpha = 0.0
        ui.animate(shrink, look.HANDOFF_SECONDS)
        self._book(look.HANDOFF_SECONDS * 0.6, 'pin back', self._fade_pin_in)
        self._book(look.HANDOFF_SECONDS, 'clear picture', self._clear_picture)
        self.place = 'pin'
        self._emit('minimise')

    def _panel_to_console(self):
        """A picture flies from over the code into the console in step with the
        console's slide; the real panel rides in on the console under it
        (proven in labs/canvas_throw_lab.py, 2026-11-08)."""
        container = places.console_container()
        if container is None or self.place != 'panel':
            return
        self._hold(look.CONSOLE_SLIDE_SECONDS + look.GHOST_FADE_SECONDS)
        panel = self.panel
        start = places.in_root(places.editor(), places.frame_of(panel))
        self._hold_picture(start, layer='root')
        places.take_away(panel)
        landing = self._console_frame()
        panel.show_place('console')
        panel.frame = landing
        panel.alpha = 0.0
        panel.content.alpha = 1.0
        places.over_console(panel)
        places.slide_console(True, look.CONSOLE_SLIDE_SECONDS)
        target = places.in_root(container, landing)
        ghost = self.ghost
        ui.animate(lambda: setattr(ghost, 'frame', target), look.CONSOLE_SLIDE_SECONDS)
        self._book(look.CONSOLE_SLIDE_SECONDS, 'land in the console', lambda: self._land('root'))
        self.place = 'console'
        self._emit('console')

    def _console_to_panel(self):
        """The console slides away while a picture flies back over the code;
        the real panel lands under it."""
        container = places.console_container()
        if container is None:
            return
        self._hold(look.CONSOLE_SLIDE_SECONDS + look.GHOST_FADE_SECONDS)
        panel = self.panel
        start = places.in_root(container, places.frame_of(panel))
        self._hold_picture(start, layer='root')
        places.take_away(panel)
        landing = self._float_frame()
        self._float_panel(landing, faded=False)
        panel.alpha = 0.0
        places.slide_console(False, look.CONSOLE_SLIDE_SECONDS)
        target = places.in_root(places.editor(), landing)
        ghost = self.ghost
        ui.animate(lambda: setattr(ghost, 'frame', target), look.CONSOLE_SLIDE_SECONDS)
        self._book(look.CONSOLE_SLIDE_SECONDS, 'land over the code', lambda: self._land('root'))
        self.place = 'panel'
        self._emit('open')

    def _console_to_pin(self):
        """From the console, the panel folds into a pin that stays in the console."""
        self._panel_to_pin()

    # ==== The tray ====

    def _tray_target(self, host, start):
        """Where a window shrinks to on its way into the tray: the tray home's
        pin when it rests in the same area, else a small spot at the top
        middle of where it was (it just fades there)."""
        home = self.holder()
        size = look.PIN_HEIGHT
        if (home is not None and home.place == 'pin'
                and home.pin is not None and home.pin_home == host):
            return home._pin_frame()
        box = self._box_spot(home, host)
        if box is not None:
            return box
        x, y, width, _ = start
        return (x + width / 2.0 - size / 2.0, y, size, size)

    def _box_spot(self, home, host):
        """Where an open holder's box row is (just under its header), when it
        is open over the same area: pieces shrink into it and grow out of it."""
        if home is None or home.place != 'panel' or home.panel is None:
            return None
        try:
            if home._host_of_panel() != host:
                return None
        except Exception:
            return None
        x, y, width, _ = places.frame_of(home.panel)
        size = look.PIN_HEIGHT
        return (x + width / 2.0 - size / 2.0, y + look.HEADER_HEIGHT, size, size)

    def _enter_tray(self):
        """Rest in the tray: no pin on screen; the tray home lists it."""
        pin = self.pin
        pin.touch_enabled = False
        pin.alpha = 0.0
        places.take_away(pin)
        self.place = 'tray'
        self._emit('minimise')
        self.manager.tray_add(self)

    def _panel_to_tray(self):
        """The page fades, then the panel shrinks into the tray home's pin
        (or fades where it is) and leaves the screen."""
        host = self._host_of_panel()
        self._hold(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS)
        panel = self.panel
        target = self._tray_target(host, places.frame_of(panel))
        ui.animate(lambda: setattr(panel.content, 'alpha', 0.0), look.CONTENT_FADE_SECONDS)

        def shrink():
            def move():
                panel.frame = target
                panel.alpha = 0.0
            ui.animate(move, look.SHRINK_SECONDS)
        self._book(look.CONTENT_FADE_SECONDS, 'shrink to tray', shrink)
        self._book(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS, 'panel away',
                   lambda: places.take_away(panel))
        self._enter_tray()

    def _dock_to_tray(self):
        """The dock slides away while a picture shrinks into the tray home's
        pin (or fades)."""
        self._hold(look.HANDOFF_SECONDS)
        start = self._dock_frame()
        self._hold_picture(start)
        self.manager.dock.give_back(self)
        ghost, target = self.ghost, self._tray_target('editor', start)

        def shrink():
            ghost.frame = target
            ghost.alpha = 0.0
        ui.animate(shrink, look.HANDOFF_SECONDS)
        self._book(look.HANDOFF_SECONDS, 'clear picture', self._clear_picture)
        self._enter_tray()

    def _tray_to_panel(self):
        """Out of the tray: the hidden pin waits on the tray home's pin, then
        the panel grows out of it, back to where it was last left."""
        self.manager.tray_remove(self)
        home = self.holder()
        pin = self.pin
        box = self._box_spot(home, self.pin_home)
        if (home is not None and home.place == 'pin'
                and home.pin is not None and home.pin_home == self.pin_home):
            pin.frame = home._pin_frame()
        elif box is not None:
            pin.frame = box
        else:
            pin.frame = self._pin_frame()
        pin.alpha = 0.0
        pin.touch_enabled = False
        self._put_in(pin, self.pin_home)
        self.open_exact = True
        self._pin_to_panel()

    # ==== The tab row (tabrow.py) ====

    def to_tab(self):
        """Rest in Pythonista's tab row: a stand-in tab named with the
        window's emoji and title. Selecting the tab brings the window out
        over the code, another tab puts it back, closing the tab closes it.
        The tab you were on stays selected. From the keyboard's place or the
        console it does nothing (bring it over the code first)."""
        if self._busy() or self.place in ('tab', 'dock', 'console'):
            return self
        import time
        from .. import tabs as editor_tabs
        from . import tabrow
        path = getattr(self, 'tab_path', None) or tabrow.stand_in_path(
            self.key, self.emoji, self.title)
        tabrow.write_stand_in(path, self.title)
        before = editor_tabs.selected_tab()
        self.tab_path = path
        self.tab_since = time.time()
        self._hook_tab_close()
        # The stand-in tab opens first, so the window can fly into it.
        editor_tabs.open_file(path)
        # Stay on the code: back to the tab that was showing (or another one,
        # when the stand-in itself was showing).
        back = before if before and not tabrow.same_path(before, path) else None
        if back is None:
            others = [other for other in editor_tabs.open_tabs()
                      if not tabrow.same_path(other, path)]
            back = others[-1] if others else None
        if back:
            editor_tabs.select_tab(back)
        if self.place == 'panel':
            self._panel_to_tab(landing=path)
            return self
        if self.place in ('hidden', 'closed'):
            self._build()
        elif self.place == 'tray':
            self.manager.tray_remove(self)
        self._enter_tab()
        editor_tabs.set_tab_alpha(path, 0.0)
        self._book(look.LIFT_SECONDS, 'tab appears',
                   lambda: editor_tabs.fade_tab_in(path, look.TAB_APPEAR_SECONDS))
        return self

    def out_of_tab(self):
        """Leave the tab row for good (its tab pulled down): the window comes
        out over the code and stays. Closing the stand-in tab is the
        caller's job."""
        self.tab_path = None
        if self.place == 'tab':
            self._tab_to_panel()
        self.tab_showing = False

    def _hook_tab_close(self):
        """Closing the window closes its stand-in tab too (once hooked)."""
        if getattr(self, 'tab_close_hooked', False):
            return
        self.tab_close_hooked = True
        self.on('close', lambda window: window._close_own_tab())

    def _close_own_tab(self):
        path, self.tab_path = getattr(self, 'tab_path', None), None
        if path:
            from .. import tabs as editor_tabs
            editor_tabs.close_tab(path)

    def _enter_tab(self):
        """Rest in the tab row: no pin on screen, no tray chip; the stand-in
        tab is all that shows."""
        pin = self.pin
        pin.touch_enabled = False
        pin.alpha = 0.0
        places.take_away(pin)
        self.place = 'tab'
        self.tab_showing = False
        self._emit('minimise')

    def _panel_to_tab(self, landing=None):
        """The page fades, then the panel shrinks up toward the tab row and
        leaves the screen. landing (a stand-in tab's path, when the window is
        going in): the panel flies into that tab's own spot in the row while
        the tab, hidden till then, fades in as it lands."""
        from .. import tabs as editor_tabs
        self._hold(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS)
        panel = self.panel
        x, y, width, _ = places.frame_of(panel)
        size = look.PIN_HEIGHT
        fallback = (x + width / 2.0 - size / 2.0, -size, size, size)
        if landing:
            editor_tabs.set_tab_alpha(landing, 0.0)
        ui.animate(lambda: setattr(panel.content, 'alpha', 0.0), look.CONTENT_FADE_SECONDS)

        def shrink():
            target = fallback
            if landing:
                found = editor_tabs.tab_frame(landing, panel.objc_instance.superview())
                if found is not None:
                    target = found
                    editor_tabs.set_tab_alpha(landing, 0.0)   # still hidden as it lands

            def move():
                panel.frame = target
                panel.alpha = look.TAB_SHRINK_ALPHA if landing else 0.0
            ui.animate(move, look.SHRINK_SECONDS)

        def arrive():
            places.take_away(panel)
            if landing:
                editor_tabs.fade_tab_in(landing, look.TAB_APPEAR_SECONDS)
        self._book(look.CONTENT_FADE_SECONDS, 'shrink to tab', shrink)
        self._book(look.CONTENT_FADE_SECONDS + look.SHRINK_SECONDS, 'panel into tab', arrive)
        self._enter_tab()

    def _tab_to_panel(self):
        """Its tab selected: the panel grows down from the top of the code,
        back to where it was last left."""
        editor_width, _ = places.editor_size()
        size = look.PIN_HEIGHT
        pin = self.pin
        self.pin_home = 'editor'
        pin.frame = (editor_width / 2.0 - size / 2.0, 0, size, size)
        pin.alpha = 0.0
        pin.touch_enabled = False
        self._put_in(pin, 'editor')
        self.open_exact = True
        self.tab_showing = True
        self._pin_to_panel()

    @_app.on_main
    def send_pin(self, home):
        """Move the pin to 'console' or 'editor' by code, as a hold at the edge
        would. Works on a window resting as its pin (a new window first appears
        as its pin, then goes)."""
        if home not in ('editor', 'console') or self._busy():
            return self
        if home == 'console' and places.console_container() is None:
            return self
        if self.place in ('hidden', 'closed'):
            self._build()
            self._fade_pin_in()
            if home != self.pin_home:
                step = self._pin_to_console if home == 'console' else self._pin_to_editor
                self._book(look.PIN_FADE_SECONDS, 'send pin', step)
            return self
        if self.place != 'pin' or home == self.pin_home:
            return self
        if home == 'console':
            self._pin_to_console()
        else:
            self._pin_to_editor()
        return self

    def _pin_to_console(self):
        """The console slides in under a picture of the pin; the pin lands in
        the console at the same spot on screen."""
        container = places.console_container()
        if container is None:
            return
        self._hold(look.CONSOLE_SLIDE_SECONDS + look.GHOST_FADE_SECONDS)
        pin = self.pin
        dropped = places.frame_of(pin)
        start = places.in_root(places.editor(), dropped)
        self._hold_picture(start, layer='root', source=pin)
        places.take_away(pin)
        places.slide_console(True, look.CONSOLE_SLIDE_SECONDS)
        # The console's final frame is readable once its slide has started.
        in_console = places.convert(dropped, places.editor(), container)
        self._set_pin_home('console')
        self._set_pin_place(self._place_from_frame(in_console, places.console_size()[0], False))
        landing = self._pin_frame()
        pin.frame = landing
        pin.alpha = 0.0
        places.over_console(pin)
        target = places.in_root(container, landing)
        ghost = self.ghost
        ui.animate(lambda: setattr(ghost, 'frame', target), look.CONSOLE_SLIDE_SECONDS)
        self._book(look.CONSOLE_SLIDE_SECONDS, 'pin lands in the console', self._land_pin)

    def _pin_to_editor(self):
        """The console slides away while a picture of the pin stays on screen;
        the pin lands over the code at the same spot."""
        container = places.console_container()
        if container is None:
            return
        self._hold(look.CONSOLE_SLIDE_SECONDS + look.GHOST_FADE_SECONDS)
        pin = self.pin
        dropped = places.frame_of(pin)
        start = places.in_root(container, dropped)
        # Convert before the slide starts, while the console is still in place.
        on_editor = places.convert(dropped, container, places.editor())
        self._hold_picture(start, layer='root', source=pin)
        places.take_away(pin)
        self._set_pin_home('editor')
        self._set_pin_place(self._place_from_frame(on_editor, places.editor_size()[0], False))
        landing = self._pin_frame()
        pin.frame = landing
        pin.alpha = 0.0
        places.over_editor(pin)
        target = places.in_root(places.editor(), landing)
        places.slide_console(False, look.CONSOLE_SLIDE_SECONDS)
        ghost = self.ghost
        ui.animate(lambda: setattr(ghost, 'frame', target), look.CONSOLE_SLIDE_SECONDS)
        self._book(look.CONSOLE_SLIDE_SECONDS, 'pin lands over the code', self._land_pin)

    def _land_pin(self):
        """The real pin shows under its picture; the picture fades off it."""
        pin, ghost = self.pin, self.ghost
        pin.alpha = 1.0
        pin.touch_enabled = True
        self._raise_ghost('root')
        ui.animate(lambda: setattr(ghost, 'alpha', 0.0), look.GHOST_FADE_SECONDS)
        self._book(look.GHOST_FADE_SECONDS, 'clear picture', self._clear_picture)

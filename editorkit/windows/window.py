"""Window: a themed panel over Pythonista's editor that rests as a pin, opens
over the code, moves and resizes, docks in the keyboard's place and comes
back. Many windows can be open at once; one clock (the Manager) runs them all.

Places: 'hidden' (made, never shown), 'pin', 'panel' (over the code),
'dock' (the keyboard's place), 'console', 'tray' (folded into the tray home),
'tab' (resting in Pythonista's tab row as a stand-in tab), 'closed'.

Every move between places uses patterns proven on device: grow and shrink, snapshot
hand-offs, holds noticed by the clock, side swipes off while dragging.
Motion is ui.animate on frame and alpha with no completion; later steps are
booked on the timeline; never ui.delay (pythonista-ui-stability guide).

The window is built from parts: homes.py (where it lives), moves.py
(moves between places), gestures.py (moving by hand); manager.py
holds the clock and state.py the shared settings and memory.
"""
import ui

from .. import _app
from . import content, look, places, rules
from .gestures import Gestures
from .homes import Homes
from .manager import _manager
from .moves import Moves
from .state import EDITOR_EVENTS, EVENTS, PAGE_TICK_SECONDS, _store, _remembered
from .views import Panel, Pin


class Beat:
    """A callback on a window's clock (win.every, win.after); stop() ends it."""

    def __init__(self, callback, at=None):
        self.callback = callback
        self.at = at                  # when a one-off is due (time.time()); None: every beat
        self.stopped = False

    def stop(self):
        self.stopped = True
class Window(Homes, Moves, Gestures):
    """A window over the editor.

        win = Window('Notes', emoji='📝')
        win.add_page('Today', thing)     # a ui.View, text, HTML, or builder(window)
        win.show()

    title       shown in the header
    emoji       the window's mark: in its pin and at the end of its header
    key         one window per key: showing a new one replaces the old; also
                what its place and size are remembered under (default: title)
    size        (width, height) the first time it opens; after that it opens
                as it was left
    min_size    the smallest the resize corner allows (default: header only)
    closable    False hides the ✕ button
    keyboard    False: this window never goes to the keyboard's place
    console     False: this window never goes to the console
    pin_text    words shown in the pin beside the emoji (set_pin_text changes them)
    on_close    a callback(window) when it closes (the same as on('close', ...))
    """

    def __init__(self, title='', emoji=look.EMOJI, key=None, size=None, min_size=None,
                 closable=True, dockable=True, console=True, pin_text=None, on_close=None,
                 dock_button=False, home=None, keyboard_row='hide',
                 backdrop='solid', backdrop_alpha=look.BACKDROP_ALPHA, inset_code=None,
                 dock_host='editor', minimise_to=None, tray_home=False, owner=None):
        home = self._current_name(home)
        self.title = title
        self.emoji = emoji
        self.key = key or title or 'window-%d' % id(self)
        self.size = size
        self.min_size = min_size or look.DEFAULT_MIN_SIZE
        self.closable = closable
        self.allows_dock = dockable           # False: never in the keyboard's place
        self.dock_button = dock_button    # show ⌨ in the header (dragging docks anyway)
        self.home = home              # where show() opens: None, 'dock', or a FRAME_HOMES name
        self.open_exact = False       # the next open from a pin lands on the stored frame
        # Pythonista's key row while this window sits above the keyboard:
        # 'hide' (default) or 'keep'. Planned: a list of keys for the tool.
        self.keyboard_row = keyboard_row
        self.hide_row_next = False
        # How the panel is filled: 'solid', 'tinted' (code shows through the
        # page area) or 'clear'; the header always keeps a fill.
        self.backdrop = backdrop
        self.backdrop_alpha = backdrop_alpha
        # Push the code down while this window sits open at the top of the
        # code, so nothing hides under it. On by default for a top bar.
        self.inset_code = (home == 'top_bar') if inset_code is None else inset_code
        # Sent above the keyboard (move_to): keep its bottom just above the
        # real keyboard, key row included, until grabbed by hand.
        self.riding = False
        self.ride_fill = False        # riding: fill the space above the dock too
        # Which text view hosts this window in the keyboard's place: the
        # script's ('editor') or the console's prompt line ('console').
        self.dock_host = dock_host
        # Where minimise() sends it: 'tray' (a chip in the tray home's bar)
        # or 'pin' (a pill resting over the code); None: look.MINIMISE_TO.
        # The tray home itself always rests as a pin.
        self.tray_home = tray_home
        self.minimise_to = 'pin' if tray_home else (minimise_to or look.MINIMISE_TO)
        # Window(owner=app): this window is one of that app's pieces. It folds
        # into the owner's box, and goes when the owner folds or closes.
        self.owner = owner
        self.box_view = None          # the automatic tiles.Box, while pieces are folded in
        self.pieces_out = []          # keys of pieces open when this window folded
        self.clock = []               # Beats: every() and after()
        self.last_place = 'hidden'    # for the 'place' event
        self.editor_watch = None      # the ek.on_change handle, once listened to
        self.allows_console = console
        self.pin_words = pin_text
        self.app_buttons = []
        if look.FULL_BUTTON:
            # ＋ first among the app buttons: ✕ – ＋ then the app's own.
            self.app_buttons.append({'name': 'full', 'icon': look.FULL_ICON,
                                     'action': lambda window: window.toggle_full(),
                                     'on': None})         # [{'name', 'icon', 'action', 'on'}], header order
        self.accessory = None         # (view, height): the strip under the tabs
        self.sheet = None             # the view lying over the page area
        self.next_page_tick = 0.0
        self.tick_failures = set()    # ids of views whose tick failed (reported once)
        self.pages = []               # [name, thing, view or None]
        self.page = None
        self.place = 'hidden'
        self.listeners = dict((name, []) for name in EVENTS)
        if on_close is not None:
            self.listeners['close'].append(on_close)
        self.manager = None
        self.palette = None
        self.pin = self.panel = self.ghost = self.dock_line = None
        self.pin_place = None         # (side, inset, top) of the pin's pill, in its home
        self.pin_home = 'editor'      # where the pin lives: 'editor' or 'console'
        self.edge_since = None        # when a dragged pin or panel started poking out
        self.grabbing = None          # 'move' or 'resize' while a panel grip is held
        self.docking = False
        self.pulled = 0.0
        self.under = None             # (line number, text) under the pin, when watched
        self.under_key = None

    # ==== Public ====

    def add_page(self, name, thing):
        """Add a page: a ui.View, builder(window), .pyui path, image, figure,
        HTML or text (see content.py). A .pyui file loads now, so it resolves
        against the calling script."""
        if rules.is_pyui_path(thing):
            thing = content.load_pyui(thing)
        self.pages.append([name, thing, None])
        if self.page is None:
            self.page = name
        if self.panel is not None:
            self.panel.set_tabs(self.page_names(), self.page)
        return self

    @_app.on_main
    def set_page_content(self, name, thing):
        """Swap what page name shows (adding the page if it is new); a page on
        screen changes in place, and the window stays where it is."""
        if rules.is_pyui_path(thing):
            thing = content.load_pyui(thing)
        entry = self._entry(name)
        if entry is None:
            return self.add_page(name, thing)
        old_view = entry[2]
        entry[1], entry[2] = thing, None
        if (self.panel is not None and self.panel.page_view is old_view
                and self.place in ('panel', 'console', 'dock')):
            self._ensure_page()
        return self

    def page_names(self):
        """The pages' names, in the order their tabs show."""
        return [entry[0] for entry in self.pages]

    def restyle(self):
        """Repaint in the palette's current colours (the manager calls this
        when the theme changes): pin, frame, then every view in the pages,
        sheet and accessory that has a restyle()."""
        if self.pin is not None:
            self.pin.restyle(self.palette)
        if self.panel is not None:
            self.panel.restyle()
        roots = []
        for _name, thing, view in self.pages:
            if view is None and isinstance(thing, ui.View):
                view = thing
            if view is not None:
                roots.append(view)
        roots.extend(view for view in (self.sheet, self.accessory) if view is not None)
        seen = set()

        def walk(view):
            if id(view) in seen:
                return
            seen.add(id(view))
            restyle = getattr(view, 'restyle', None)
            if callable(restyle):
                try:
                    restyle()
                except Exception as error:
                    print('editorkit windows: restyle failed in %s: %r' % (self.key, error))
            for child in getattr(view, 'subviews', ()) or ():
                walk(child)

        for root in roots:
            walk(root)

    def can_use_console(self):
        """True when this window may go to the console and there is one."""
        return self.allows_console and places.console_container() is not None

    def on(self, event, callback):
        """callback(window, ...) on 'open', 'minimise', 'dock', 'console',
        'close', 'page' (its name), 'under' ((number, text) or None), 'place'
        (old, new: whenever the window changes place), or the editor's
        'text', 'selection' and 'file' (old, new), delivered on the main
        thread while the window is up. 'keyboard' is the old name for
        'dock'."""
        event = self._current_name(event)
        if event in EDITOR_EVENTS:
            self._watch_editor()
        self.listeners[event].append(callback)
        return self

    def _watch_editor(self):
        """Listen to the editor once, for every editor event; stop on close."""
        if self.editor_watch is not None:
            return
        from .. import events
        self.editor_watch = events.on_change(self._editor_changed, kinds=EDITOR_EVENTS)
        handle = self.editor_watch
        self.listeners['close'].append(lambda window: events.remove_listener(handle))

    def _editor_changed(self, change):
        if self.place in ('hidden', 'closed'):
            return
        self._emit(change['kind'], change['old'], change['new'])

    def every(self, callback):
        """callback(now) on every beat of the window's clock while it is up
        (pin, panel, keyboard's place or console): for helpers that belong
        to the window rather than to a page, such as ek.Pair. Returns a Beat:
        beat.stop() ends it. A failing callback is reported once and kept."""
        beat = Beat(callback)
        self.clock.append(beat)
        return beat

    def after(self, seconds, callback):
        """callback(now) once, seconds from now (on the window's clock, so
        while the window is up). Returns a Beat: stop() cancels it."""
        import time
        beat = Beat(callback, at=time.time() + seconds)
        self.clock.append(beat)
        return beat

    def is_up(self):
        """True while the window shows as a panel: over the code, in the
        keyboard's place or over the console (not a pin, hidden or closed)."""
        return self.place in ('panel', 'dock', 'console')

    def is_busy(self):
        """True while a move is running: not the moment to start another."""
        return self._busy()

    def is_held(self):
        """True while the user holds the window to move or resize it."""
        return self.grabbing is not None

    # --- Header buttons -----------------------------------------------

    def add_button(self, icon, action, name=None, on=None):
        """Add a header button showing icon; a tap calls action(window).
        App buttons sit after close and minimise, in the order added, and a
        narrow window drops them before those two. on=True lights it (a
        toggle); see set_button. Same name again replaces it. Returns the name."""
        name = name or icon
        spec = {'name': name, 'icon': icon, 'action': action, 'on': on}
        for index, existing in enumerate(self.app_buttons):
            if existing['name'] == name:
                self.app_buttons[index] = spec
                break
        else:
            self.app_buttons.append(spec)
        self._sync_buttons()
        return name

    def set_button(self, name, on=None, icon=None):
        """Light or unlight a header button (on=True/False) or change its icon."""
        for spec in self.app_buttons:
            if spec['name'] == name:
                if on is not None:
                    spec['on'] = on
                if icon is not None:
                    spec['icon'] = icon
                self._sync_buttons()
                return self
        return self

    def remove_button(self, name):
        """Take away the header button add_button made with this name."""
        self.app_buttons = [spec for spec in self.app_buttons if spec['name'] != name]
        self._sync_buttons()
        return self

    def _sync_buttons(self):
        if self.panel is not None:
            self.panel.sync_app_buttons()

    # --- Sheets, the accessory strip and the page clock ----------------

    @_app.on_main
    def show_sheet(self, view):
        """Lay view over the page area (under the header, tabs and accessory),
        sized by the window and kept across page switches. A new sheet
        replaces the old one, whose sheet_closed(window) is called if it has
        one. None takes the sheet away."""
        old = self.sheet
        self.sheet = view
        if old is not None and old is not view:
            self._call(old, 'sheet_closed')
        if getattr(self, 'full_sheet', None) is not None:
            self.full_sheet.set_overlay(view)   # full screen: shown there
        elif self.panel is not None:
            self.panel.show_sheet(view)
        return self

    def close_sheet(self):
        """Take away the sheet show_sheet laid over the page, if there is one."""
        return self.show_sheet(None)

    @_app.on_main
    def set_accessory(self, view, height=36):
        """A strip under the page tabs, shared by every page; None removes it."""
        self.accessory = (view, height) if view is not None else None
        if self.panel is not None:
            self.panel.set_accessory(view, height)
        return self

    def _call(self, view, name, *args):
        hook = getattr(view, name, None)
        if callable(hook):
            try:
                hook(self, *args)
            except Exception as error:
                print('editorkit windows: %s failed: %r' % (name, error))

    def _tick_pages(self, now):
        """tick(now) on every page view (shown or not), the sheet and the
        accessory, where they have one. A failing view is reported once."""
        views = []
        for _name, thing, view in self.pages:
            if view is None and isinstance(thing, ui.View):
                view = thing
            if view is not None:
                views.append(view)
        if self.sheet is not None:
            views.append(self.sheet)
        if self.accessory is not None:
            views.append(self.accessory[0])
        for view in views:
            tick = getattr(view, 'tick', None)
            if not callable(tick):
                continue
            try:
                tick(now)
            except Exception as error:
                if id(view) not in self.tick_failures:
                    self.tick_failures.add(id(view))
                    print('editorkit windows: %s.tick failed: %r'
                          % (type(view).__name__, error))

    @_app.on_main
    def show(self, page=None):
        """Open from a pin: to the window's home (Window(home=...)), else over
        the code growing out of the pin. A window in the console brings the
        console back."""
        if page is not None:
            self.page = page
        if (self.home == 'dock' and self.allows_dock
                and self.place in ('hidden', 'closed', 'pin', 'tray')):
            result = self.to_dock()
        else:
            result = self._open()
        self._pieces_out()
        return result

    def _open(self):
        """Over the code (or the console, for a console window), ignoring home."""
        if self.place == 'tab':
            # Resting in the tab row: selecting its tab brings it out (follow_tabs).
            from .. import tabs as editor_tabs
            editor_tabs.select_tab(self.tab_path)
            return self
        if self.place in ('hidden', 'closed'):
            self._build()
        elif self._busy():
            return self
        if self.place == 'tray':
            self._tray_to_panel()
        elif self.place == 'pin':
            self._pin_to_panel()
        elif self.place == 'dock':
            self._dock_to_panel()
        elif self.place == 'console':
            places.slide_console(True, look.CONSOLE_SLIDE_SECONDS)
            self._ensure_page()
        elif self.panel is not None:
            self._ensure_page()
        return self

    @_app.on_main
    def minimise(self):
        """Fold away: into its holder's box (its owner's, else the tray
        home's), else into its own pin, so it is never lost. An owner takes
        its open pieces with it. (A new window just appears folded.)
        A full-screen window (to_full) goes back to its normal frame instead;
        minimising again folds it."""
        if self.is_full():
            return self.leave_full()
        if self.minimise_to == 'tab':
            return self.to_tab()                   # rests in the tab row instead
        if self.place not in ('hidden', 'closed') and not self._busy():
            self._pieces_in()
        if self.place in ('hidden', 'closed'):
            self._build()
            if self.folds_to_tray():
                self._enter_tray()
            else:
                self._fade_pin_in()
        elif self._busy():
            return self
        elif self.folds_to_tray() and self.place in ('panel', 'dock', 'console'):
            if self.place == 'dock':
                self._dock_to_tray()
            else:
                self._panel_to_tray()
        elif self.place == 'panel':
            self._panel_to_pin()
        elif self.place == 'dock':
            self._dock_to_pin()
        elif self.place == 'console':
            self._console_to_pin()
        return self

    @_app.on_main
    def to_dock(self):
        """Into the keyboard's place: from over the code it drops in; from a
        pin it rises straight in (a pin in the console goes via a panel)."""
        if not self.allows_dock or self._busy():
            return self
        if self.place == 'panel':
            self._panel_to_dock()
        elif self.place == 'tray':
            self.manager.tray_remove(self)
            self._pin_to_dock()
        elif self.place in ('hidden', 'closed', 'pin'):
            if self.place == 'pin' and self.pin_home == 'console':
                self._open()
                self.manager.timeline.book(look.GROW_SECONDS + look.CONTENT_FADE_SECONDS,
                                           'then to keyboard', self._panel_to_dock, self)
            else:
                self._pin_to_dock()
        return self

    def tray(self):
        """Windows waiting in the tray, most recently minimised first (for a
        tray home's bar)."""
        return self.manager.tray_windows(self) if self.manager is not None else []

    # --- Owners and boxes -----------------------------------------------------

    def holder(self):
        """The window whose box this one folds into: its owner while the
        owner is open, else the tray home, else None (its own pin)."""
        owner = self.owner
        if owner is not None and owner is not self and owner.place not in ('hidden', 'closed'):
            return owner
        home = self.manager.tray_home() if self.manager is not None else None
        return home if home is not None and home is not self else None

    def folds_to_tray(self):
        """– goes into a box: the window folds to the tray and has a holder."""
        return self.minimise_to == 'tray' and self.holder() is not None

    def pieces(self):
        """The live windows this one owns."""
        if self.manager is None:
            return []
        return [window for window in self.manager.windows.values()
                if getattr(window, 'owner', None) is self]

    def _pieces_in(self):
        """Folding an owner: its open pieces fold into its box first, and are
        remembered so showing it brings them back out."""
        self.pieces_out = []
        for piece in self.pieces():
            if piece.place in ('panel', 'dock', 'console'):
                self.pieces_out.append(piece.key)
                piece.minimise()

    def _pieces_out(self):
        keys, self.pieces_out = self.pieces_out, []
        for piece in self.pieces():
            if piece.key in keys and piece.place == 'tray':
                piece.show()

    def _refresh_box(self):
        """An owner's automatic box row under the header: there while pieces
        are folded into it, gone when it is empty. Left alone on the tray
        home and on windows with an accessory of their own."""
        if self.tray_home or self.manager is None:
            return
        from ..native.box import Box
        current = self.accessory[0] if self.accessory is not None else None
        if current is not None and current is not self.box_view:
            return
        folded = self.manager.tray_windows(self)
        if folded:
            if self.box_view is None:
                self.box_view = Box(self)
                self.set_accessory(self.box_view, Box.HEIGHT)
            self.box_view.show(folded)
        elif self.box_view is not None:
            self.box_view = None
            self.set_accessory(None)

    @_app.on_main
    def to_panel(self):
        """Back over the code."""
        if self._busy():
            return self
        if self.place == 'dock':
            self._dock_to_panel()
        elif self.place == 'console':
            self._console_to_panel()
        elif self.place in ('hidden', 'closed', 'pin', 'tray'):
            self._open()
        return self

    @_app.on_main
    def to_console(self):
        """Over the console, which slides in to take it."""
        if self._busy() or not self.can_use_console():
            return self
        if self.place == 'panel':
            self._panel_to_console()
        elif self.place in ('hidden', 'closed', 'pin'):
            self._open()                            # a console pin opens in the console
            if self.pin_home != 'console':
                self.manager.timeline.book(look.GROW_SECONDS + look.CONTENT_FADE_SECONDS,
                                           'then to console', self._panel_to_console, self)
        return self

    @_app.on_main
    def close(self):
        """Shrink away and remove the window (and its pieces). Safe to call
        twice."""
        if self.place in ('hidden', 'closed'):
            return
        for piece in self.pieces():
            piece.close()
        manager = self.manager
        manager.timeline.cancel(self)
        place = self.place
        self.place = 'closed'
        self._page_hook('page_hidden')
        if place == 'dock':
            self._hold_picture(self._dock_frame())
            manager.dock.give_back(self)
            ghost = self.ghost
            ui.animate(lambda: setattr(ghost, 'alpha', 0.0), look.CLOSE_SECONDS)
        elif place in ('panel', 'console'):
            panel = self.panel
            x, y, width, height = places.frame_of(panel)
            end = (x + width * 0.1, y + height * 0.1, width * 0.8, height * 0.8)

            def vanish():
                panel.frame = end
                panel.alpha = 0.0
            ui.animate(vanish, look.CLOSE_SECONDS)
        pin = self.pin
        pin.touch_enabled = False
        ui.animate(lambda: setattr(pin, 'alpha', 0.0), look.CLOSE_SECONDS)
        manager.timeline.book(look.CLOSE_SECONDS, 'closed', self._remove_views, self)
        if manager.windows.get(self.key) is self:
            del manager.windows[self.key]
        manager.tray_remove(self)
        self._emit('close')

    @_app.on_main
    def set_page(self, name):
        """Show the page called name (one add_page made); fires 'page'."""
        if name not in self.page_names() or name == self.page:
            return
        self._page_hook('page_hidden')
        self.page = name
        # Every place where the panel shows its page; a pin shows none.
        if self.place in ('panel', 'dock', 'console'):
            self._ensure_page()
        if self.panel is not None:
            self.panel.set_tabs(self.page_names(), self.page)
        self._emit('page', name)

    @_app.on_main
    def set_title(self, text):
        """Change the title in the header (the full-screen header follows)."""
        self.title = text
        if getattr(self, 'full_sheet', None) is not None:
            self.full_sheet.refresh()    # full screen: the sheet's header follows
        if self.panel is not None:
            self.panel.refresh()

    @_app.on_main
    def set_full_look(self, background=None, button=None, text=None, accent=None, header=True):
        """This window's colours while full screen: the sheet and its header
        (background), the header buttons (button, with accent icons) and the
        title (text). None keeps the palette's colour. A game whose page has
        its own background passes it here so the screen is one surface.
        header=False hides the header altogether: the page draws its own
        and must offer a way back (window.leave_full, window.close)."""
        self.full_look = {'background': background, 'button': button,
                          'text': text, 'accent': accent, 'header': header}
        if getattr(self, 'full_sheet', None) is not None:
            self.full_sheet.restyle()

    @_app.on_main
    def set_pin_text(self, text):
        """Words beside the emoji in the pin (None: just the emoji)."""
        self.pin_words = text
        if self.pin is None:
            return
        self.pin.set_text(self.pin_text())
        if self.place == 'pin' and not self.pin.dragging and not self._busy():
            self.pin.frame = self._pin_frame()

    def pin_text(self):
        """The emoji at the end of the pin nearest its edge, matching the header."""
        if not self.pin_words:
            return self.emoji
        if self.pin_place and self.pin_place[0] == 'right':
            return '%s %s' % (self.pin_words, self.emoji)
        return '%s %s' % (self.emoji, self.pin_words)

    # ==== The clock ====

    def _tick(self, now):
        """One beat of this window, from the Manager's clock."""
        if self.place != self.last_place:
            old, self.last_place = self.last_place, self.place
            self._emit('place', old, self.place)
        if self.place in ('hidden', 'closed'):
            return
        if now >= self.next_page_tick:
            self.next_page_tick = now + PAGE_TICK_SECONDS
            self._tick_pages(now)
        pin = self.pin
        if (pin.pressed_at is not None and not pin.dragging
                and now - pin.pressed_at >= look.HOLD_SECONDS):
            self._lift_pin()
        for grip in (self.panel.emoji, self.panel.backdrop):
            if (grip.pressed_at is not None and self.grabbing is None
                    and now - grip.pressed_at >= look.HOLD_SECONDS):
                grip.pressed_at = None
                self._grab('move')
        self._check_edge(now)
        if self.place == 'dock' and not self._busy():
            keyboard = self.manager.dock
            if keyboard.window is not self or keyboard.lost():
                # The keyboard was put away, or another window took its place.
                keyboard.give_back(self)
                self.place = 'pin'
                self._fade_pin_in()
                self._emit('minimise')
        if (self.place == 'pin' and self.pin_home == 'editor' and not pin.dragging
                and self.listeners['under']):
            self._look_under_pin()
        for beat in list(self.clock):
            if beat.stopped:
                self.clock.remove(beat)
                continue
            if beat.at is not None:
                if now < beat.at:
                    continue
                self.clock.remove(beat)       # a one-off runs once
            try:
                beat.callback(now)
            except Exception as error:
                if id(beat) not in self.tick_failures:
                    self.tick_failures.add(id(beat))
                    print('editorkit windows: clock %r failed: %r' % (beat.callback, error))

    def _is_dragging(self):
        return self.pin is not None and (self.pin.dragging or self.grabbing is not None)

    def _emit(self, event, *values):
        for callback in list(self.listeners.get(event, ())):
            try:
                callback(self, *values)
            except Exception as error:
                print('editorkit windows: %s callback failed: %r' % (event, error))

    # ==== Building and removing ====

    def _build(self):
        manager = _manager()
        old = manager.windows.get(self.key)
        if old is not None and old is not self:
            old._dismantle()              # same key again: the new one replaces it
        self.manager = manager
        self.palette = manager.palette
        self.pin = Pin(self, manager.palette)
        self.panel = Panel(self, manager.palette)
        try:
            from . import holdmove
            holdmove.attach(self)      # hold anywhere on the panel to move it
        except Exception as error:
            print('editorkit windows: hold to move unavailable: %r' % (error,))
        self.ghost = ui.View(background_color=look.CLEAR)
        self.ghost.touch_enabled = False
        self.dock_line = ui.View(background_color=manager.palette.accent)
        self.dock_line.touch_enabled = False
        for view in (self.pin, self.panel, self.ghost, self.dock_line):
            _app.prepare(view)
        for entry in self.pages:
            entry[2] = None
        self.panel.set_tabs(self.page_names(), self.page)
        if self.accessory is not None:
            self.panel.set_accessory(*self.accessory)
        if self.sheet is not None:
            self.panel.show_sheet(self.sheet)
        stacked = len(manager.windows)
        self.pin_place = _remembered('pins').get(self.key) or (
            'right', look.EDGE, look.EDGE + stacked * (look.PIN_HEIGHT + look.PIN_STACK_GAP))
        self.pin_home = _remembered('pin_homes').get(self.key, 'editor')
        if self.pin_home == 'console' and places.console_container() is None:
            self.pin_home = 'editor'
        manager.windows[self.key] = self
        self.pin.set_text(self.pin_text())
        self.pin.alpha = 0.0
        self.pin.frame = self._pin_frame()
        self._put_in(self.pin, self.pin_home)
        self.place = 'pin'
        self.under = self.under_key = None

    def _remove_views(self):
        self._clear_picture()
        for view in (self.pin, self.panel, self.dock_line):
            if view is not None:
                places.take_away(view)

    def _dismantle(self):
        """Remove at once, with no motion (a replacement, or stop())."""
        if self.place in ('hidden', 'closed'):
            return
        manager = self.manager
        manager.timeline.cancel(self)
        if self.place == 'dock':
            manager.dock.give_back(self)
        self._page_hook('page_hidden')
        self.place = 'closed'
        self._remove_views()
        if manager.windows.get(self.key) is self:
            del manager.windows[self.key]
        manager.tray_remove(self)
        self._emit('close')

    # ==== Pages ====

    def _entry(self, name):
        for entry in self.pages:
            if entry[0] == name:
                return entry
        return None

    def _ensure_page(self):
        entry = self._entry(self.page)
        if entry is None or self.panel is None:
            return
        if entry[2] is None:
            entry[2] = content.view_for(entry[1], self)
        self.panel.show_page(entry[2])
        self.panel.set_tabs(self.page_names(), self.page)
        self._page_hook('page_shown')

    def _page_hook(self, name):
        entry = self._entry(self.page)
        view = entry[2] if entry is not None else None
        hook = getattr(view, name, None)
        if callable(hook):
            try:
                hook(self)
            except Exception as error:
                print('editorkit windows: %s failed: %r' % (name, error))

    # ==== Where things go ====

    def _busy(self):
        return self.manager is not None and self.manager.timeline.busy(self)

    def _hold(self, seconds):
        self.manager.timeline.hold(self, seconds)

    def _book(self, delay, name, step):
        self.manager.timeline.book(delay, name, step, self)


# ---- Module functions --------------------------------------------------------

def live_windows():
    """The windows that are showing (as pins, panels or in the keyboard's
    place), as a new list: always a list, empty when none are. Safe to close
    windows while looping over it."""
    manager = _store().get('manager')
    return list(manager.windows.values()) if manager is not None else []


def show(thing, title=None, key=None, on_pick=None, **options):
    """One line: a window with one page showing thing (anything a page
    takes, a cards.Page included). With a cards.Page, on_pick(item) gets the
    item of whatever card, chip or button is tapped:

        ek.show(page, title='Colours', on_pick=chosen)

    Showing again under the same key (the title, by default) swaps the
    content in place and leaves the window where it is, so show() can run
    in a loop."""
    if on_pick is not None:
        thing = content.Picking(thing, on_pick)
    title = title or content.title_for(thing)
    key = key or title
    for window in live_windows():
        if window.key == key:
            return window.set_page_content(window.page or title, thing)
    window = Window(title, key=key, **options)
    window.add_page(title, thing)
    return window.show()


@_app.on_main
def close_all(at_once=False):
    """Close every window. at_once=True removes them with no motion, and
    the windows' clock too: use it before reloading editorkit's modules."""
    if at_once:
        return stop()
    for window in live_windows():
        window.close()


@_app.on_main
def stop():
    """Remove every window at once, and the clock. Use before reloading modules."""
    manager = _store().pop('manager', None)
    if manager is None:
        return
    for window in list(manager.windows.values()):
        try:
            window._dismantle()
        except Exception as error:
            print('editorkit windows: stop: %r' % (error,))
    manager.swipes.release()
    manager.objc_instance.removeFromSuperview()

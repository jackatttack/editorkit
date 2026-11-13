"""Gestures Part of Window: see window.py."""
import ui

from . import look, places, rules
from .state import _remembered


class Gestures(object):
    """Moving by hand: lifting, dragging and dropping pins, grabbing,
    pulling and releasing panels, holding past an edge to cross, the dock
    line, and the code line under a resting pin."""

    # ==== Dragging the pin ====

    def _lift_pin(self):
        pin = self.pin
        if pin.dragging or self.place != 'pin' or self._busy():
            pin.pressed_at = None
            return
        pin.dragging = True
        pin.pressed_at = None
        self.manager.swipes.block(pin.objc_instance.superview())   # editor or console
        x, y, width, height = places.frame_of(pin)
        grow = look.LIFT_GROW
        lifted = (x - grow, y - grow, width + 2 * grow, height + 2 * grow)

        def lift():
            pin.frame = lifted
            pin.alpha = look.LIFT_ALPHA
        ui.animate(lift, look.LIFT_SECONDS)

    def _drag_pin(self, step_x, step_y):
        self.pin.x += step_x
        self.pin.y += step_y

    def _drop_pin(self, speed_x=0.0):
        """Let go: the pin snaps to the nearer side of its home (a fling: the side
        it was flung at), or stays where it is, and is remembered. Crossing over
        is only by holding at the edge (_check_edge)."""
        pin = self.pin
        pin.dragging = False
        self.edge_since = None
        self.manager.swipes.release()
        area_width, _ = self._home_size()
        place = self._place_from_frame(places.frame_of(pin), area_width, look.SNAP_PINS_TO_SIDES)
        side = self._fling_side(speed_x)
        if side is not None:
            place = (side, look.EDGE, place[2])
        self._set_pin_place(place)
        target = self._pin_frame()

        def settle():
            pin.frame = target
            pin.alpha = 1.0
        ui.animate(settle, look.SNAP_SECONDS)

    def _pin_rim(self):
        """The clear rim around a pin's visible pill (touch pad, plus lift growth)."""
        x, y, width, height = places.frame_of(self.pin)
        return (height - look.PIN_HEIGHT) / 2.0

    def _overhang(self, view, home, rim=0.0):
        """How far view's visible part pokes past the edge it would cross."""
        area_width = places.editor_size()[0] if home == 'editor' else 0.0
        return rules.overhang(places.frame_of(view), home, area_width, rim)

    def _check_edge(self, now):
        """A dragged pin or panel held poking past the crossing edge dims as a
        cue; after EDGE_DWELL_SECONDS it crosses over without waiting for the
        finger to let go. Pulled back in before then, it brightens and stays."""
        if not self.can_use_console():
            return
        if self.pin.dragging:
            view, home = self.pin, self.pin_home
            poking = self._overhang(view, home, self._pin_rim()) >= look.PIN_OVERHANG
            resting_alpha = look.LIFT_ALPHA
        elif self.grabbing == 'move' and self.place in ('panel', 'console'):
            view, home = self.panel, self._host_of_panel()
            poking = self._overhang(view, home) >= look.PANEL_OVERHANG
            # The tab drop owns the top edge: a window lifted above the code is
            # heading for the tab row, never the console. Crossing there mid
            # tab drop crashed Pythonista (2026-11-12).
            tabbing = getattr(self, 'tabbing', False)
            if (poking and self.place == 'panel' and self._takes_tab_drop()
                    and (tabbing or view.y < 0)):
                poking = False
            resting_alpha = look.DOCK_ALPHA if (self.docking or tabbing) else look.GRAB_ALPHA
        else:
            self.edge_since = None
            return
        if not poking:
            if self.edge_since is not None:
                self.edge_since = None
                ui.animate(lambda: setattr(view, 'alpha', resting_alpha), look.LIFT_SECONDS)
            return
        if self.edge_since is None:
            self.edge_since = now
            ui.animate(lambda: setattr(view, 'alpha', look.DOCK_ALPHA), look.LIFT_SECONDS)
            return
        if now - self.edge_since < look.EDGE_DWELL_SECONDS:
            return
        # Held there long enough: cross over now, mid-drag.
        self.edge_since = None
        self.manager.swipes.release()
        if view is self.pin:
            self.pin.dragging = False
            self.pin.pressed_at = None
            if home == 'editor':
                self._pin_to_console()
            else:
                self._pin_to_editor()
        else:
            self.grabbing = None
            self.docking = False
            self.tabbing = False
            self._hide_dock_line()
            self._hide_tab_line()
            self.panel.alpha = 1.0
            if self.place == 'panel':
                self._panel_to_console()
            else:
                self._console_to_panel()

    def _look_under_pin(self):
        """The code scrolls under a resting pin: work out the line beneath it
        when the scroll or the pin has moved, and tell 'under' listeners."""
        key = (places.scroll_key(), tuple(round(value) for value in places.frame_of(self.pin)))
        if key == self.under_key:
            return
        self.under_key = key
        under = places.line_under(self.pin)
        if under != self.under:
            self.under = under
            self.emit('under', under)

    # ==== Holding the panel ====

    def _grab(self, job):
        self.riding = False          # placed by hand now: stop riding the keyboard
        self.docking = False
        self.pulled = 0.0
        if self._busy():
            self.grabbing = None
            return
        if self.place == 'dock' and job == 'move':
            self.grabbing = job                    # a pull up brings it back over the code
            return
        if self.place not in ('panel', 'console'):
            self.grabbing = None
            return
        self.grabbing = job
        # Switch off the swipes above wherever the panel lives (editor or console).
        self.manager.swipes.block(self.panel.objc_instance.superview())
        panel = self.panel
        ui.animate(lambda: setattr(panel, 'alpha', look.GRAB_ALPHA), look.LIFT_SECONDS)
        if job == 'move' and self.place == 'panel' and self.allows_dock:
            self._show_dock_line()
        if job == 'move' and self.place == 'panel' and self._takes_tab_drop():
            self.tabbing = False
            self._show_tab_line()

    def _pull(self, job, step_x, step_y):
        if self.grabbing != job:
            return
        if self.place == 'dock':
            self.pulled += step_y
            if self.pulled < -look.PULL_OUT and not self._busy():
                self.grabbing = None
                self._dock_to_panel()
            return
        panel = self.panel
        if job == 'move':
            panel.x += step_x
            panel.y += step_y
            if self.place == 'panel' and self._takes_tab_drop():
                # Up past the tab line: it brightens and the panel dims, so the
                # finger knows letting go will drop it into the tab row.
                tabbing = panel.y < look.TAB_LINE
                if tabbing != getattr(self, 'tabbing', False):
                    self.tabbing = tabbing
                    self._mark_tab_line(tabbing)
            if self.place != 'panel' or not self.allows_dock:
                return                         # docking is only from over the code
            _, editor_height = places.editor_size()
            docking = panel.y > editor_height * look.DOCK_LINE
            if docking != self.docking:
                # Past the line: it brightens and the panel dims, so the finger
                # knows letting go will dock it.
                self.docking = docking
                line = self.dock_line

                def mark():
                    panel.alpha = look.DOCK_ALPHA if docking else look.GRAB_ALPHA
                    line.alpha = 1.0 if docking else look.DOCK_LINE_ALPHA
                ui.animate(mark, look.LIFT_SECONDS)
        else:
            least_width, least_height = self.min_size
            panel.width = max(least_width, panel.width + step_x)
            panel.height = max(least_height, panel.height + step_y)

    def _release(self, job, speed_x=0.0):
        """Let go of a grip. Past the dock line: the keyboard's place. Otherwise
        the panel stays inside its area (a fling lines it up with the edge it was
        flung at) and its frame is remembered for that area. Crossing to or from
        the console is only by holding at the edge (_check_edge)."""
        if self.grabbing != job:
            return
        self.grabbing = None
        self.edge_since = None
        self._hide_dock_line()
        self._hide_tab_line()
        if self.place == 'dock':
            return                                 # a short pull: nothing happens
        self.manager.swipes.release()
        panel = self.panel
        if job == 'move' and getattr(self, 'tabbing', False):
            self.tabbing = False
            panel.alpha = 1.0
            # Its own drop (a script window: back to its file's tab), else
            # it rests in the tab row as a stand-in tab.
            (getattr(self, 'tab_drop', None) or type(self).to_tab)(self)
            return
        if job == 'move' and self.docking:
            self.docking = False
            panel.alpha = 1.0
            self._panel_to_dock()              # the remembered frame stays as it was
            return
        in_console = self.place == 'console'
        area = places.console_size() if in_console else places.editor_size()
        x, y, width, height = places.frame_of(panel)
        side = self._fling_side(speed_x) if job == 'move' else None
        if side == 'right':
            x = area[0] - look.EDGE - width
        elif side == 'left':
            x = look.EDGE
        target = self._clamp((x, y, width, height), area)
        _remembered('console_frames' if in_console else 'frames')[self.key] = target

        def settle():
            panel.frame = target
            panel.alpha = 1.0
        ui.animate(settle, look.SNAP_SECONDS)

    def _show_dock_line(self):
        editor_width, editor_height = places.editor_size()
        line = self.dock_line
        line.frame = (look.EDGE, round(editor_height * look.DOCK_LINE),
                      editor_width - 2 * look.EDGE, 2)
        line.alpha = 0.0
        places.over_editor(line)
        places.over_editor(self.panel)             # the panel stays above the line
        ui.animate(lambda: setattr(line, 'alpha', look.DOCK_LINE_ALPHA), look.LIFT_SECONDS)

    def _hide_dock_line(self):
        line = self.dock_line
        if line is None or line.objc_instance.superview() is None:
            return
        ui.animate(lambda: setattr(line, 'alpha', 0.0), look.LIFT_SECONDS)

        def remove():
            if self.grabbing is None:
                places.take_away(line)
        self._book(look.LIFT_SECONDS, 'dock line away', remove)

    # --- The tab row as a drop target (win.on_tab_drop) -------------------

    def on_tab_drop(self, callback):
        """Let this window be dropped into Pythonista's tab row: dragged up
        so its top passes look.TAB_LINE above the code, then let go, calls
        callback(window). While it is dragged, a line across the top of the
        code brightens when letting go would drop it. Script windows use it
        to turn back into their file's tab."""
        self.tab_drop = callback
        return self

    def _takes_tab_drop(self):
        """Its own on_tab_drop, or every window while look.TAB_DROP_ALL."""
        return getattr(self, 'tab_drop', None) is not None or look.TAB_DROP_ALL

    def _tab_line_view(self):
        line = getattr(self, 'tab_line', None)
        if line is None:
            line = self.tab_line = ui.View(background_color=self.manager.palette.accent)
            line.touch_enabled = False
        return line

    def _show_tab_line(self):
        editor_width, _ = places.editor_size()
        line = self._tab_line_view()
        line.frame = (look.EDGE, 0, editor_width - 2 * look.EDGE, 3)
        line.alpha = 0.0
        places.over_editor(line)
        places.over_editor(self.panel)             # the panel stays above the line
        ui.animate(lambda: setattr(line, 'alpha', look.DOCK_LINE_ALPHA), look.LIFT_SECONDS)

    def _mark_tab_line(self, tabbing):
        line = self._tab_line_view()
        panel = self.panel

        def mark():
            panel.alpha = look.DOCK_ALPHA if tabbing else look.GRAB_ALPHA
            line.alpha = 1.0 if tabbing else look.DOCK_LINE_ALPHA
        ui.animate(mark, look.LIFT_SECONDS)
        # The tab it would become slides into the row (or away again).
        self._tab_preview_do('show' if tabbing else 'hide')

    def _tab_preview_text(self):
        """What the preview says: the window's own drop (a script window)
        becomes its file's tab, named by the file; otherwise a stand-in
        tab named with the emoji and title."""
        if getattr(self, 'tab_drop', None) is not None:
            return self.title
        return '%s %s' % (self.emoji, self.title) if self.title else self.emoji

    def _tab_preview_do(self, action):
        """Show or hide the preview tab. Never lets a failure reach the drag:
        it prints once and the drag carries on without a preview."""
        try:
            preview = getattr(self, 'tab_preview', None)
            if preview is None:
                if action == 'hide':
                    return
                from .tabpreview import TabPreview
                preview = self.tab_preview = TabPreview(self.manager.palette)
            if action == 'show':
                preview.show(self._tab_preview_text())
            else:
                preview.hide()
        except Exception:
            if not getattr(self, 'tab_preview_failed', False):
                self.tab_preview_failed = True
                import traceback
                print('editorkit windows: tab preview failed:')
                traceback.print_exc()

    def _hide_tab_line(self):
        self._tab_preview_do('hide')
        line = getattr(self, 'tab_line', None)
        if line is None or line.objc_instance.superview() is None:
            return
        ui.animate(lambda: setattr(line, 'alpha', 0.0), look.LIFT_SECONDS)

        def remove():
            if self.grabbing is None:
                places.take_away(line)
        self._book(look.LIFT_SECONDS, 'tab line away', remove)

    # ==== Hold anywhere to move ====

    def no_hold_move(self, view):
        """Leave holds that start on view to view (its own hold-to-act, a
        drag handle): they will not pick the window up."""
        from . import holdmove
        holdmove.skip(self, view)

    def own_drags(self, view):
        """Let view keep the swipes and drags that start on it (a game
        board, a slider of your own): Pythonista's side swipes and hold to
        move then leave them alone, and the header still moves the window.
        Call it from the page's tick: it redoes its work only after the
        window has moved to a new place. See owndrags.py."""
        from . import owndrags
        return owndrags.own(view)

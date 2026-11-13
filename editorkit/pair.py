"""Pair: a view and its input method, working as one tool.

    view = ek.Window('Calc', dockable=False)          # the tool: one pin
    ek.Pair(view, make_keys).show()                    # make_keys() -> a Window
    ek.Pair(board, make_pad, fill=True)                # a board fills above its pad

The view is the tool and owns the only pin. The keys are its input method:
make_keys() builds a fresh keys window (Window(home='dock')) each time
they are summoned, from ⌨ in the view's header, on show(), or by the tool
(say a tap on its input area). While the keys sit in the keyboard's place
the view rides just above them (win.ride_dock); with fill=True it fills the
space above them, below the status bar. Folding the keys (−, or tapping
back into the code) puts them away, with no pin of their own, and the view
stops riding where it is. Once the view has been resized by hand, fill
stops: the view keeps the user's size and only rides above the keys. icon=
sets the view's header button (default ⌨). Moving or resizing the view by
hand puts the keys away too; folding or closing the view does. The keys
follow the view across to the console and back. The Pair ticks itself on
the view's clock.

Where the view is when its keys are summoned (plan_for):

    over the code, console   the keys come at once, on that side
    in the dock              the view hands the keyboard's place over: it
                             lifts out over the code, then the keys come
                             and it rides above them (and stays there when
                             they go)
    pin, tray, hidden        the view comes back over the code first
    closed                   nothing

While the keys are up, a view sent into the dock puts them away first:
only one window holds the keyboard's place. Before this rule a script
window in the dock asked for Scissors, the dock evicted the script window
to the tray, and its fold put the new keys away (2026-11-11).
"""
from . import trace


# --- Settings -------------------------------------------------------------

KEYS_ICON = '⌨'
KEYS_BUTTON = 'keys'           # the view's header button
SUMMON_TRIES = 2               # attempts to land the view before the keys come

# --- The rule: what summoning keys means from each place ---------------------

SHOWING = ('panel', 'console')            # the keys can come at once
LIFT_FIRST = ('dock', 'pin', 'tray', 'hidden')   # the view moves over the code first


def plan_for(place):
    """'bring', 'lift' or 'none' for a view at place (see the module doc)."""
    if place in SHOWING:
        return 'bring'
    if place in LIFT_FIRST:
        return 'lift'
    return 'none'


def is_up(window):
    return window is not None and window.is_up()


class Pair:

    def __init__(self, view, make_keys, fill=False, icon=KEYS_ICON):
        self.view = view
        self.make_keys = make_keys
        self.fill = fill
        self.sized_by_hand = False   # the user resized the view: fill no more
        self.keys = None
        view.add_button(icon, lambda _window: self.toggle_keys(), name=KEYS_BUTTON)
        view.on('minimise', self.view_folded)
        view.on('close', self.view_folded)
        view.on('place', self.view_moved)
        view.every(self.tick)

    def show(self):
        self.view.show()
        self.summon_keys()
        return self

    # --- The keys ---------------------------------------------------------

    def toggle_keys(self):
        if is_up(self.keys):
            self.put_keys_away()
        else:
            self.summon_keys()

    def summon_keys(self, tries=SUMMON_TRIES):
        """Bring the keys, landing the view first when it is in the dock or
        folded (plan_for). Tries again once a move lands; gives up quietly
        (a trace note) rather than fight over the keyboard's place."""
        trace.note('pair summon', 'up' if is_up(self.keys) else 'down', self.view.place)
        if is_up(self.keys):
            return
        plan = plan_for(self.view.place)
        if plan == 'bring':
            self.bring_keys()
        elif plan == 'lift' and tries > 0:
            self.view.to_panel()
            self.view.when_still(lambda view: self.summon_keys(tries - 1))
        else:
            trace.note('pair summon skipped', self.view.place)

    def bring_keys(self):
        keys = self.make_keys()
        # Keys are an input method, not a tool: folding them closes them
        # (put_keys_away), so they never join the tray. release_keys gives
        # the old setting back.
        keys.pair_minimise_before = keys.minimise_to
        keys.minimise_to = 'pin'
        # Keys go to the keyboard's place on the side the view is on.
        keys.dock_host = 'console' if self.view.place == 'console' else 'editor'
        keys.on('dock', self.keys_docked)
        keys.on('minimise', self.keys_folded)
        keys.on('close', self.keys_closed)
        self.keys = keys
        self.view.set_button(KEYS_BUTTON, on=True)
        keys.show()

    def put_keys_away(self):
        trace.note('pair put away')
        keys, self.keys = self.keys, None
        self.view.set_button(KEYS_BUTTON, on=False)
        self.view.stop_riding()
        if keys is not None and keys.place != 'closed':
            keys.close()

    def release_keys(self):
        """Let the keys go without closing them: they become a window of
        their own (Files' script-window preview taking its own keys). Returns
        them, folding to wherever they folded to before the Pair."""
        trace.note('pair release')
        keys, self.keys = self.keys, None
        self.view.set_button(KEYS_BUTTON, on=False)
        self.view.stop_riding()
        if keys is not None:
            keys.minimise_to = getattr(keys, 'pair_minimise_before', keys.minimise_to)
        return keys

    def keys_folded(self, window, *details):
        # Only this Pair's current keys: a released window folds on its own.
        if window is self.keys:
            self.put_keys_away()

    def keys_docked(self, window, *details):
        if window is not self.keys:
            return
        trace.note('pair docked')
        fill = self.fill and not self.sized_by_hand
        self.view.when_still(lambda view: view.ride_dock(fill=fill))

    def keys_closed(self, window, *details):
        if window is self.keys:
            self.keys = None
            self.view.set_button(KEYS_BUTTON, on=False)

    def tick(self, now=None):
        """On the view's clock: moving or resizing the view by hand puts the
        keys away (scrolling it does not); a resize also ends fill, so the
        user's size is kept the next time the keys come up."""
        if not self.view.is_held():
            return
        if getattr(self.view, 'grabbing', None) == 'resize':
            self.sized_by_hand = True
        if is_up(self.keys):
            self.put_keys_away()

    # --- The view ---------------------------------------------------------

    def view_folded(self, window, *details):
        self.put_keys_away()

    def view_moved(self, window, old, new):
        """The view went into the dock: its keys go (one holder only). The
        view crossed to the console or back: the keys follow it (in the
        console, Pythonista focuses the prompt, which would bring up the
        system keyboard instead). Fresh keys once the move has landed."""
        if new == 'dock':
            if is_up(self.keys):
                trace.note('pair view docked: keys away')
                self.put_keys_away()
            return
        if 'console' not in (old, new) or 'panel' not in (old, new):
            return
        trace.note('pair crossed', old, '->', new)
        self.put_keys_away()
        self.view.when_still(lambda view: self.summon_keys())
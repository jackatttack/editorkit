"""🧪 Scratch: throwaway Python pads in one folder (scratch/pads), never
beside your code.

    ＋ New pad      a pad named for the time, opened in the editor
    a pad's card    tap: open it · ▶ run it in the Console · 📌 keep it ·
                    🗑 twice: delete it
    🧹 Clean        the first tap lists what would go (pads not kept, and old
                    scratch_pad.py strays anywhere in Documents); a second
                    tap deletes them for real
    ⚙️ Auto-clean   off, or delete pads not kept that are older than N days,
                    each time Scratch opens (a tap steps through the choices)

The files side is scratch_pads.py; this file only draws it. Pads show as
Toolbox's file cards (filecards).
"""
import os
import time

import editorkit as ek
from editorkit.web import cards
from editorkit.web import tiles as web_tiles

from . import filecards, scratch_pads


# --- Settings -------------------------------------------------------------

TITLE = 'Scratch'
EMOJI = '🧪'
WINDOW_KEY = 'scratch'
START_ZOOM = 0.9
ARM_SECONDS = 8.0            # a Sure? (Clean, 🗑) waits this long for its second tap
STRAYS_SHOWN = 8             # stray paths named in Clean's note
RUN_ICON = '▶'
PIN_ICON = '📌'
DELETE_ICON = '🗑'
EMPTY_NOTE = 'No pads yet. ＋ New pad makes one in scratch/pads and opens it.'


# --- The page -----------------------------------------------------------------

def scratch_page(pad_list, auto_days, clean_plan=None, delete_armed=None, message='', now=None):
    """Buttons, any message, Clean's plan while it waits for its second tap,
    then the pads as cards."""
    now = time.time() if now is None else now
    page = cards.Page()
    if clean_plan is not None:
        count = len(clean_plan[0]) + len(clean_plan[1])
        clean = cards.Action('🧹 Sure? Delete %d' % count, ('clean', None), armed=True, look='warn')
    else:
        clean = cards.Action('🧹 Clean', ('clean', None))
    page.buttons([cards.Action('＋ New pad', ('new', None), look='go'), clean,
                  cards.Action('⚙️ Auto-clean: %s' % auto_label(auto_days), ('auto', None),
                               look='field')])
    if message:
        page.note(message)
    if clean_plan is not None:
        page.note(plan_note(*clean_plan))
    if pad_list:
        page.grid([pad_card(pad, delete_armed == pad.path, now) for pad in pad_list],
                  min_width=filecards.CARD_WIDTH)
    else:
        page.note(EMPTY_NOTE)
    return page


def pad_card(pad, delete_armed, now):
    """A pad as a file card: tap opens it; ▶ 📌 🗑 act on it."""
    card = filecards.file_card(pad.path, ('open', pad.path),
                               where='scratch/pads · %s' % ago(now - pad.modified))
    actions = [cards.Action(RUN_ICON, ('run', pad.path)),
               cards.Action(PIN_ICON, ('pin', pad.name)),
               cards.Action('Sure?' if delete_armed else DELETE_ICON, ('delete', pad.path),
                            armed=delete_armed)]
    return card._replace(title=('📌 ' if pad.pinned else '') + pad.name, actions=actions)


def plan_note(pad_paths, stray_paths):
    if not pad_paths and not stray_paths:
        return 'Nothing to clean.'
    words = '%s not kept and %s. Tap again to delete them.' % (
        plural(len(pad_paths), 'pad'), plural(len(stray_paths), 'old scratch_pad file'))
    if stray_paths:
        named = [os.path.relpath(path, scratch_pads.DOCUMENTS) for path in stray_paths[:STRAYS_SHOWN]]
        more = len(stray_paths) - len(named)
        words += ' Strays: %s%s.' % (', '.join(named), ' and %d more' % more if more else '')
    return words


def ago(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return '%d min ago' % (seconds // 60)
    if seconds < 86400:
        return '%d h ago' % (seconds // 3600)
    return plural(seconds // 86400, 'day') + ' ago'


def auto_label(days):
    return 'off' if not days else plural(days, 'day')


def plural(count, word):
    return '%d %s%s' % (count, word, '' if count == 1 else 's')


# --- The tool -----------------------------------------------------------------

class ScratchTool:

    def __init__(self, window):
        self.window = window
        self.clean_plan = None       # (pads, strays) while Clean waits for its second tap
        self.delete_armed = None     # the pad whose 🗑 was tapped once
        self.armed_until = 0.0
        self.message = ''
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                     zoom_key='scratch', extra_css=filecards.CSS)
        window.add_page(TITLE, self.cards)
        self.opened()

    def opened(self):
        """Scratch opened: auto-clean (when it is on), then draw."""
        days = scratch_pads.load_settings()['auto_clean_days']
        stale = scratch_pads.stale_pads(days)
        if stale:
            deleted, failed = scratch_pads.delete_files(stale)
            self.message = 'Auto-clean deleted %s older than %s.' % (
                plural(deleted, 'pad'), plural(days, 'day'))
        self.refresh()

    def refresh(self):
        now = time.time()
        if now >= self.armed_until:
            self.clean_plan = self.delete_armed = None
        settings = scratch_pads.load_settings()
        self.cards.show(scratch_page(scratch_pads.pads(), settings['auto_clean_days'],
                                     self.clean_plan, self.delete_armed, self.message, now))

    def arm(self, clean_plan=None, delete=None):
        self.clean_plan, self.delete_armed = clean_plan, delete
        self.armed_until = time.time() + ARM_SECONDS
        self.refresh()

    def armed(self):
        return time.time() < self.armed_until

    def picked(self, item):
        kind, value = item
        self.message = ''
        if kind == 'new':
            self.open_pad(scratch_pads.new_pad())
        elif kind == 'open':
            self.open_pad(value)
        elif kind == 'run':
            from . import console
            self.window.minimise()
            console.run_script(value)
        elif kind == 'pin':
            pinned = value in scratch_pads.load_settings()['pinned']
            scratch_pads.set_pinned(value, not pinned)
            self.refresh()
        elif kind == 'delete':
            self.delete_tapped(value)
        elif kind == 'clean':
            self.clean_tapped()
        elif kind == 'auto':
            self.step_auto_clean()

    def open_pad(self, path):
        self.window.minimise()           # out of the way of the pad it opens
        ek.open_file(path)

    def delete_tapped(self, path):
        """First tap: Sure? Second tap on the same pad in time: delete it."""
        if self.delete_armed != path or not self.armed():
            self.arm(delete=path)
            return
        scratch_pads.delete_files([path])
        self.message = 'Deleted %s.' % os.path.basename(path)
        self.armed_until = 0.0
        self.refresh()

    def clean_tapped(self):
        """First tap: work out and show the plan. Second tap in time: delete."""
        if self.clean_plan is None or not self.armed():
            plan = scratch_pads.clean_plan()
            if not plan[0] and not plan[1]:
                self.message = 'Nothing to clean.'
                self.refresh()
                return
            self.arm(clean_plan=plan)
            return
        deleted, failed = scratch_pads.delete_files(self.clean_plan[0] + self.clean_plan[1])
        self.message = 'Deleted %s.' % plural(deleted, 'file')
        if failed:
            self.message += ' %s could not be deleted.' % plural(failed, 'file')
        self.armed_until = 0.0
        self.refresh()

    def step_auto_clean(self):
        choices = scratch_pads.AUTO_CLEAN_CHOICES
        days = scratch_pads.load_settings()['auto_clean_days']
        following = choices[(choices.index(days) + 1) % len(choices)] if days in choices else choices[0]
        scratch_pads.set_auto_clean_days(following)
        self.refresh()


def open_scratch():
    """Open Scratch over the code (or bring it back)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = ScratchTool(window)
    window.scratch_tool = tool
    window.on('open', lambda _window: tool.opened())
    window.show()
    return tool
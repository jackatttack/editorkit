"""Quick: one-tap tools for the open script, or for a script window's file.

open_quick(path) targets a file: while it is the open tab every tool works;
otherwise only the tools marked 'file' (copy, duplicate) show, with 📝 Open
to make it the open tab, after which the full set appears by itself.

Sections of cards on editorkit's card kit (a heading per section, a grid
that reflows to the width, pinch to zoom). ? in the header turns on help
mode: a tap then explains the tool (tiles.Card). Clear and
Delete need a second tap within CONFIRM_SECONDS. Tools that change the
script, or open one, bring the editor forward.

The operations come from deck/scriptops.py (rename the tab follows, delete
closing the tab, script URLs, the scratch pad; ported from Editor Deck).
Replace with clipboard shows what would change as a card page
(deck/diff_rows.py) with Replace and Cancel. The clipboard goes through
editorkit.clip, never the clipboard module.

    from editorkit_toolbox import quick
    quick.open_quick()
"""
import os
import time

import editorkit as ek
from editorkit import clip, layouts, tiles
from editorkit.web import cards, codeview
from editorkit.web import tiles as web_tiles

from . import console, diff_rows, scriptview
from . import scriptops as bridge        # the script operations (was Editor Deck's editor_bridge)


# --- Settings -------------------------------------------------------------

TITLE = 'Quick'
EMOJI = '⚡'
WINDOW_KEY = 'deck-quick'
HELP_ICON = '?'
CONFIRM_SECONDS = 3.0
ARMED_TITLE = 'Tap again'
WARN = '#FF9F43'
DANGER = '#FF5A5F'
START_ZOOM = 0.9                 # the first size; a pinch is remembered
CARD_MIN_WIDTH = 130             # narrowest a card gets before a row drops a column
HELP_NOTE = 'Help: tap a tool to read about it. ? again to finish.'

# The tools, in order: section, icon, title, caption, help, method, tint, confirm.
TOOLS = [
    {'section': 'COPY', 'icon': '📋', 'title': 'Copy Script', 'caption': 'to clipboard',
     'do': 'copy_script', 'file': True,
     'about': 'Copies the whole open script, unsaved edits included. You stay here.'},
    {'section': 'COPY', 'icon': '📂', 'title': 'Copy Path', 'caption': 'to clipboard',
     'do': 'copy_path', 'file': True,
     'about': "Copies the open script's full path, the kind open() expects."},
    {'section': 'COPY', 'icon': '▶️', 'title': 'Run URL', 'caption': 'pythonista3://',
     'do': 'copy_run_url',
     'about': 'Copies a link that opens Pythonista and runs this script (Shortcuts, '
              'bookmarks). Scripts inside Documents only.'},
    {'section': 'COPY', 'icon': '📝', 'title': 'Open URL', 'caption': 'pythonista3://',
     'do': 'copy_open_url',
     'about': 'Copies a link that opens this script without running it.'},
    {'section': 'SCRIPT', 'icon': '🗒️', 'title': 'Scratch Pad', 'caption': 'new tab',
     'do': 'open_scratch_pad',
     'about': 'Creates a blank scratch_pad.py beside the open script and opens it.'},
    {'section': 'SCRIPT', 'icon': '✏️', 'title': 'Rename', 'caption': 'tab follows',
     'do': 'rename',
     'about': "Renames the open script with Pythonista's own rename, so its tab "
              'follows. Leave off the extension to keep it. Taken names are refused.'},
    {'section': 'SCRIPT', 'icon': '📄', 'title': 'Duplicate', 'caption': 'new tab',
     'do': 'duplicate', 'file': True,
     'about': 'Saves a copy beside the script (unsaved edits included) and opens it: in '
              'the editor from the open tab, as a script window from a window.'},

    {'section': 'CLIPBOARD', 'icon': '📥', 'title': 'Replace', 'caption': 'shows changes',
     'do': 'replace_with_clipboard', 'tint': WARN,
     'about': 'Shows what would change (removed red, added green), then Replace on '
              'that sheet swaps the whole script for the clipboard.'},
    {'section': 'CLIPBOARD', 'icon': '➕', 'title': 'Append', 'caption': 'at the end',
     'do': 'append_clipboard',
     'about': "Adds the clipboard's text to the end of the open script."},
    {'section': 'DANGER', 'icon': '🧹', 'title': 'Clear', 'caption': 'tap twice',
     'do': 'clear_script', 'tint': DANGER, 'confirm': True,
     'about': 'Removes every line from the open script. Needs a second tap.'},
    {'section': 'DANGER', 'icon': '🗑️', 'title': 'Delete', 'caption': 'tap twice',
     'do': 'delete_script', 'tint': DANGER, 'confirm': True,
     'about': "Closes the open script's tab and permanently deletes its file. No "
              'undo, no bin. Needs a second tap.'},
]

# Shown instead of the editor-only tools while a targeted script is not the
# open tab.
OPEN_TOOL = {'section': 'SCRIPT', 'icon': '📝', 'title': 'Open', 'caption': 'in the editor',
             'do': 'open_in_editor',
             'about': 'Opens this script in the editor. Every Quick tool then works on it.'}


class QuickTool:
    """The Quick window."""

    def __init__(self, target=None):
        self.target = os.path.realpath(target) if target else None
        self.help_mode = False
        self.armed = None                # the confirm tool waiting for its second tap
        self.armed_until = 0.0
        self.pending_replace = None      # (path, old text, new text) while the diff shows
        self.showing_on_tab = None       # whether the cards drawn are the full set
        title = os.path.basename(self.target) if self.target else TITLE
        self.window = ek.Window(title, emoji=EMOJI, key=WINDOW_KEY)
        self.window.add_button(HELP_ICON, self.toggle_help, name='help')
        self.grid = web_tiles.Cards(self.window, on_pick=self.tapped, zoom=START_ZOOM,
                                zoom_key='quick')
        self.card = web_tiles.Card(self.window, on_close=self.close_help)
        self.prompt = layouts.prompt(self.window)
        self.window.add_page('Quick', self.grid)

        self.window.every(self.tick)
        self.refresh()

    # --- Which script -------------------------------------------------------

    def script_path(self):
        """The script Quick works on: its target, else the open script."""
        return self.target or ek.current_file()

    def on_tab(self):
        """True when the script is the open tab, so every tool works."""
        return self.target is None or console.same_file(self.target, ek.current_file())

    def script_text(self):
        path = self.script_path()
        return console.script_text(path) if path else None

    # --- Cards ------------------------------------------------------------

    def refresh(self):
        if self.pending_replace is not None:
            self.show_diff()             # Replace waits for Replace or Cancel
            return
        self.showing_on_tab = self.on_tab()
        if self.showing_on_tab:
            tools = TOOLS
        else:
            tools = [tool for tool in TOOLS if tool.get('file')] + [OPEN_TOOL]
        page = cards.Page()
        if self.help_mode:
            page.note(HELP_NOTE)
        section, row = None, []
        for tool in tools:
            if tool['section'] != section:
                if row:
                    page.grid(row, min_width=CARD_MIN_WIDTH)
                section, row = tool['section'], []
                page.heading(section)
            armed = self.armed == tool['do']
            row.append(cards.Card(ARMED_TITLE if armed else tool['title'], item=tool,
                                  body=cards.face(tool['icon'], tool['caption']),
                                  colour=DANGER if armed else tool.get('tint')))
        if row:
            page.grid(row, min_width=CARD_MIN_WIDTH)
        self.grid.show(page)

    def tapped(self, tool):
        if isinstance(tool, tuple):      # the diff page's Replace and Cancel
            if tool == ('diff', 'apply') and self.pending_replace is not None:
                self.apply_replace()
            elif tool == ('diff', 'cancel'):
                self.close_diff()
            return
        if self.help_mode:
            self.show_help('%s  %s' % (tool['icon'], tool['title']), tool['about'])
            return
        if tool.get('confirm'):
            if self.armed != tool['do'] or time.time() > self.armed_until:
                self.armed = tool['do']
                self.armed_until = time.time() + CONFIRM_SECONDS
                self.refresh()
                return
            self.disarm()
        elif self.armed:
            self.disarm()
        getattr(self, tool['do'])()

    def disarm(self):
        self.armed = None
        self.armed_until = 0.0
        self.refresh()

    def tick(self, now):
        if self.armed and time.time() > self.armed_until:
            self.disarm()
        if self.on_tab() != self.showing_on_tab:
            self.refresh()               # the target became (or stopped being) the open tab

    # --- Help ---------------------------------------------------------------

    def toggle_help(self, *ignored):
        self.help_mode = not self.help_mode
        self.window.set_button('help', on=self.help_mode)
        self.refresh()                   # the help note comes and goes
        if not self.help_mode:
            self.close_help()

    def show_help(self, title, text):
        self.card.set_text('%s\n\n%s' % (title, text))
        self.window.show_sheet(self.card)

    def close_help(self, *ignored):
        if self.window.sheet is self.card:
            self.window.close_sheet()

    def minimise(self):
        self.window.minimise()

    # --- Copy ---------------------------------------------------------------

    def has_script(self):
        path = self.script_path()
        if path and (self.target is None or os.path.isfile(path)):
            return True
        bridge.hud('No script', 'error')
        return False

    def copy_script(self):
        if self.has_script():
            clip.set_text(self.script_text() or '')
            bridge.hud('Script copied')

    def copy_path(self):
        if self.has_script():
            clip.set_text(self.script_path())
            bridge.hud('Path copied')

    def copy_run_url(self):
        self.copy_url('run')

    def copy_open_url(self):
        self.copy_url('open')

    def copy_url(self, action):
        url = bridge.script_url(action)
        if url:
            clip.set_text(url)
            bridge.hud('%s URL copied' % action.title())
        else:
            bridge.hud('No URL for this file', 'error', 1.2)

    # --- Script -------------------------------------------------------------

    def open_scratch_pad(self):
        bridge.open_scratch_pad()

    def rename(self):
        if not self.has_script():
            return
        name = os.path.basename(ek.current_file())
        self.prompt.ask('Rename %s' % name, name, on_answer=self.rename_to)

    def rename_to(self, typed):
        if bridge.rename_active_script(typed):        # says why on a problem
            bridge.bring_editor_forward()

    def duplicate(self):
        """From the open tab: the bridge's copy, opened in the editor. From a
        script window's file: a copy beside it, opened as a script window."""
        if self.on_tab():
            copy_path = bridge.duplicate_active_script()
            if copy_path:
                bridge.open_script(copy_path)
            return
        if not self.has_script():
            return
        text = self.script_text()
        if text is None:
            bridge.hud("Can't read the script", 'error')
            return
        copy_path = bridge.next_duplicate_path(self.target)
        with open(copy_path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        bridge.hud('Saved %s' % os.path.basename(copy_path))
        scriptview.open_script_window(copy_path)

    def open_in_editor(self):
        """📝 Open: make the target the open tab (tick then shows every tool)."""
        if self.has_script():
            bridge.open_script(self.target)

    # --- Clipboard ----------------------------------------------------------

    def replace_with_clipboard(self):
        """First step: show what would change. Replace on the sheet applies
        exactly the texts it showed (apply_replace)."""
        if not self.has_script():
            return
        new_text, old_text = clip.text(), ek.text()
        if not new_text.strip():
            bridge.hud('Clipboard is empty', 'error')
            return
        if new_text == old_text:
            bridge.hud('Clipboard matches the script')
            return
        self.pending_replace = (ek.current_file(), old_text, new_text)
        self.refresh()

    def show_diff(self):
        """What Replace would change, as the page: a heading, the summary,
        Replace and Cancel, then the lines (removed struck through, added
        green, a little context around each change)."""
        path, old_text, new_text = self.pending_replace
        rows, added, removed = diff_rows.diff_rows(old_text, new_text)
        page = cards.Page()
        page.heading('Replace %s with the clipboard?' % os.path.basename(path or 'the script'))
        page.note(diff_rows.summary(added, removed))
        page.buttons([cards.Action('Replace', ('diff', 'apply'), look='warn'),
                      cards.Action('Cancel', ('diff', 'cancel'))])
        html, items = page.section()
        rows_html, rows_items = codeview.rows_section(1, '', rows)
        items = dict(items)
        items.update(rows_items)
        self.grid.shown_page = None      # the next tool page always redraws
        self.grid.set_section((html + rows_html, items))

    def apply_replace(self):
        path, old_text, new_text = self.pending_replace
        self.close_diff()
        if ek.current_file() != path or ek.text() != old_text:
            bridge.hud('Script changed; tap Replace again', 'error', 1.2)
            return
        if bridge.replace_active_text(new_text):
            bridge.hud('Script replaced')
            bridge.bring_editor_forward()

    def close_diff(self):
        self.pending_replace = None
        self.refresh()

    def append_clipboard(self):
        if self.has_script() and bridge.append_to_active_text(clip.text()):
            bridge.hud('Clipboard appended')
            bridge.bring_editor_forward()

    # --- Danger -------------------------------------------------------------

    def clear_script(self):
        if bridge.replace_active_text(''):
            bridge.hud('Script cleared')
            bridge.bring_editor_forward()

    def delete_script(self):
        bridge.delete_active_script()     # closes the tab and shows the editor itself


def open_quick(target=None):
    """Open Quick over the code, for target (a script window's file) or the
    open script. One Quick window: a new call retargets it."""
    tool = QuickTool(target)
    tool.window.show()
    return tool
"""📦 Packages: find, inspect, install and remove Python packages from PyPI.

The engine is Pipista's, vendored in deck/packages (standard library only):
downloads are checked and verified, archives are unpacked safely, nothing
runs setup.py, and a dependency plan shows everything that will happen
before anything changes. Toolbox keeps its own records in
Documents/.editorkit/packages, so it only removes what it installed itself;
everything else importable shows read-only under Installed.

    🔎 Find        suggestions, PyPI index matches as you type, any exact name
    tap a package  Inspect: its dependency plan, then 📦 Install
    📦 Installed   what Toolbox installed (🗑 twice to remove), then the rest
                   of your environment, read-only (tap one: Explain)

Network work runs on two Jobs: lookups (search index, inspect) and changes
(install, remove), so a new search never cancels an install part way.

    from editorkit_toolbox import packages_tool
    packages_tool.open_packages()
"""
import os
import time

import editorkit as ek

from .docs import card_kit, layouts, web_tiles
from .packages import catalog, dependencies, engine, environment, pypi


# --- Settings -------------------------------------------------------------

TITLE = 'Packages'
EMOJI = '📦'
WINDOW_KEY = 'deck-packages'
STATE_FOLDER = os.path.expanduser('~/Documents/.editorkit/packages')   # Toolbox's own records
FIELD_HINT = 'Search packages, or type an exact name'
START_ZOOM = 0.9
CARD_WIDTH = 200
CATALOGUE_SHOWN = 40
INDEX_SHOWN = 40
NOT_OURS = ("{name} is already installed outside Toolbox (by Pipista, StaSh or by hand), "
            "so Toolbox will not overwrite its files. It shows under Installed, read-only; "
            "to manage it here, remove it with the tool that installed it, then install it here.")
CONFIRM_SECONDS = 3.0        # a second 🗑 within this removes
COLOURS = {'tested': '#5FD3BC', 'candidate': '#F5C26B', 'pypi': '#4FA3FF',
           'managed': '#8E6CEF'}
HOW = ('Tap a package to inspect it: you see every package it would install '
       'before anything changes. Pure-Python packages work best.')
TRUST = ('Installing imports the package to check it works, which runs its code: '
         'install packages you trust.')
NO_INDEX = ("Download PyPI's list of names once to search all of PyPI as you type. "
            'Without it, type an exact name and inspect it.')


# --- Reading what the engine gives back (pure) -------------------------------

def name_of(item):
    """The package name in whatever shape a source gives it: a name, or a
    dict with name, package, project or import_name."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ('name', 'package', 'project', 'import_name'):
            if item.get(key):
                return str(item[key])
        return ''
    return str(getattr(item, 'name', item))


def plan_counts(plan):
    """(names the plan would install, blockers as sentences)."""
    to_install = [name_of(item) for item in plan.get('items') or []
                  if item.get('status') == 'install']
    blockers = ['%s: %s' % (blocker.get('package', ''), blocker.get('message', ''))
                for blocker in plan.get('blockers') or []]
    return to_install, blockers


def friendly_error(traceback_text, name=''):
    """A failed job's traceback as one plain sentence: an install that would
    overwrite files Toolbox does not manage says so; anything else is its
    last line without the module path ('InstallConflictError: ...')."""
    lines = [line for line in (traceback_text or '').strip().splitlines() if line.strip()]
    last = lines[-1].strip() if lines else 'unknown error'
    if 'InstallConflictError' in last:
        return NOT_OURS.format(name=name or 'This package')
    kind, colon, words = last.partition(': ')
    if colon and '.' in kind:
        last = '%s: %s' % (kind.rsplit('.', 1)[-1], words)
    return 'Could not do that: %s' % last


def plural(count, word):
    return '%d %s%s' % (count, word, '' if count == 1 else 's')


# --- Pages (pure) --------------------------------------------------------------

def mode_chips(page, mode):
    page.chips([card_kit.Chip('🔎 Find', item=('mode', 'find'), on=mode == 'find'),
                card_kit.Chip('📦 Installed', item=('mode', 'installed'), on=mode == 'installed')])


def find_page(query, catalogue_items, index_items, index_status, message=''):
    """Suggestions, then PyPI index matches, then Inspect for an exact name,
    then the index's state with its button."""
    page = card_kit.Page()
    mode_chips(page, 'find')
    if message:
        page.note(message)
    if not query:
        page.note(HOW)
    shown = set()
    suggested = []
    for item in catalogue_items:
        name = name_of(item)
        shown.add(name.lower())
        details = item if isinstance(item, dict) else {}
        status = details.get('status') or 'candidate'
        suggested.append(card_kit.Card(name, item=('inspect', name),
                                       body=card_kit.text(details.get('description') or status),
                                       colour=COLOURS.get(status, COLOURS['candidate'])))
    if suggested:
        page.heading('Suggested · green ones are tested on Pythonista')
        page.grid(suggested, min_width=CARD_WIDTH)
    on_pypi = []
    for item in index_items:
        name = name_of(item)
        if name and name.lower() not in shown:
            shown.add(name.lower())
            on_pypi.append(card_kit.Card(name, item=('inspect', name),
                                         body=card_kit.text('on PyPI'), colour=COLOURS['pypi']))
    if on_pypi:
        page.heading('On PyPI')
        page.grid(on_pypi, min_width=CARD_WIDTH)
    if query and query.lower() not in shown:
        page.buttons([card_kit.Action('🔎 Inspect "%s" on PyPI' % query, ('inspect', query))])
    if index_status.get('ready'):
        page.note('PyPI index: %s names, searched as you type.' % index_status.get('count', '?'))
        page.buttons([card_kit.Action('↻ Refresh the PyPI index', ('sync',))])
    else:
        page.note(NO_INDEX)
        page.buttons([card_kit.Action('⬇ Download the PyPI index', ('sync',))])
    return page


def plan_page(name, inspection, plan, message='', busy=False):
    """One package: what PyPI says, the plan, and Install when nothing blocks it."""
    page = card_kit.Page()
    page.chips([card_kit.Chip('◀ Back', item=('back',))])
    details = inspection if isinstance(inspection, dict) else {}
    page.heading('%s %s' % (name, details.get('version') or ''))
    if details.get('summary'):
        page.note(details['summary'])
    latest = details.get('latest_version')
    if latest and details.get('version') and latest != details['version']:
        page.note('The newest version that runs on this Python. The latest, %s, '
                  'needs a newer Python than Pythonista has.' % latest)
    if message:
        page.note(message)
    if plan is None:
        if not message:
            page.note('Looking it up and working out what it needs...')
        return page
    to_install, blockers = plan_counts(plan)
    lines = [line for line in dependencies.format_plan(plan).splitlines() if line.strip()]
    page.grid([card_kit.Card('The plan', body=''.join(card_kit.text(line) for line in lines))],
              min_width=CARD_WIDTH)
    if blockers:
        page.note('Blocked, so nothing will be installed: ' + '; '.join(blockers))
    elif busy:
        page.note('Installing...')
    elif to_install:
        page.buttons([card_kit.Action('📦 Install %s' % plural(len(to_install), 'package'),
                                      ('install',))])
    else:
        page.note('Nothing to install: everything it needs is already here.')
    page.note(TRUST)
    return page


def installed_page(managed, environment_groups, armed=None, message=''):
    """What Toolbox installed (removable), then the rest, read-only."""
    page = card_kit.Page()
    mode_chips(page, 'installed')
    if message:
        page.note(message)
    page.heading('Installed by Toolbox · %d' % len(managed))
    if managed:
        cards = []
        for record in managed:
            name = name_of(record)
            is_armed = name == armed
            cards.append(card_kit.Card(
                name, colour=COLOURS['managed'],
                body=card_kit.text(str(record.get('version') or '') if isinstance(record, dict) else ''),
                actions=[card_kit.Action('Sure?' if is_armed else '🗑', ('remove', name),
                                         armed=is_armed)]))
        page.grid(cards, min_width=CARD_WIDTH)
    else:
        page.note('Nothing yet: find a package and install it.')
    for key, title in (('user', 'Your other packages · read-only'),
                       ('bundled', 'Built into Pythonista · read-only')):
        items = environment_groups.get(key) or []
        if isinstance(items, dict):
            items = list(items.values())
        names = sorted(set(name for name in (name_of(item) for item in items) if name),
                       key=str.lower)
        if names:
            page.heading('%s · %d' % (title, len(names)))
            page.chips([card_kit.Chip(name, item=('module', name)) for name in names])
    return page


# --- The tool -----------------------------------------------------------------

class PackagesTool:

    def __init__(self, window):
        self.window = window
        self.mode = 'find'
        self.query = ''
        self.inspecting = None       # (name, inspection, plan) while a package shows
        self.message = ''
        self.armed = None            # the package whose 🗑 waits for a second tap
        self.armed_until = 0.0
        self.busy = False            # an install or remove is running
        self.manager = engine.PackageManager(state_dir=STATE_FOLDER)
        self.index = pypi.PyPIIndex(state_dir=STATE_FOLDER)
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                     zoom_key='packages')
        self.view = layouts.query_list(window, FIELD_HINT, on_change=self.typed,
                                       body=self.cards, compact_in_dock=False)
        self.lookups = ek.Job(window, self.lookup_work, on_items=self.progress,
                              on_done=self.looked_up, on_error=self.failed)
        self.changes = ek.Job(window, self.change_work, on_done=self.changed,
                              on_error=self.failed)
        self.refresh()

    # --- Drawing ------------------------------------------------------------

    def refresh(self):
        if self.inspecting is not None:
            name, inspection, plan = self.inspecting
            page = plan_page(name, inspection, plan, self.message, self.busy)
        elif self.mode == 'installed':
            managed = self.manager.installed()
            armed = self.armed if time.time() < self.armed_until else None
            page = installed_page(managed, environment.scan_environment(managed), armed,
                                  self.message)
        else:
            status = self.index.status()
            found = (self.index.search(self.query, limit=INDEX_SHOWN)
                     if self.query and status.get('ready') else [])
            page = find_page(self.query, catalog.catalogue_matches(self.query, limit=CATALOGUE_SHOWN),
                             found, status, self.message)
        self.cards.show(page)

    def typed(self, field, text):
        self.query = text.strip()
        self.mode = 'find'
        self.inspecting = None
        self.message = ''
        self.refresh()

    def picked(self, item):
        kind = item[0]
        if kind == 'mode':
            self.mode, self.inspecting, self.message = item[1], None, ''
        elif kind == 'back':
            self.inspecting, self.message = None, ''
        elif kind == 'inspect':
            self.inspecting, self.message = (item[1], None, None), ''
            self.lookups.start('inspect', item[1])
        elif kind == 'sync':
            self.message = 'Downloading the PyPI index...'
            self.lookups.start('sync', None)
        elif kind == 'install':
            self.install()
        elif kind == 'remove':
            self.remove_tapped(item[1])
        elif kind == 'module':
            from . import explain
            explain.open_explain().hold_name(item[1])
            return
        self.refresh()

    # --- Lookups (a thread: no ui here) ---------------------------------------

    def lookup_work(self, run, what, name):
        if what == 'sync':
            self.index.sync(progress=lambda *parts, **more: run.put(parts))
            return ('synced', None, None)
        inspection = self.manager.inspect_pypi(name)
        if run.cancelled:
            return None
        plan = dependencies.build_dependency_plan(name, self.manager)
        return ('inspected', name, (inspection, plan))

    def progress(self, batches):
        latest = ' '.join(str(part) for part in batches[-1]) if batches else ''
        self.message = 'Downloading the PyPI index... %s' % latest
        self.refresh()

    def looked_up(self, result):
        if result is None:
            return
        kind, name, value = result
        if kind == 'synced':
            self.message = 'PyPI index ready: type to search all of PyPI.'
        elif self.inspecting is not None and self.inspecting[0] == name:
            self.inspecting = (name, value[0], value[1])
        self.refresh()

    # --- Changes (a thread: no ui here) -------------------------------------

    def install(self):
        if self.busy or self.inspecting is None or self.inspecting[2] is None:
            return
        self.busy = True
        self.message = ''
        self.changes.start('install', self.inspecting[2])

    def remove_tapped(self, name):
        if self.busy:
            return
        if self.armed != name or time.time() >= self.armed_until:
            self.armed, self.armed_until = name, time.time() + CONFIRM_SECONDS
            return
        self.armed, self.armed_until = None, 0.0
        self.busy = True
        self.message = 'Removing %s...' % name
        self.changes.start('remove', name)

    def change_work(self, run, what, value):
        if what == 'install':
            dependencies.execute_dependency_plan(value, self.manager)
            return ('installed', None)
        self.manager.uninstall(value)
        return ('removed', value)

    def changed(self, result):
        self.busy = False
        kind, value = result
        if kind == 'installed' and self.inspecting is not None:
            name = self.inspecting[0]
            self.message = '✓ Installed. Try it in a script: import %s' % name.replace('-', '_')
            self.inspecting = (name, self.inspecting[1], None)
            self.lookups.start('inspect', name)      # the plan again: now nothing to install
        elif kind == 'removed':
            self.message = '✓ Removed %s.' % value
        self.refresh()

    def failed(self, error):
        self.busy = False
        name = self.inspecting[0] if self.inspecting is not None else ''
        self.message = friendly_error(error, name)
        self.refresh()


def open_packages():
    """Open Packages over the code (or bring it back)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = PackagesTool(window)
    window.packages_tool = tool
    window.on('open', lambda _window: tool.refresh())
    window.show()
    return tool
"""🎓 Learn: the lessons and examples that come with Toolbox, one tap away.

The installer puts them in Documents/Toolbox/lessons and /examples. Learn
shows them as cards in the same style as Files and Snippets: lessons in
order (their steps on the card), then the examples grouped by the first
word of their name (tool_, window_, editor_, theme_). Chips along the top
show everything, one lesson pack, or the examples. A tap opens the script in the editor (▶ runs
it); 📜 opens it in a script window. ℹ️ in the header says what Toolbox and
editorkit are (ABOUT; the hub's ℹ️ About shows it too).

♻️ Restore, at the top, puts back any lesson or example that was changed or
deleted, from the installer's untouched copies in Documents/Toolbox/.originals.
A changed file is moved aside to Documents/_to_delete first (fileops.trash),
never overwritten, and files you added yourself are never touched.

Lesson packs: Toolbox's own (editorkit's lessons, then Pythonista's own
modules), and any other a JSON file in Documents/Toolbox/packs/ names, the
way tool plugins join the hub:

    {"name": "My library", "emoji": "📦", "folder": "projects/mylib/lessons",
     "about": "What the lessons teach, in a line."}

folder is relative to Documents (or absolute). A file that cannot be read
shows as a note in Learn; Learn still opens.

    from editorkit_toolbox import learn
    learn.open_learn()
"""
import ast
import filecmp
import html
import json
import os
import shutil
import time

import editorkit as ek
from editorkit import fileops

from . import filecards, search
from .docs import card_kit, web_tiles


# --- Settings ---------------------------------------------------------------

TITLE = 'Learn'
EMOJI = '🎓'
WINDOW_KEY = 'deck-learn'
DOCUMENTS = os.path.expanduser('~/Documents')
TOOLBOX_HOME = os.path.join(DOCUMENTS, 'Toolbox')
LESSONS_FOLDER = os.path.join(TOOLBOX_HOME, 'lessons')
EXAMPLES_FOLDER = os.path.join(TOOLBOX_HOME, 'examples')
ORIGINALS_FOLDER = os.path.join(TOOLBOX_HOME, '.originals')   # the installer's untouched copies
PYTHONISTA_LESSONS_FOLDER = os.path.join(TOOLBOX_HOME, 'pythonista_lessons')
PACKS_FOLDER = os.path.join(TOOLBOX_HOME, 'packs')   # lesson packs others add: one JSON file each
LEARN_FOLDERS = (('lessons', LESSONS_FOLDER), ('examples', EXAMPLES_FOLDER),
                 ('pythonista_lessons', PYTHONISTA_LESSONS_FOLDER))
EXAMPLES_WHERE = 'Toolbox/examples'     # the folder line on an example's card
START_ZOOM = 0.9             # the page's first size; a pinch is remembered
LESSON_COLOUR = '#F5C26B'    # a lesson card's edge (examples take Files' colour for .py)
STEP_LINES = 8               # steps listed on a lesson's card before it cuts
RESTORE_ARM_SECONDS = 5      # Restore asks Sure?; a second tap within this restores
ABOUT_ICON = 'ℹ️'
# Toolbox's own lesson packs, in Learn's order; pack files in PACKS_FOLDER follow.
BUILT_IN_PACKS = (
    {'name': 'editorkit', 'emoji': '🎓', 'folder': LESSONS_FOLDER, 'built_in': True,
     'about': 'Script Pythonista itself: windows over your code, cards, the editor, '
              'your own tools.'},
    {'name': 'Pythonista', 'emoji': '🐍', 'folder': PYTHONISTA_LESSONS_FOLDER, 'built_in': True,
     'about': "Pythonista's own modules, a step at a time: ui, scene and dialogs."},
)
DEFAULT_PACK_EMOJI = '📚'
EMPTY_PACK = 'No lessons in %s yet.'
EXAMPLE_GROUPS = (('tool', 'Finished tools · use them, copy them'),
                  ('window', 'Windows'),
                  ('editor', 'The editor'),
                  ('theme', 'Themes'),
                  ('other', 'More examples'))
HOW_IT_WORKS = 'Tap a lesson, then ▶ to run it: it walks you through its own code.'
MISSING = 'Nothing here yet: run the Toolbox installer again to put the %s in Documents/Toolbox.'

ABOUT = '''🧰 Toolbox

Tools that live inside Pythonista's editor: a hub to open them, and windows over your code for files, finding, moving lines, snippets, running code, explaining names, reading the docs and installing packages from PyPI.

Toolbox is built on editorkit, a Python library for scripting Pythonista itself. Your own scripts can use it to open windows over the editor, put notes and highlights beside your code, add your own keys and toolbar buttons, read and change the open script, and work with tabs, files and themes.

🎓 Learn has the lessons and examples. A lesson walks you through its own code, step by step, while you watch it work. Start with Lesson 1, then build your own tools. Change them as much as you like: ♻️ Restore in Learn puts them back.

Everything lives in Documents/Toolbox. Run the installer again any time to update: your snippets and settings are kept.'''


# --- Reading lessons and examples (pure) -------------------------------------

def script_facts(source):
    """(headline, summary, steps) for a lesson or example: the module
    docstring's first paragraph, its second, and the titles of its
    @lesson.step(...) functions in order. Reads the code; never runs it.
    Code that does not parse gives ('', '', [])."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return '', '', []
    doc = ast.get_docstring(tree) or ''
    paragraphs = [' '.join(part.split()) for part in doc.split('\n\n') if part.strip()]
    headline = paragraphs[0] if paragraphs else ''
    summary = paragraphs[1] if len(paragraphs) > 1 else ''
    steps = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == 'step' and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                    and isinstance(decorator.args[0].value, str)):
                steps.append(decorator.args[0].value)
    return headline, summary, steps


def scripts(folder):
    """[(path, headline, summary, steps)] for the scripts in folder, by name."""
    found = []
    if not os.path.isdir(folder):
        return found
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.py') or name.startswith(('_', '.')):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, encoding='utf-8') as handle:
                source = handle.read()
        except OSError:
            continue
        found.append((path,) + script_facts(source))
    return found


def readable_name(path):
    return os.path.splitext(os.path.basename(path))[0].replace('_', ' ')


def lesson_title(path, headline):
    """'Lesson 1: Windows.' -> 'Lesson 1 · Windows'; no headline: the file name."""
    number, _, name = headline.rstrip('.').partition(': ')
    if name:
        return '%s · %s' % (number, name)
    return headline.rstrip('.') or readable_name(path)


def example_group(path):
    """The group an example's card goes under: the first word of its name
    (tool_finder.py -> 'tool'), or 'other'."""
    prefix = os.path.basename(path).split('_', 1)[0]
    return prefix if prefix in dict(EXAMPLE_GROUPS) else 'other'


# --- Restore (pure planning; restore() does the file work) -------------------

def restore_plan(originals, folders=LEARN_FOLDERS):
    """[(original, installed)] for every lesson or example file that is
    missing or differs from its untouched copy under originals. Files you
    added yourself have no original, so they are never in the plan."""
    plan = []
    for name, folder in folders:
        source = os.path.join(originals, name)
        if not os.path.isdir(source):
            continue
        for entry in sorted(os.listdir(source)):
            original = os.path.join(source, entry)
            if entry.startswith('.') or not os.path.isfile(original):
                continue
            installed = os.path.join(folder, entry)
            if not os.path.exists(installed) or not filecmp.cmp(original, installed, shallow=False):
                plan.append((original, installed))
    return plan


def restore(plan):
    """Carry out a restore_plan: a changed file is moved to Documents/_to_delete
    first (fileops.trash), then the original is copied in. A file that cannot
    be moved aside is left as it is. Returns (restored, left alone)."""
    restored = left = 0
    for original, installed in plan:
        try:
            if os.path.exists(installed):
                fileops.trash(installed, DOCUMENTS)
            os.makedirs(os.path.dirname(installed), exist_ok=True)
            shutil.copy2(original, installed)
            restored += 1
        except Exception:
            left += 1
    return restored, left


# --- The page (pure) ----------------------------------------------------------


def pack_from_file(path):
    """A lesson pack from its JSON file ({"name", "folder", "emoji",
    "about"}; folder relative to Documents or absolute). A file that cannot
    be read is a pack with an 'error' and no folder, so Learn can say so."""
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding='utf-8') as handle:
            spec = json.load(handle)
        folder = str(spec['folder'])
    except Exception as problem:
        return {'name': name, 'emoji': '⚠️', 'folder': None, 'about': '',
                'error': '%s could not load: %s' % (os.path.basename(path), problem)}
    if not os.path.isabs(folder):
        folder = os.path.join(DOCUMENTS, folder)
    return {'name': str(spec.get('name', name)), 'emoji': str(spec.get('emoji', DEFAULT_PACK_EMOJI)),
            'folder': folder, 'about': str(spec.get('about', ''))}


def lesson_packs(packs_folder=PACKS_FOLDER, built_in=BUILT_IN_PACKS):
    """Toolbox's own packs, then one per JSON file in packs_folder, by file name."""
    packs = [dict(pack) for pack in built_in]
    try:
        names = sorted(os.listdir(packs_folder))
    except OSError:
        names = []
    packs.extend(pack_from_file(os.path.join(packs_folder, name))
                 for name in names if name.endswith('.json'))
    return packs


def pack_key(pack):
    """The chip key that shows one pack."""
    return 'pack:' + pack['name']


def view_item(path):
    """📜's item on a card: the hub's own (the script in a script window)."""
    return search.ViewHit(search.Hit(path, 1, 0, 0))


def lesson_card(path, headline, summary, steps, emoji='🎓'):
    """A lesson as a card in Files' style: its steps numbered where a file
    card shows its first lines, edged in the lesson colour. emoji is its
    pack's."""
    where = '%s %d steps · ▶ runs it' % (emoji, len(steps)) if steps else '%s lesson' % emoji
    body = '<div class="fx-where">%s</div>' % html.escape(where)
    listed = '\n'.join('%d  %s' % (number, step) for number, step in enumerate(steps, 1))
    body += card_kit.code(listed or summary, lines=STEP_LINES, python=False)
    return card_kit.Card(lesson_title(path, headline), item=('open', path), body=body,
                         colour=LESSON_COLOUR,
                         actions=[card_kit.Action(filecards.WINDOW_ICON, view_item(path))])


def example_card(path, headline, summary, steps):
    """An example as Files shows a file: name, folder, first lines, 📜."""
    return filecards.file_card(path, ('open', path), view_item(path), where=EXAMPLES_WHERE)


def restore_row(page, changed, armed):
    """♻️ at the top: nothing when there are no originals (changed None),
    a quiet note when all is as installed, else the button (Sure? when armed)."""
    if changed is None:
        return
    if not changed:
        page.note('♻️ Every lesson and example is as installed.')
        return
    if armed:
        label = 'Sure? Restore %d · your versions go to _to_delete' % changed
    else:
        label = '♻️ Restore lessons and examples · %d changed' % changed
    page.buttons([card_kit.Action(label, ('restore',), armed=armed)])


def learn_page(packs, examples, showing='all', changed=None, armed=False, message=''):
    """The Learn page: chips (All, one per lesson pack, Examples), any
    message, ♻️ Restore, then each pack's lessons in order and the examples
    by group. packs is [(pack, lessons)] (lesson_packs, scripts)."""
    page = card_kit.Page()
    chips = [('all', 'All', sum(len(lessons) for _pack, lessons in packs) + len(examples))]
    chips.extend((pack_key(pack), '%s %s' % (pack['emoji'], pack['name']), len(lessons))
                 for pack, lessons in packs)
    chips.append(('examples', 'Examples', len(examples)))
    page.chips([card_kit.Chip('%s%s · %d' % ('✓ ' if key == showing else '', label, count),
                              item=('show', key))
                for key, label, count in chips])
    if message:
        page.note(message)
    shown = [(pack, lessons) for pack, lessons in packs
             if showing in ('all', 'lessons', pack_key(pack))]
    if shown:
        restore_row(page, changed, armed)
        page.note(HOW_IT_WORKS)
    for pack, lessons in shown:
        page.heading('%s %s · in order' % (pack['emoji'], pack['name']))
        if pack.get('error'):
            page.note(pack['error'])
            continue
        if pack.get('about'):
            page.note(pack['about'])
        if lessons:
            page.grid([lesson_card(*entry, emoji=pack['emoji']) for entry in lessons],
                      min_width=filecards.CARD_WIDTH)
        elif pack.get('built_in'):
            page.note(MISSING % 'lessons')
        else:
            page.note(EMPTY_PACK % pack['folder'])
    if showing in ('all', 'examples'):
        if not examples:
            page.heading('Examples')
            page.note(MISSING % 'examples')
        for key, title in EXAMPLE_GROUPS:
            group = [entry for entry in examples if example_group(entry[0]) == key]
            if group:
                page.heading(title)
                page.grid([example_card(*entry) for entry in group],
                          min_width=filecards.CARD_WIDTH)
    return page


# --- The tool -----------------------------------------------------------------

class LearnTool:

    def __init__(self, window):
        self.window = window
        self.showing = 'all'
        self.armed_until = 0.0       # Restore's Sure? lasts until then
        self.message = ''            # what the last restore did
        self.cards = web_tiles.Cards(window, on_pick=self.picked, zoom=START_ZOOM,
                                     zoom_key='learn', extra_css=filecards.CSS)
        self.about = web_tiles.Card(window, on_close=self.close_about)
        window.add_page(TITLE, self.cards)
        window.add_button(ABOUT_ICON, self.show_about, name='about')
        self.refresh()

    def refresh(self):
        """Read the folders again: lessons and examples may have changed."""
        changed = None
        if os.path.isdir(ORIGINALS_FOLDER):
            changed = len(restore_plan(ORIGINALS_FOLDER))
        packs = [(pack, scripts(pack['folder']) if pack.get('folder') else [])
                 for pack in lesson_packs()]
        self.cards.show(learn_page(packs, scripts(EXAMPLES_FOLDER),
                                   self.showing, changed, time.time() < self.armed_until,
                                   self.message))

    def picked(self, item):
        if isinstance(item, search.ViewHit):          # 📜: a script window
            from . import scriptview
            self.window.minimise()
            scriptview.open_script_window(item.hit.path, item.hit.line)
            return
        kind = item[0]
        if kind == 'open':
            self.window.minimise()           # out of the way of the script it opens
            ek.open_file(item[1])
        elif kind == 'show':
            self.showing = item[1]
            self.message = ''
            self.refresh()
        elif kind == 'restore':
            self.restore_tapped()

    def restore_tapped(self):
        """First tap: Sure? Second tap within RESTORE_ARM_SECONDS: restore."""
        if time.time() >= self.armed_until:
            self.armed_until = time.time() + RESTORE_ARM_SECONDS
            self.refresh()
            return
        self.armed_until = 0.0
        restored, left = restore(restore_plan(ORIGINALS_FOLDER))
        self.message = 'Restored %d file%s.' % (restored, '' if restored == 1 else 's')
        if left:
            self.message += ' %d could not be moved aside, so were left as they are.' % left
        self.refresh()

    def show_about(self, *ignored):
        self.about.set_text(ABOUT)
        self.window.show_sheet(self.about)

    def close_about(self, *ignored):
        if self.window.sheet is self.about:
            self.window.close_sheet()


def open_learn():
    """Open Learn over the code (or bring it back)."""
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    tool = LearnTool(window)
    window.learn_tool = tool
    window.on('open', lambda _window: tool.refresh())
    window.show()
    return tool
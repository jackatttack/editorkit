"""Toolbox's tools, in the order the hub's Tools page shows them.

Each tool is a dict: name, emoji, what (a few words: its card's caption),
home (where it opens, said in its help card), about (the help-mode card)
and open (a function that opens it). A group is a tool with 'group':
[tools] instead of open; its card opens the group's own page in the hub
(Games). every_tool() lists them all, groups opened out.

Your own tools join the hub through plugin files (plugin_tools): one JSON
file each in Documents/Toolbox/tools/. Files in Documents/Toolbox/games/
work the same way and land in the Games group.
"""
import importlib
import json
import os
import sys
import traceback

from . import find
from . import hub_layout


# --- Plugin folders -----------------------------------------------------------

DOCUMENTS = os.path.expanduser('~/Documents')
TOOLS_FOLDER = os.path.join(DOCUMENTS, 'Toolbox', 'tools')
GAMES_FOLDER = os.path.join(DOCUMENTS, 'Toolbox', 'games')

# (folder, group its tools join, function called when a file names none)
PLUGIN_FOLDERS = (
    (TOOLS_FOLDER, None, 'main'),
    (GAMES_FOLDER, 'Games', 'open_game'),
)

# How a group's card looks. A group not listed here gets the default emoji.
GROUP_CARDS = {
    'Games': {'emoji': '🎮', 'home': 'games',
              'about': 'Games played over the code, added by other projects. '
                       'Tap to see them.'},
}
DEFAULT_GROUP_EMOJI = '🗂'


# --- Toolbox's own tools ------------------------------------------------------

def open_learn():
    from . import learn
    learn.open_learn()


def open_packages():
    from . import packages_tool
    packages_tool.open_packages()


def open_scissors():
    """The Scissors pad in the keyboard's place."""
    from . import scissors_pad
    return scissors_pad.open_scissors_pad()


def open_explain():
    from . import explain
    return explain.open_explain()


def open_snippets():
    # Imported on first use, so the hub still opens if Snippets cannot load.
    from . import snippets
    return snippets.open_snippets()


def open_search():
    """Searching across files is the hub's Find."""
    from . import hub
    return hub.open_find()


def open_files():
    from . import filebrowser
    return filebrowser.open_files()


def open_console():
    from . import console
    return console.open_console()


def open_script():
    from . import scriptview
    return scriptview.open_script_window()


def open_quick():
    from . import quick
    return quick.open_quick()


def open_find():
    return find.open_find()


def open_web():
    from . import web_tool
    return web_tool.open_web()


def open_tidy():
    import editorkit as ek
    return ek.tidy()


def open_scratch():
    from . import scratch_tool
    return scratch_tool.open_scratch()


BUILT_IN = [
    {'name': 'Learn', 'emoji': '🎓', 'what': 'lessons and examples',
     'home': 'over the code', 'open': open_learn,
     'about': 'The lessons and examples that come with Toolbox. A lesson walks you '
              'through its own code: open it, tap ▶ to run it, and its window explains '
              'each step while the editor shows that step\'s code. Examples are small '
              'scripts, one idea each. Start here to build your own tools with editorkit.'},
    {'name': 'Files', 'emoji': '📁', 'what': 'browse and preview',
     'home': 'over the code', 'open': open_files,
     'about': 'Folders and files as tiles. Tap a folder to go in, a chip in the '
              'path to go back. Tap a file to preview it in the keyboard\'s place '
              '(as a script window: ▶ ✂️ ⚡ and line taps), again or ↗ to open it. '
              '🔍 searches the folder you are in, by name and code.'},
    {'name': 'Find in script', 'emoji': '🔍', 'what': 'in the open script',
     'home': 'at the top of the code', 'open': open_find,
     'about': 'Find in the open script: a slim bar over the code, matches marked '
              'in the editor, ◀ ▶ or Return to step. ⇄ shows Replace. To look '
              'through other files, ⤢ carries the term over to the hub\'s Find.'},
    {'name': 'Scissors', 'emoji': '✂️', 'what': 'select and move code',
     'home': 'in the keyboard\'s place (a small window on an iPad)', 'open': open_scissors,
     'about': 'Select code fast and act on it. ◀ ▶ hop between words, ▲ ▼ to the word '
              'above or below. ⊕ grows the selection: the word, the whole line, then '
              'one more line a tap; ⊖ walks it back; ⟲ goes back to one word. Once '
              'whole lines are selected the arrows change: ⇧ ⇩ move the lines, ⇤ ⇥ '
              'indent. Hold an arrow or ⊕ to repeat. 📋 copy, ✂️ cut, 📥 paste (lines '
              're-indented to fit), ▶ run in the Console, ? Explain the selection; ⋯ for '
              'duplicate, comment, snippet and the script window. Undo covers every edit.'},
    {'name': 'Script', 'emoji': '📜', 'what': 'a script as a window',
     'home': 'over the code', 'open': open_script,
     'about': 'The open script in its own window, as code: tap a line to open it '
              'there, ▶ runs it in the Console, ✂️ brings Scissors for it, ⚡ '
              'Quick. One window per script; several can wait in the tray.'},
    {'name': 'Snippets', 'emoji': '🧩', 'what': 'saved code to type',
     'home': 'over the code', 'open': open_snippets,
     'about': 'Saved code as cards: tap one to type it at the cursor, ✏️ to edit '
              'it in the text box, 🗑 twice to delete. Groups along the top; '
              '＋ Snippet starts from your selection. ${cursor}, ${date}, ${time} '
              'and ${clipboard} are filled in when typed.'},
    {'name': 'Packages', 'emoji': '📦', 'what': 'install from PyPI',
     'home': 'over the code', 'open': open_packages,
     'about': 'Find, inspect, install and remove Python packages from PyPI. Inspect shows '
              'every package it would install before anything changes; downloads are '
              'checked and verified, and nothing runs setup.py. Toolbox only removes '
              'what it installed. Pure-Python packages work best.'},
    {'name': 'Console', 'emoji': '📟', 'what': 'run and see output',
     'home': 'over the code', 'open': open_console,
     'about': 'Run the open script, or only the selected lines, and watch its '
              'output stream in as cards. Tap a traceback line to open the file '
              'there. ■ stops a run, ⌫ clears.'},
    {'name': 'Scratch', 'emoji': '🧪', 'what': 'throwaway Python pads',
     'home': 'over the code', 'open': open_scratch,
     'about': 'Throwaway Python, kept out of your projects: every pad lives in '
              'scratch/pads. ＋ New pad makes one and opens it; on a pad, ▶ runs it in '
              'the Console, 📌 keeps it, 🗑 twice deletes it. 🧹 Clean deletes every pad '
              'not kept, and old scratch_pad.py files anywhere in Documents, after a '
              'second tap. Auto-clean deletes old pads each time Scratch opens.'},
    {'name': 'Quick', 'emoji': '⚡', 'what': 'one-tap script actions',
     'home': 'over the code', 'open': open_quick,
     'about': 'One-tap actions on the open script: copy, run, duplicate, '
              'constants, clipboard and more. ? in its header explains each.'},
    {'name': 'Explain', 'emoji': '❓', 'what': 'what is this? and the docs',
     'home': 'over the code', 'open': open_explain,
     'about': 'Put the cursor on a name, or select some code: Explain says what it is, '
              'as cards. A Python object shows its signature, docs and members (tap one '
              'to go into it, ◀ to come back) with Insert and Insert call; your own names '
              'show where this file defines and uses them (tap to jump); inside a call, '
              'tap a parameter to insert name=. Select a class to see its methods. Type '
              'a name in the field to explain that instead. On no name, it says what '
              'the line is. Its 📖 Docs tab searches and reads Pythonista\'s own '
              'documentation (view, add_subview, os.path); the field searches there.'},
    {'name': 'Web', 'emoji': '🌐', 'what': 'browse the web',
     'home': 'over the code', 'open': open_web,
     'about': 'A browser over your code. Type an address, or words to search, in the '
              'field at the top. ◀ goes back (or swipe from the left edge), ↻ reloads, '
              '↗ opens the page in Safari, ⧉ copies its link. Packages opens PyPI '
              'pages here too.'},

]


# --- Plugins: tools other scripts add -------------------------------------------

def plugin_path(folder):
    """A plugin's folder: absolute, or relative to Documents (so one file
    works on every device)."""
    return folder if os.path.isabs(folder) else os.path.join(DOCUMENTS, folder)


def import_fresh(module_name, folder=None):
    """Import module_name fresh, so an edited plugin shows at once. With a
    folder, that folder goes first on sys.path."""
    if folder:
        path = plugin_path(folder)
        if not os.path.isdir(path):
            raise RuntimeError('%s is not there' % path)
        if path not in sys.path:
            sys.path.insert(0, path)
    root = module_name.split('.')[0]
    for loaded in [name for name in sys.modules if name.split('.')[0] == root]:
        del sys.modules[loaded]
    return importlib.import_module(module_name)


def plugin_tool(spec, group, default_function):
    """One tool from a plugin file: name, module, and optionally folder,
    function (called with args when the tool opens), emoji, what, about,
    home and group."""
    function_name = spec.get('function', default_function)
    arguments = list(spec.get('args', []))

    def open_it():
        module = import_fresh(spec['module'], spec.get('folder'))
        return getattr(module, function_name)(*arguments)

    return {'name': spec['name'], 'emoji': spec.get('emoji', '🧰'),
            'what': spec.get('what', 'tool'), 'home': spec.get('home', 'over the code'),
            'about': spec.get('about', ''), 'open': open_it,
            'in_group': spec.get('group', group)}


def provided_tools(spec, group):
    """Several tools from one plugin file: its module's `tools` function
    returns tool dicts (with open), each optionally naming a group."""
    module = import_fresh(spec['module'], spec.get('folder'))
    found = []
    for tool in getattr(module, spec['tools'])():
        tool = dict(tool)
        named_group = tool.pop('group', None)
        tool['in_group'] = named_group if isinstance(named_group, str) else group
        tool.setdefault('emoji', '🧰')
        tool.setdefault('what', 'tool')
        tool.setdefault('home', 'over the code')
        tool.setdefault('about', '')
        found.append(tool)
    return found


def plugin_tools():
    """Every tool the plugin folders add. A file that fails is reported and
    skipped: the hub must open either way."""
    found = []
    for folder, group, default_function in PLUGIN_FOLDERS:
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if not name.endswith('.json'):
                continue
            try:
                with open(os.path.join(folder, name), encoding='utf-8') as handle:
                    spec = json.load(handle)
                if 'tools' in spec:
                    found.extend(provided_tools(spec, group))
                else:
                    found.append(plugin_tool(spec, group, default_function))
            except Exception:                # the hub shows it as a dimmed card instead
                found.append(broken_plugin(name, folder))
    return found


def broken_plugin(file_name, folder):
    """A stand-in card for a plugin file that failed to load: the hub shows
    it dimmed with "could not load", and its help card names the error.
    Call it inside the except block (it reads the exception being handled)."""
    error = traceback.format_exception_only(*sys.exc_info()[:2])[-1].strip()
    return {'name': '⚠ ' + file_name, 'emoji': '⚠️', 'what': 'could not load',
            'home': 'nowhere', 'open': None, 'broken': True,
            'about': 'Toolbox could not load the plugin file %s (in %s). Fix the file, '
                     'then open the hub again.\n\n%s' % (file_name, folder, error)}


def with_plugins(built_in, plugins, moves=None):
    """Toolbox's tools, then plugin tools, then one card per group.

    moves ({tool name: group}, your hub settings: hub_layout) puts any
    tool, Toolbox's own too, into a group; '' brings a plugin's tool out of
    its group onto the home view."""
    moves = moves or {}
    loose, groups = [], {}
    for tool in list(built_in) + list(plugins):
        group = moves[tool['name']] if tool['name'] in moves else tool.get('in_group')
        if group:
            groups.setdefault(group, []).append(dict(tool, in_group=group))
        else:
            loose.append(dict(tool, in_group=None) if tool.get('in_group') else tool)
    cards = []
    for name, members in groups.items():
        look = GROUP_CARDS.get(name, {})
        cards.append({'name': name, 'emoji': look.get('emoji', DEFAULT_GROUP_EMOJI),
                      'home': look.get('home', 'tools'), 'group': members, 'open': None,
                      'about': look.get('about', '%s: tools gathered in one card. '
                                                 'Tap to see them.' % name)})
    return loose + cards


def load():
    """Build the tool list afresh: BUILT_IN plus whatever the plugin folders
    hold now. The hub calls it each time it opens, so a plugin file added
    since Pythonista started shows without a restart. Returns the list, also
    kept as TOOLS."""
    global TOOLS
    TOOLS = with_plugins(BUILT_IN, plugin_tools(), hub_layout.load()['groups'])
    return TOOLS


TOOLS = load()


def every_tool():
    """Every tool, with groups opened out (the hub's Find lists these)."""
    found = []
    for tool in TOOLS:
        found.extend(tool['group'] if 'group' in tool else [tool])
    return found
"""The deck's tools, in the order the hub's Tools page shows them.

Each tool: name, emoji, what (a few words on what it is for: its card's
caption), home (where it opens: said in its help card), about (the
help-mode card) and open (a function that opens it, or None while it is
still to be built; its tile then shows as 'soon'). A group is a tool with
'group': [tools] instead of open: its card opens the group's own page in
the hub (Games). every_tool() lists them all, groups opened out.
"""
import importlib.util

from . import find


def shipped(module):
    """True when this copy of the app has the module. The public release
    leaves some tools out (tools/stage_release.py LEFT_OUT); their cards go
    with them (OPTIONAL_TOOLS below)."""
    return importlib.util.find_spec('%s.%s' % (__package__, module)) is not None


def open_scissors():
    """The Scissors bar over the top of the code (the keyboard version is
    still a script window's ✂️ keys, until it is retired)."""
    from . import scissors_bar
    return scissors_bar.open_scissors_bar()


def open_lens():
    from . import lens
    return lens.open_lens()


def open_docs():
    from . import docs
    return docs.open_docs()


def open_snippets():
    # Imported on first use, so the hub still opens if the snippet keyboard's
    # core (projects/keyboard/snippets) is missing.
    from . import snippets
    return snippets.open_snippets()


def open_search():
    """Searching across files is the hub's Find now."""
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


def open_calc():
    from . import calc
    return calc.open_calc()


def open_snake():
    from . import snake
    return snake.open_snake()


def open_find():
    return find.open_find()


def open_tidy():
    import editorkit as ek
    return ek.tidy()


def maths_game_tool(game):
    """One Maths Games game (native) as a tool for the Games group."""

    def open_it(game_id=game.game_id):
        from . import mathsgames
        return mathsgames.open_game(game_id)

    return {'name': game.title, 'emoji': game.icon, 'what': 'Maths Games',
            'home': 'over the code', 'open': open_it, 'about': game.tagline}


def maths_games_tools():
    """Maths Games (a separate project, hosted in place) as tools, or []
    when it is not on this device. The hub must open either way."""
    try:
        from . import mathsgames_source
        return [maths_game_tool(game) for game in mathsgames_source.games()]
    except Exception:
        import traceback
        traceback.print_exc()
        return []


GAMES = [
    {'name': 'Snake', 'emoji': '🐍', 'what': 'a demo over your code',
     'home': 'over the code', 'open': open_snake,
     'about': 'A demo: Snake played over your own code. The pad sits in the '
              'keyboard\'s place (⌨ brings it back); the game pauses while it '
              'is away. The edges wrap; do not bite yourself.'},
]
if shipped('mathsgames_source'):
    from . import mathsgames_source
    GAMES.extend(maths_games_tools())
    GAMES.extend(mathsgames_source.web_port_tools())




TOOLS = [
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

    {'name': 'Scissors', 'emoji': '✂️', 'what': 'cut, copy, move lines',
     'home': 'at the top of the code', 'open': open_scissors,
     'about': 'A range of lines at the top of the code: type the first and last '
              'lines, or select by hand and they follow. ⌂ the cursor\'s line, ▣ '
              'the block around it (again to widen), ⤓ one more line. Then copy, '
              'cut, ⧉ duplicate, ↑ ↓ move past the neighbours, ⇥ ⇤ indent, # '
              'comment, 🧩 save as a snippet, ▶ run in the Console. The lines stay '
              'selected, so press again to carry on. No range: the cursor\'s line.'},
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
    {'name': 'Console', 'emoji': '📟', 'what': 'run and see output',
     'home': 'over the code', 'open': open_console,
     'about': 'Run the open script, or only the selected lines, and watch its '
              'output stream in as cards. Tap a traceback line to open the file '
              'there. ■ stops a run, ⌫ clears.'},
    {'name': 'Quick', 'emoji': '⚡', 'what': 'one-tap script actions',
     'home': 'over the code', 'open': open_quick,
     'about': 'One-tap actions on the open script: copy, run, duplicate, '
              'constants, clipboard and more. ? in its header explains each.'},
    {'name': 'Calc', 'emoji': '🧮', 'what': 'sums, algebra, calculus',
     'home': 'in the keyboard\'s place', 'open': open_calc,
     'about': 'A calculator in the keyboard\'s place, with MATH behind it. 123 '
              'for arithmetic, f(x) for functions and solve, factor, expand, '
              'd/dx, ∫, simplify. ↶ takes the last answer back; tap the tape to '
              'reuse; sel and ↧ code work with the script.'},
    {'name': 'Games', 'emoji': '🎮', 'home': 'games', 'group': GAMES, 'open': None,
     'about': 'Games played over the code: Maths Games, their web ports beside '
              'them for comparison, and Snake. Tap to see them.'},
    {'name': 'Lens', 'emoji': '🔬', 'what': 'tune the value here',
     'home': 'at the top of the code', 'open': open_lens,
     'about': 'A look at what is under the cursor, and a control that fits it. '
              'On a number: steps of its last digit (0.35 steps by 0.01) and a '
              'slider. On a colour (\'#E8365A\', (0.2, 0.4, 1.0) or (255, 128, 0)): '
              'a swatch and R G B sliders. Values are written the way they were, '
              'and one slider drag is one undo. More lenses to come.'},
    {'name': 'Docs', 'emoji': '📖', 'what': "Pythonista's documentation",
     'home': 'over the code', 'open': open_docs,
     'about': 'Pythonista\'s own documentation, searched and read over the code. '
              'Type a name (view, add_subview, os.path) and tap a result to open '
              'its page at that entry; links inside pages work. ☰ goes back to the '
              'results. Pages come out of the app\'s docs as you open them.'},
]

# Tools a copy of the app may leave out, by the module each one needs. The
# public release leaves these out, and their cards go with them.
OPTIONAL_TOOLS = {'Calc': 'calc', 'Games': 'snake'}
TOOLS = [tool for tool in TOOLS
         if tool['name'] not in OPTIONAL_TOOLS or shipped(OPTIONAL_TOOLS[tool['name']])]


def every_tool():
    """Every tool, with groups opened out (the hub's Find lists these)."""
    found = []
    for tool in TOOLS:
        found.extend(tool['group'] if 'group' in tool else [tool])
    return found
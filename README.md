# editorkit

**Lessons that run over their own code.** Open a lesson in Pythonista and a
window appears over the editor. Each step explains itself, selects its own
code so you can see it, and runs when you tap ▶ Try it. Ten lessons take you
from a first window to a tool of your own in Toolbox's hub.

<!-- GIF here: a lesson stepping through its own code (media/lesson.gif) -->

It comes as two things:

- **Toolbox**, an app that lives over Pythonista's editor: files, search,
  snippets, packages, a console, docs and more, each a tap away.
- **editorkit**, the library Toolbox is built with: windows over the
  editor, pages of cards, and the editor itself (text, selections,
  highlights, themes). The lessons teach it.

Early days: this is still being tested, and things will change.

## Install

Make a new script in Pythonista, paste this in and run it:

    import urllib.request
    url = ('https://raw.githubusercontent.com/'
           'jackatttack/editorkit/main/install.py')
    source = urllib.request.urlopen(url).read()
    exec(compile(source, 'install.py', 'exec'), {'__name__': '__main__'})

Run the same script again any time to update. Your snippets and settings
are kept, and so are your edits to the lessons and examples: an update
moves your version into `Documents/_to_delete` before the new one lands.

The installer:

- puts two packages in `site-packages-3`: `editorkit` (the library) and
  `editorkit_toolbox` (the app),
- makes `Documents/Toolbox/` with the Toolbox launcher, the uninstaller,
  the lessons and the examples,
- adds **Toolbox** to the editor's wrench menu.

## Uninstall

Run `Documents/Toolbox/Uninstall.py`. It takes Toolbox out of the wrench
menu and moves both packages and `Documents/Toolbox` into
`Documents/_to_delete`; nothing is deleted. Your saved data stays in
`Documents/.editorkit` unless you set `MOVE_SAVED_DATA = True` at the top
of the script. Packages you installed with 📦 Packages stay where they are.

## Toolbox

Tap the wrench, then **Toolbox**. The 🏡 hub opens over your code.

| | Tool | What it does |
|---|---|---|
| 🎓 | Learn | The lessons, in order, and the examples. Start here. |
| 📁 | Files | Folders and files as cards; tap a file to preview it. |
| 🔍 | Find in script | A slim bar for the open script, with Replace. |
| ✂️ | Scissors | A pad in the keyboard's place: select words and lines fast, then move, indent, copy, cut, paste, run or explain them. |
| 📜 | Script | A script in its own window: tap a line to go there. |
| 🧩 | Snippets | Saved code to type at the cursor; over a hundred to start. |
| 📦 | Packages | Install pure-Python packages from PyPI. |
| 📟 | Console | Run the script, or just the selection, and see its output. |
| ⚡ | Quick | One-tap actions on the open script. |
| ❓ | Explain | What is the name or line under the cursor? Signature, docs, uses. Its 📖 Docs tab searches Pythonista's own documentation. |

**Searching.** The hub's Find is the one search across files: it finds
file names and code under a folder, in sections. Find in script is the
quick bar for the file you are in; its ⤢ carries your search over to the
hub's Find, and Files' 🔍 opens the hub's Find in the folder you are in.

**Packages** shows every package it would install before anything
changes. Each download's SHA-256 is checked against the one PyPI
publishes (a package without one is refused), and nothing runs `setup.py`.
Toolbox removes only what it installed; anything installed another way
(Pipista, StaSh, by hand) shows read-only. Its engine comes from Pipista,
my package manager for Pythonista, but it keeps its own records in
`Documents/.editorkit/packages`.

### Add your own tool to the hub

A tool joins the hub through a plugin file: one JSON file in
`Documents/Toolbox/tools/`. Lesson 10 ends by writing one.

    {
      "name": "TODOs",
      "emoji": "✅",
      "what": "in the open script",
      "folder": "Toolbox/examples",
      "module": "tool_todos",
      "function": "main",
      "about": "Every TODO comment in the open script."
    }

`folder` is relative to Documents (or absolute) and goes on `sys.path`;
the hub imports `module` fresh and calls `function` when the tool's card
is tapped. Add `"group": "Games"` to put it in a group. One file can give
several tools: name a function with `"tools"` that returns a list of tool
dicts (`name`, `emoji`, `what`, `about`, `open`). Files in
`Documents/Toolbox/games/` land in the Games group.

## Build with editorkit

    import editorkit as ek

    ek.show('Hello from a window over your code')

    window = ek.Window('Notes', emoji='📝')
    window.add_page('Today', 'Finish the lesson.')
    window.add_page('HTML', '<h2>Hello</h2>')
    window.show()

    ek.annotate(12, 'Look here', style='note')
    ek.select(*ek.line_range(12, 14))

A page can be text, HTML, an image, a matplotlib figure, any `ui.View`,
or a page of cards, whose taps hand back your own items:

    from editorkit.web import cards

    page = cards.Page()
    page.grid([cards.Card('Red', item='#ff5a5f'), cards.Card('Teal', item='#5fd3bc')])
    ek.show(page, title='Colours', on_pick=print)

A tool's window outlives its script, so end a tool with `ek.run_tool(main)`:
its callbacks can then use the script's names after Pythonista clears them.
The finished tools in `Documents/Toolbox/examples` (`tool_*.py`) all do.

The lessons, in order: Windows · Cards · The editor · Edit the code · Work
in the background · Tabs and files · The keyboard's place · The feed · Part
of Pythonista · Build a tool.

### Words editorkit uses

- **Window**: a panel over the code (`ek.Window`). Its header holds ✕ – ＋
  and your buttons; its pages become tabs.
- **Pin**: a folded window, a small chip at the screen's edge. Tap it to
  bring the window back. (`ek.pin_view` is different: it pins a view of
  yours beside a line of code.)
- **Tray**: where folded windows wait while a home window runs (Toolbox's
  🏡 hub shows them as chips).
- **Dock**: the keyboard's place. One window at a time can sit there.
- **Home**: where a window opens: over the code, `'top_bar'`,
  `'above_dock'` or `'dock'`.
- **Owner and pieces**: `Window(owner=app)` makes a window one of an
  app's pieces. It folds into the owner's box (a row of chips under its
  header) and closes with it.
- **Sheet**: a view laid over a window's page (`show_sheet`).
  **Accessory**: a strip under the page tabs, shared by every page.
- **Pair**: a view over the code joined to its keys in the dock (`ek.Pair`).
- **Tiles**: the web pieces pages are built from (`editorkit.web.tiles`:
  Cards, Code, Feed, Tape). **Native** pieces (`editorkit.native`) are for
  text entry and fast motion.
- **Cards**: a `cards.Page` of headings, notes, chips, buttons and cards.
- **Lesson**: a script that teaches by running its own steps
  (`editorkit.lessons`).

## Good to know

- Made for Pythonista 3.4 (Python 3.10). Tested on iPhone with iOS 27.2.
  It runs on iPad too, where some window sizes are still being tuned.
- editorkit reaches Pythonista's own (private) classes through
  `objc_util`. That is what makes it possible, and it means a Pythonista
  update could break something. If one does, please open an issue.
- It writes only to `site-packages-3`, `Documents/Toolbox` and
  `Documents/.editorkit`. Anything it replaces or removes goes to
  `Documents/_to_delete`, never straight to deletion.

## Licence

MIT. See LICENSE.
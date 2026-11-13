# editorkit

Tools that work over Pythonista's own editor, and the library they are
built on.

Early days: this is still being tested, and things will change.

## Install

Make a new script in Pythonista, paste this in and run it:

    import urllib.request
    url = ('https://raw.githubusercontent.com/'
           'jackatttack/editorkit/main/install.py')
    source = urllib.request.urlopen(url).read()
    exec(compile(source, 'install.py', 'exec'), {'__name__': '__main__'})

Run the same script again any time to update. Your snippets and settings
are kept.

The installer:

- puts three packages in `site-packages-3`: `editorkit` (the library),
  `editorkit_toolbox` (the app) and `codesense` (the code analysis behind
  Lens),
- makes `Documents/Toolbox/` with the Toolbox launcher, the examples and
  the lessons,
- adds **Toolbox** to the editor's wrench menu.

## Use it: Toolbox for Pythonista

Tap the wrench, then **Toolbox**. The hub opens over your code with Files,
Find, Scissors, Script, Snippets, Console, Quick, Lens and Docs.

## Build with it: editorkit

editorkit gives you windows over Pythonista's editor, keyboard and console,
pages built from cards, and the editor itself: text, selections, highlights
and themes.

Start with the lessons in `Toolbox/lessons/`, in order, then the small
scripts in `Toolbox/examples/`: one idea each.

## Licence

MIT. See LICENSE.
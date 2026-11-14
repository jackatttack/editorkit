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
  Explain),
- makes `Documents/Toolbox/` with the Toolbox launcher, the examples and
  the lessons,
- adds **Toolbox** to the editor's wrench menu.

## Use it: Toolbox for Pythonista

Tap the wrench, then **Toolbox**. The hub opens over your code with Learn,
Files, Find, Scissors, Script, Snippets, Packages, Console, Quick, Docs and
Explain. 📦 Packages installs pure-Python packages from PyPI, showing every
dependency before anything changes (its engine comes from Pipista). ℹ️ About on the hub says what everything is.

Snippets comes with a library of over a hundred: Pythonista's own modules,
editorkit, everyday Python, web and data, maths and plots, and whole-file
templates. 📄 opens a scratch pad beside your script to try them in.

## Build with it: editorkit

editorkit gives you windows over Pythonista's editor, keyboard and console,
pages built from cards, and the editor itself: text, selections, highlights
and themes.

Open 🎓 **Learn** in Toolbox. Nine lessons, in order, each walk you through
their own code while it runs, then the examples, starting with finished
tools to use and copy. Change them freely: ♻️ Restore in Learn puts them
back, and updating keeps your versions in `Documents/_to_delete`.

## Licence

MIT. See LICENSE.
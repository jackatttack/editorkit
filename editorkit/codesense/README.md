# codesense

Pure-Python code analysis for **Coil**, the overlay for Pythonista's editor.
It turns text plus a caret or selection into a `Context`, keeps a symbol
index of the file, and (next) runs jedi and pyflakes in the background.

No UI and no Pythonista imports: it runs headless, in Forge tests and in
PythonIDE. Never import `editorkit`, `objc_util`, `editor` or `ui` here.

## Use

    import codesense

    ledger = codesense.Ledger()
    index = codesense.build_index(text, ledger=ledger)
    context = codesense.context_at(text, caret, index=index, ledger=ledger)
    print(context.kind, context.text, context.details, context.scope)
    print('\n'.join(ledger.report()))

Positions are UTF-16 units, the same as Pythonista's editor.

## Tiers

- **0, every keystroke:** `context_at` reads the current line with
  `tokenize`. Kinds: nothing, number, name, attribute, call, def, import,
  string, comment, lines, text. Budget under 1 ms.
- **1, after a pause:** `build_index` parses the file with `ast`: symbols,
  scopes, Python's visibility rules. Cached by a hash of the text; a file
  that does not parse keeps the last good index, marked stale. Budget
  under 60 ms.
- **2, on request (next):** jedi 0.9 completions, definitions and
  signatures, and pyflakes, off the main thread with a time budget.

## Files

- `units.py`: UTF-16 and Python positions, lines
- `context.py`: tier 0
- `index.py`: tier 1
- `timing.py`: the ledger
- `tests/smoke_codesense.py`: headless checks and budgets (Forge RUN)


"""codesense: pure-Python code analysis for the Coil editor overlay.

No UI and no Pythonista imports, so it runs headless, in Forge tests and in
PythonIDE. Positions in and out are UTF-16 units (the editor's), converted
at the edges by units.py.

Tier 0  context_at(text, start, end=None, index=None, ledger=None) -> Context
        what the caret or selection is on; reads one line; under 1 ms
Tier 1  build_index(text, previous=None, ledger=None) -> SymbolIndex
        names, scopes and visibility for the file; cached; under 60 ms
        suggestions(context, index) -> [Suggestion], instant, from the index
Tier 2  Assistant: jedi completions, signatures and definitions, and
        pyflakes lint, on one background thread with versioned answers
Timing  Ledger: every step records its last, worst, mean and median time

See projects/editorkit/docs/DESIGN.txt, sections 5, 7 and 8.
"""
from .assist import Answer, Assistant
from .context import KINDS, Context, context_at
from .index import Symbol, SymbolIndex, build_index
from .suggest import Suggestion, suggestions
from .timing import Ledger

__version__ = '0.2.0'
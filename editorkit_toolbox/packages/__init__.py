"""The package engine behind 📦 Packages, vendored from Pipista (MIT, the
same author): engine (inspect, stage, verify, install, uninstall, recover),
dependencies (a read-only plan, then an install that rolls back on failure),
pypi (PyPI's name index), environment (what is already importable) and
catalog (a short list of packages tested on Pythonista).

Standard library only; dependencies uses the packaging module when it is
there and its own fallback when it is not. One addition in engine, marked
there: inspection falls back to the newest release this Python supports
(_newest_supported). Otherwise copied unchanged from
Documents/Pipista/pipista_core, less Pipista's own interface (frontend,
app_base) and GitHub projects (github). Toolbox passes its own state folder,
so its records are separate from Pipista's.
"""
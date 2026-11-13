"""Lookup: what Python can say about a name without running your code.

Explain's helpers (they lived in Lens until it was retired, 2026-11-13).

    reachable('os.path')               the object, or None when reaching it
                                       would mean importing one of your scripts
    describe(owner, 'join', 'member')  one line about owner.join
    short_signature(function)          '(a, b=1)', cut to DESCRIPTION_LENGTH
"""
import importlib
import importlib.util
import inspect
import sys


# --- Settings -------------------------------------------------------------

DESCRIPTION_LENGTH = 80      # a docstring line or signature is cut here
VALUE_LENGTH = 60            # a value's repr is cut here


def first_doc_line(thing):
    doc = inspect.getdoc(thing) or ''
    for line in doc.splitlines():
        if line.strip():
            return line.strip()[:DESCRIPTION_LENGTH]
    return ''


def reachable(base):
    """The object a dotted base names ('sys', 'os.path', 'ui.Button'), when
    Python can reach it without running your own code: a module already
    loaded, or one importable from outside Documents (the standard library,
    Pythonista's modules, site-packages). None otherwise."""
    if not base:
        return None
    parts = base.split('.')
    found = sys.modules.get(parts[0])
    if found is None:
        try:
            spec = importlib.util.find_spec(parts[0])
        except Exception:
            return None
        origin = (getattr(spec, 'origin', None) or '') if spec is not None else ''
        if spec is None or ('/Documents/' in origin and 'site-packages' not in origin):
            return None              # one of your scripts: importing it would run it
        try:
            found = importlib.import_module(parts[0])
        except Exception:
            return None
    for part in parts[1:]:
        try:
            found = getattr(found, part)
        except Exception:
            return None
    return found


def short_signature(member):
    """'(hook, /)' when a member has no docstring (builtins on device often
    do not), cut like a description; '' when there is none."""
    try:
        text = str(inspect.signature(member))
    except (TypeError, ValueError):
        return ''
    return text if len(text) <= DESCRIPTION_LENGTH else text[:DESCRIPTION_LENGTH - 1] + '…'


def describe(owner, name, kind):
    """One line about owner.name: a docstring's first line for functions,
    classes and modules, a short repr for values, else the kind."""
    if owner is None:
        return kind
    try:
        member = getattr(owner, name)
    except Exception:
        return kind
    if callable(member) or inspect.ismodule(member):
        return first_doc_line(member) or short_signature(member) or kind
    text = repr(member)
    return text if len(text) <= VALUE_LENGTH else text[:VALUE_LENGTH - 1] + '…'
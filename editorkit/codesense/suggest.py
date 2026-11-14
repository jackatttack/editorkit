"""Instant suggestions from the symbol index, for the strip while jedi
(tier 2, assist.py) thinks.

    suggestions(context, index, limit=12) -> [Suggestion]

Names: what is in scope, nearest first, then builtins, then keywords.
After 'self.': the enclosing class's methods, attributes and class variables.
Exact-case prefix matches come before case-insensitive ones; the word being
typed never suggests itself. Other attribute bases (os.path.) are left to
jedi.
"""
import builtins
import keyword

BUILTIN_NAMES = sorted(name for name in dir(builtins) if not name.startswith('_'))


class Suggestion(object):
    """One thing the strip could insert.

    kind    symbol kind (function, method, variable, ...), or builtin,
            keyword, or jedi's own type name
    detail  a readable summary, such as a signature
    source  index, builtins, keywords or jedi
    """
    __slots__ = ('name', 'kind', 'detail', 'source')

    def __init__(self, name, kind='', detail='', source=''):
        self.name = name
        self.kind = kind
        self.detail = detail
        self.source = source

    def __repr__(self):
        return 'Suggestion(%s, %s, %s)' % (self.name, self.kind, self.source)


def suggestions(context, index, limit=12):
    prefix = context.prefix
    if context.kind == 'attribute':
        if context.details.get('base') == 'self' and index is not None:
            return _matching(_class_members(index, context.scope), prefix, context.text, limit)
        return []
    if context.kind not in ('name', 'nothing', 'call') or not prefix:
        return []
    found = []
    if index is not None:
        for symbol in index.visible_from(context.line):
            found.append(Suggestion(symbol.name, symbol.kind, symbol.detail, 'index'))
    found.extend(Suggestion(name, 'builtin', '', 'builtins') for name in BUILTIN_NAMES)
    found.extend(Suggestion(word, 'keyword', '', 'keywords') for word in keyword.kwlist)
    return _matching(found, prefix, context.text, limit)


def _class_members(index, scope):
    """Methods, self attributes and class variables of the innermost class
    around scope."""
    for depth in range(len(scope), 0, -1):
        path = scope[:depth]
        if index.scope_kinds.get(path) == 'class':
            return [Suggestion(symbol.name, symbol.kind, symbol.detail, 'index')
                    for symbol in index.symbols if symbol.scope == path]
    return []


def _matching(candidates, prefix, typed, limit):
    """Exact-case prefix matches, then case-insensitive ones; one per name;
    never the word being typed."""
    seen = set([typed]) if typed else set()
    exact, loose = [], []
    lowered = prefix.lower()
    for candidate in candidates:
        name = candidate.name
        if name in seen:
            continue
        if name.startswith(prefix):
            exact.append(candidate)
            seen.add(name)
        elif name.lower().startswith(lowered):
            loose.append(candidate)
            seen.add(name)
    return (exact + loose)[:limit]
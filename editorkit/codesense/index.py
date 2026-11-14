"""Tier 1: a symbol index of one file, rebuilt after a pause.

    build_index(text, previous=None, ledger=None) -> SymbolIndex

Cached by a hash of the text: the same text returns the same index. A file
that does not parse keeps the last good index, marked stale, with the
error. Budget: under 60 ms (measured 7 ms on 530 lines, 53 ms on 4000).
"""
import ast
import gc
import hashlib

from .timing import maybe_timed


class Symbol(object):
    """A name the file defines.

    kind    class, function, method, argument, variable, attribute (self.x,
            filed under its class) or import
    line    1-based line of the definition
    scope   enclosing def and class names, outermost first
    detail  a readable summary: 'def place(self, origin)', 'from math import sqrt'
    """
    __slots__ = ('name', 'kind', 'line', 'scope', 'detail')

    def __init__(self, name, kind, line, scope, detail=''):
        self.name = name
        self.kind = kind
        self.line = line
        self.scope = scope
        self.detail = detail

    def __repr__(self):
        where = ' in ' + '.'.join(self.scope) if self.scope else ''
        return 'Symbol(%s %s, line %d%s)' % (self.kind, self.name, self.line, where)


class SymbolIndex(object):
    def __init__(self, text_hash=None):
        self.text_hash = text_hash
        self.failed_hash = None
        self.symbols = []
        self.scopes = []          # (path, kind, first line, last line)
        self.scope_kinds = {}     # path -> 'class' or 'function'
        self.strings = []         # (first line, last line) of multi-line strings
        self.error = None
        self.stale = False
        self.line_count = 0

    def enclosing(self, line):
        """The innermost scope path holding line; () at module level."""
        best = ()
        for path, kind, first, last in self.scopes:
            if first <= line <= last and len(path) > len(best):
                best = path
        return best

    def in_string(self, line):
        """True when line is inside a multi-line string (a docstring, or a
        string assigned directly), between its first and last lines."""
        for first, last in self.strings:
            if first < line < last:
                return True
        return False

    def defined(self, name):
        return [symbol for symbol in self.symbols if symbol.name == name]

    def visible_from(self, line):
        """Names visible at line, nearest first: the innermost scope, then
        outwards to module level. A class body's names are skipped inside
        its methods, as in Python. One entry per name."""
        path = self.enclosing(line)
        found, seen = [], set()
        for depth in range(len(path), -1, -1):
            chain = path[:depth]
            if depth and depth != len(path) and self.scope_kinds.get(chain) == 'class':
                continue
            here = sorted((symbol for symbol in self.symbols if symbol.scope == chain),
                          key=lambda symbol: abs(symbol.line - line))
            for symbol in here:
                if symbol.name not in seen:
                    seen.add(symbol.name)
                    found.append(symbol)
        return found

    def summary(self):
        state = ' (stale: %s)' % self.error if self.stale else ''
        return '%d symbols in %d scopes, %d lines%s' % (
            len(self.symbols), len(self.scopes), self.line_count, state)


def text_hash(text):
    return hashlib.md5(text.encode('utf-8', 'surrogatepass')).hexdigest()


def build_index(text, previous=None, ledger=None):
    digest = text_hash(text)
    if previous is not None and digest in (previous.text_hash, previous.failed_hash):
        return previous
    with maybe_timed(ledger, 'build_index'):
        # Parsing makes thousands of small objects; a cycle collection in the
        # middle can double the time. Pause it for the build, then restore.
        collecting = gc.isenabled()
        gc.disable()
        try:
            with maybe_timed(ledger, 'parse'):
                try:
                    tree = ast.parse(text)
                except (SyntaxError, ValueError) as error:
                    tree = None
                    message = '%s (line %s)' % (getattr(error, 'msg', error),
                                                getattr(error, 'lineno', '?'))
            if tree is None:
                kept = previous if previous is not None else SymbolIndex()
                kept.stale = True
                kept.error = message
                kept.failed_hash = digest
                return kept
            index = SymbolIndex(digest)
            index.line_count = text.count('\n') + 1
            with maybe_timed(ledger, 'collect'):
                _Collector(index).visit(tree)
            return index
        finally:
            if collecting:
                gc.enable()


# ---- Walking the tree -------------------------------------------------------

def _all_arguments(arguments):
    found = list(getattr(arguments, 'posonlyargs', [])) + list(arguments.args)
    if arguments.vararg is not None:
        found.append(arguments.vararg)
    found.extend(arguments.kwonlyargs)
    if arguments.kwarg is not None:
        found.append(arguments.kwarg)
    return found


def _signature(arguments):
    parts = [argument.arg for argument in
             list(getattr(arguments, 'posonlyargs', [])) + list(arguments.args)]
    if arguments.vararg is not None:
        parts.append('*' + arguments.vararg.arg)
    elif arguments.kwonlyargs:
        parts.append('*')
    parts.extend(argument.arg for argument in arguments.kwonlyargs)
    if arguments.kwarg is not None:
        parts.append('**' + arguments.kwarg.arg)
    return ', '.join(parts)


class _Collector(object):
    """Walks statements only. Names are defined by statements (assignment,
    loop, with and except targets, defs, imports), so expression trees are
    never visited. That keeps the index fast on big files: a NodeVisitor
    over every node cost 136 ms on 4000 lines (2026-11-07).
    Not indexed: walrus targets and comprehension variables."""

    def __init__(self, index):
        self.index = index
        self.path = ()
        self.kinds = []
        self.handlers = {
            ast.Assign: self.assign,
            ast.AugAssign: self.single_target,
            ast.AnnAssign: self.single_target,
            ast.For: self.loop,
            ast.AsyncFor: self.loop,
            ast.While: self.branches,
            ast.If: self.branches,
            ast.With: self.with_block,
            ast.AsyncWith: self.with_block,
            ast.Try: self.try_block,
            ast.FunctionDef: self.function,
            ast.AsyncFunctionDef: self.function,
            ast.ClassDef: self.class_block,
            ast.Import: self.import_names,
            ast.ImportFrom: self.import_from,
            ast.Expr: self.expression_statement,
        }
        try_star = getattr(ast, 'TryStar', None)
        if try_star is not None:
            self.handlers[try_star] = self.try_block
        match = getattr(ast, 'Match', None)
        if match is not None:
            self.handlers[match] = self.match_block

    # ---- Walking ----

    def visit(self, tree):
        self.statements(tree.body)

    def statements(self, body):
        handlers = self.handlers
        for node in body:
            handler = handlers.get(type(node))
            if handler is not None:
                handler(node)

    def add(self, name, kind, node, detail='', scope=None):
        self.index.symbols.append(Symbol(
            name, kind, getattr(node, 'lineno', 0),
            self.path if scope is None else scope, detail))

    def enter(self, node, kind, arguments=None):
        path = self.path + (node.name,)
        last = getattr(node, 'end_lineno', None) or node.lineno
        self.index.scopes.append((path, kind, node.lineno, last))
        self.index.scope_kinds[path] = kind
        saved = self.path
        self.path = path
        self.kinds.append(kind)
        if arguments is not None:
            for argument in _all_arguments(arguments):
                self.add(argument.arg, 'argument', argument)
        self.statements(node.body)
        self.kinds.pop()
        self.path = saved

    # ---- Statements that define names ----

    def class_block(self, node):
        self.add(node.name, 'class', node, 'class %s' % node.name)
        self.enter(node, 'class')

    def function(self, node):
        kind = 'method' if self.kinds and self.kinds[-1] == 'class' else 'function'
        self.add(node.name, kind, node, 'def %s(%s)' % (node.name, _signature(node.args)))
        self.enter(node, 'function', node.args)

    def assign(self, node):
        for target in node.targets:
            self.target(target)
        self.note_string(node.value)

    def expression_statement(self, node):
        """Bare strings: docstrings and string blocks."""
        self.note_string(node.value)

    def note_string(self, value):
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            last = getattr(value, 'end_lineno', None)
            if last is not None and last > value.lineno:
                self.index.strings.append((value.lineno, last))

    def single_target(self, node):
        self.target(node.target)

    def loop(self, node):
        self.target(node.target)
        self.statements(node.body)
        self.statements(node.orelse)

    def branches(self, node):
        self.statements(node.body)
        self.statements(node.orelse)

    def with_block(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                self.target(item.optional_vars)
        self.statements(node.body)

    def try_block(self, node):
        self.statements(node.body)
        for handler in node.handlers:
            if handler.name:
                self.add(handler.name, 'variable', handler)
            self.statements(handler.body)
        self.statements(node.orelse)
        self.statements(node.finalbody)

    def match_block(self, node):
        for case in node.cases:
            self.statements(case.body)

    def import_names(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.add(name, 'import', node, 'import %s' % alias.name)

    def import_from(self, node):
        module = '.' * node.level + (node.module or '')
        for alias in node.names:
            self.add(alias.asname or alias.name, 'import', node,
                     'from %s import %s' % (module, alias.name))

    # ---- Targets ----

    def target(self, node):
        if isinstance(node, ast.Name):
            self.add(node.id, 'variable', node)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                self.target(element)
        elif isinstance(node, ast.Starred):
            self.target(node.value)
        elif (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == 'self'):
            for depth in range(len(self.kinds) - 1, -1, -1):
                if self.kinds[depth] == 'class':
                    self.add(node.attr, 'attribute', node, 'self.' + node.attr,
                             scope=self.path[:depth + 1])
                    break
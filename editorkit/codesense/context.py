"""Tier 0: what is the caret, or the selection, on?

Runs on every keystroke, so it reads only the current line, with tokenize.
Budget: under 1 ms. A string or bracket that spans lines is only partly
visible from one line; the symbol index (tier 1) covers the whole file.

    context_at(text, start, end=None, index=None, ledger=None) -> Context

start and end are editor positions (UTF-16). With end, the selection is
classified; without, the caret. With an index, the context's scope is
filled in.
"""
import ast
import io
import keyword
import tokenize

from . import units
from .timing import maybe_timed

KINDS = ('nothing', 'number', 'name', 'attribute', 'call', 'def', 'import',
         'string', 'comment', 'lines', 'text')

SKIPPED_TOKENS = (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER,
                  tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT)
WORD_TOKENS = (tokenize.NAME, tokenize.NUMBER, tokenize.STRING)


class Context(object):
    """What the caret or selection is on.

    kind     one of KINDS
    text     the token, the selected text, or a call's function name
    span     (start, end) UTF-16 positions of text
    line     1-based line, or (first, last) for kind 'lines'
    prefix   the part of a name before the caret (completions use it)
    details  extras by kind: number value, attribute base, call function
             and argument index, import modules, inside_call for names
    scope    enclosing def and class names, outermost first (needs an index)
    """

    def __init__(self, kind, text='', span=(0, 0), line=1, prefix='', details=None, scope=()):
        self.kind = kind
        self.text = text
        self.span = span
        self.line = line
        self.prefix = prefix
        self.details = details or {}
        self.scope = scope

    def __repr__(self):
        extras = ', %r' % self.details if self.details else ''
        return 'Context(%s, %r, line %s%s)' % (self.kind, self.text, self.line, extras)


def context_at(text, start, end=None, index=None, ledger=None):
    with maybe_timed(ledger, 'context_at'):
        if end is not None and end != start:
            context = _selection_context(text, min(start, end), max(start, end))
        else:
            context = _caret_context(text, start, index)
        if index is not None:
            first = context.line[0] if isinstance(context.line, tuple) else context.line
            context.scope = index.enclosing(first)
        return context


# ---- The caret --------------------------------------------------------------

def _caret_context(text, position, index=None):
    caret = units.to_python(text, position)
    line_start, line_end = units.line_bounds(text, caret)
    line_text = text[line_start:line_end]
    column = caret - line_start
    line = units.line_number(text, caret)
    line_start_utf16 = position - units.utf16_length(line_text[:column])

    def span(first, last):
        return (line_start_utf16 + units.utf16_length(line_text[:first]),
                line_start_utf16 + units.utf16_length(line_text[:last]))

    if index is not None and index.in_string(line):
        # Inside a multi-line string the index knows about; one line alone
        # cannot tell.
        return Context('string', line_text, span(0, len(line_text)), line,
                       details={'closed': False, 'multiline': True})
    state, state_start = _scan(line_text, column)
    if state == 'comment':
        return Context('comment', line_text[state_start:],
                       span(state_start, len(line_text)), line)
    if state == 'string':
        return Context('string', line_text[state_start:column],
                       span(state_start, column), line, details={'closed': False})

    tokens = _line_tokens(line_text)
    call = _enclosing_call(tokens, column)
    found = _token_at(tokens, column)
    if found is not None:
        token = tokens[found]
        first, last = token.start[1], token.end[1]
        if token.type == tokenize.NUMBER:
            return Context('number', token.string, span(first, last), line,
                           details={'value': _literal(token.string)})
        if token.type == tokenize.STRING:
            return Context('string', token.string, span(first, last), line,
                           details={'closed': True, 'value': _literal(token.string)})
        if token.type == tokenize.NAME:
            return _name_context(tokens, found, column, line, span, line_text, call)
        if token.type == tokenize.OP and token.string == '.' and last == column:
            return Context('attribute', '', (position, position), line, '',
                           {'base': _chain_before(tokens, found), 'name': ''})
    if call is not None:
        return Context('call', call[0], (position, position), line,
                       details={'function': call[0], 'argument': call[1]})
    return Context('nothing', '', (position, position), line)


def _name_context(tokens, found, column, line, span, line_text, call):
    token = tokens[found]
    word = token.string
    first, last = token.start[1], token.end[1]
    prefix = word[:column - first]
    before = tokens[found - 1].string if found > 0 else None
    after = tokens[found + 1].string if found + 1 < len(tokens) else None
    if tokens[0].string in ('import', 'from'):
        return Context('import', word, span(first, last), line, prefix,
                       {'statement': line_text.strip(), 'modules': _imported_modules(line_text)})
    if word in ('def', 'class') or before in ('def', 'class'):
        named = tokens[found + 1] if word in ('def', 'class') and after else token
        what = 'class' if 'class' in (word, before) else 'def'
        return Context('def', named.string, span(named.start[1], named.end[1]), line,
                       details={'what': what, 'name': named.string})
    if keyword.iskeyword(word):
        return Context('nothing', word, span(first, last), line, details={'keyword': word})
    details = {'name': word}
    if call is not None:
        details['inside_call'] = call
    if before == '.':
        details['base'] = _chain_before(tokens, found - 1)
        return Context('attribute', word, span(first, last), line, prefix, details)
    details['called'] = after == '('
    return Context('name', word, span(first, last), line, prefix, details)


# ---- A selection ------------------------------------------------------------

def _selection_context(text, start, end):
    python_start, python_end = units.to_python(text, start), units.to_python(text, end)
    selected = text[python_start:python_end]
    first = units.line_number(text, python_start)
    last = units.line_number(text, max(python_start, python_end - 1))
    if last > first:
        return Context('lines', selected, (start, end), (first, last),
                       details={'count': last - first + 1})
    tokens = _line_tokens(selected.strip())
    if len(tokens) == 1:
        token = tokens[0]
        if token.type == tokenize.NUMBER:
            return Context('number', selected, (start, end), first,
                           details={'value': _literal(token.string)})
        if token.type == tokenize.NAME and not keyword.iskeyword(token.string):
            return Context('name', selected, (start, end), first,
                           details={'name': token.string})
        if token.type == tokenize.STRING:
            return Context('string', selected, (start, end), first,
                           details={'closed': True, 'value': _literal(token.string)})
    return Context('text', selected, (start, end), first)


# ---- Helpers ----------------------------------------------------------------

def _scan(line_text, column):
    """('code', None), ('string', where it opened) or ('comment', where the
    # is) for the line up to column."""
    quote, opened, position = None, None, 0
    while position < column:
        character = line_text[position]
        if quote:
            if character == '\\':
                position += 2
                continue
            if line_text.startswith(quote, position):
                position += len(quote)
                quote = None
                continue
        else:
            if character == '#':
                return 'comment', position
            if character in '"\'':
                triple = line_text[position:position + 3]
                quote = triple if triple in ('"""', "'''") else character
                opened = position
                position += len(quote)
                continue
        position += 1
    return ('string', opened) if quote else ('code', None)


def _line_tokens(line_text):
    """Tokens of one line. A line that does not tokenize alone (a bracket
    closed on a later line) still gives the tokens before the problem."""
    tokens = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(line_text + '\n').readline):
            if token.type not in SKIPPED_TOKENS:
                tokens.append(token)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return tokens


def _token_at(tokens, column):
    """Index of the token the caret touches, preferring words over operators."""
    fallback = None
    for position, token in enumerate(tokens):
        if token.start[1] <= column <= token.end[1]:
            if token.type in WORD_TOKENS:
                return position
            if fallback is None:
                fallback = position
    return fallback


def _chain_before(tokens, dot):
    """The dotted name before the '.' at tokens[dot]: 'os.path' in os.path.x"""
    parts = []
    position = dot - 1
    while position >= 0 and tokens[position].type == tokenize.NAME:
        parts.insert(0, tokens[position].string)
        if position >= 1 and tokens[position - 1].string == '.':
            position -= 2
        else:
            break
    return '.'.join(parts)


def _chain_ending(tokens, position):
    """The dotted name ending at the NAME at tokens[position]."""
    parts = [tokens[position].string]
    position -= 1
    while position >= 1 and tokens[position].string == '.' and tokens[position - 1].type == tokenize.NAME:
        parts.insert(0, tokens[position - 1].string)
        position -= 2
    return '.'.join(parts)


def _enclosing_call(tokens, column):
    """(function, argument index) of the innermost call the caret is inside,
    or None."""
    stack = []
    for position, token in enumerate(tokens):
        if token.start[1] >= column:
            break
        if token.type != tokenize.OP:
            continue
        if token.string in ('(', '[', '{'):
            function = None
            if (token.string == '(' and position > 0
                    and tokens[position - 1].type == tokenize.NAME
                    and not keyword.iskeyword(tokens[position - 1].string)):
                function = _chain_ending(tokens, position - 1)
            stack.append([function, 0])
        elif token.string in (')', ']', '}'):
            if stack:
                stack.pop()
        elif token.string == ',' and stack:
            stack[-1][1] += 1
    for function, commas in reversed(stack):
        if function:
            return (function, commas)
    return None


def _imported_modules(line_text):
    try:
        tree = ast.parse(line_text.strip())
    except SyntaxError:
        return []
    node = tree.body[0] if tree.body else None
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return ['.' * node.level + (node.module or '')]
    return []


def _literal(source):
    try:
        return ast.literal_eval(source)
    except (ValueError, SyntaxError):
        return None
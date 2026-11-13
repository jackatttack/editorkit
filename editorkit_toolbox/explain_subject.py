"""What ❓ Explain is looking at, and the plain-text helpers its facets use.

    subject_at(text, start, end)   the Subject under the cursor or selection
    dotted_at(text, index)         'ui.Button' with the cursor on Button
    definitions(text, name)        where this file defines name
    usages(text, name, limit)      where this file uses name
    outline(source)                classes, methods and functions in some code
    names_in(source)               the dotted names used, first seen first

Indices are Python string indices (the editor's ek.selection). No UI and no
editor: tests/smoke_explain_subject.py runs it headless.
"""
import ast
import collections
import html as html_module
import builtins
import io
import tokenize
import keyword
import posixpath
import re
import textwrap

try:
    import codesense
    from codesense import units
except ImportError:                  # without codesense, kinds come from the text alone
    codesense = None

# kind: codesense's context kind, or 'colour', 'lines', 'name', 'text'
# text, start, end: what it covers (Python indices)
# line: 1-based line, 0 for a name typed or tapped rather than read from code
# dotted: the name to explain ('' if none); value: a number's or colour's value
# details: codesense's context details
Subject = collections.namedtuple('Subject', 'kind text start end line dotted value details')

NAMES_SHOWN = 12
DOTTED = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
NO_NAME_KINDS = ('string', 'comment', 'number')


def line_bounds(text, index):
    """(start, end) of the line holding index, without its newline."""
    start = text.rfind('\n', 0, index) + 1
    end = text.find('\n', index)
    return start, (len(text) if end == -1 else end)


def line_of(text, index):
    return text.count('\n', 0, index) + 1


def line_start(text, line):
    """Where 1-based line starts (the end of the text past the last line)."""
    index = 0
    for _ in range(max(0, line - 1)):
        found = text.find('\n', index)
        if found == -1:
            return len(text)
        index = found + 1
    return index


def dotted_at(text, index):
    """(name, (start, end)): the dotted name touching index, up to the part
    the cursor is on ('ui.Button' on Button in ui.Button.title). ('', (index,
    index)) when the cursor touches no name, or touches a keyword."""
    start, end = line_bounds(text, index)
    line = text[start:end]
    column = index - start
    for match in DOTTED.finditer(line):
        if match.start() <= column <= match.end():
            if match.start() > 0 and line[match.start() - 1].isdigit():
                break                              # 1e5, 0x1F: part of a number
            stop = line.find('.', column, match.end())
            stop = match.end() if stop == -1 else stop
            name = line[match.start():stop]
            if keyword.iskeyword(name.rsplit('.', 1)[-1]):
                break
            return name, (start + match.start(), start + stop)
    return '', (index, index)


def subject_at(text, start, end=None):
    """The Subject at the cursor (start) or in the selection (start to end)."""
    end = start if end is None else end
    start, end = min(start, end), max(start, end)
    line = line_of(text, start)
    if end > start:
        selected = text[start:end]
        if '\n' in selected.strip('\n'):
            return Subject('lines', selected, start, end, line, '', None, {})
        name = selected.strip()
        if DOTTED.fullmatch(name) and not keyword.iskeyword(name):
            offset = selected.index(name)
            return Subject('name', name, start + offset, start + offset + len(name), line,
                           name, None, {})
        return Subject('text', selected, start, end, line, '', None, {})
    context = None
    if codesense is not None:
        try:
            context = codesense.context_at(text, units.to_utf16(text, start))
        except Exception:
            context = None
    kind = context.kind if context is not None else 'nothing'
    details = dict(context.details) if context is not None else {}
    name, (name_start, name_end) = dotted_at(text, start)
    if kind in NO_NAME_KINDS:
        name = ''
    if name:
        if kind in ('nothing', 'text', 'lines'):
            kind = 'name'
        return Subject(kind, text[name_start:name_end], name_start, name_end, line, name,
                       None, details)
    word = context.text if context is not None and context.text else ''
    if kind == 'call' and word:
        return Subject('call', word, start, start, line, word, None, details)
    return Subject(kind, word, start, start, line, '', None, details)


def matching_lines(text, pattern, limit=None):
    """([(line number, index, line)], total) for the lines pattern finds. The
    index is where the pattern's last matched group starts (the name)."""
    found, total, offset = [], 0, 0
    for number, line in enumerate(text.split('\n'), 1):
        match = pattern.search(line)
        if match:
            total += 1
            if limit is None or len(found) < limit:
                found.append((number, offset + match.start(match.lastindex or 0), line))
        offset += len(line) + 1
    return found, total


def definitions(text, name):
    """[(line number, index, line)] where this file defines name: def, class,
    or an assignment at the start of a line."""
    word = re.escape(name)
    pattern = re.compile(r'^\s*(?:async\s+)?(?:def|class)\s+(%s)\b|^\s*(%s)\s*(?::[^=]*)?=(?!=)'
                         % (word, word))
    return matching_lines(text, pattern)[0]


def usages(text, name, limit=12):
    """([(line number, index, line)], total) for the lines that use name."""
    return matching_lines(text, re.compile(r'\b(%s)\b' % re.escape(name)), limit)


def _doc_line(node):
    doc = ast.get_docstring(node) or ''
    return doc.strip().split('\n', 1)[0] if doc.strip() else ''


def _arguments(node):
    try:
        return '(%s)' % ast.unparse(node.args)
    except Exception:
        return '(…)'


def _bases(node):
    try:
        return '(%s)' % ', '.join(ast.unparse(base) for base in node.bases) if node.bases else ''
    except Exception:
        return ''


def outline(source):
    """[(kind, name, signature, first doc line, line)] for the classes, their
    methods and the functions in source (lines are 1-based within source).
    [] when source does not parse."""
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []
    found = []
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            found.append(('class', node.name, _bases(node), _doc_line(node), node.lineno))
            for child in node.body:
                if isinstance(child, functions):
                    found.append(('method', '%s.%s' % (node.name, child.name), _arguments(child),
                                  _doc_line(child), child.lineno))
        elif isinstance(node, functions):
            found.append(('function', node.name, _arguments(node), _doc_line(node), node.lineno))
    return found


def names_in(source, limit=NAMES_SHOWN):
    """The dotted names in source, first seen first, keywords left out."""
    seen = []
    for match in DOTTED.finditer(source):
        name = match.group(0)
        if keyword.iskeyword(name.split('.', 1)[0]) or name in seen:
            continue
        seen.append(name)
        if len(seen) >= limit:
            break
    return seen


def block_at(text, line, limit=60):
    """The code that starts at 1-based line (a def, a class, an assignment):
    that line and every line indented under it, dedented, at most limit lines."""
    lines = text.split('\n')
    if not 1 <= line <= len(lines):
        return ''
    first = lines[line - 1]
    indent = len(first) - len(first.lstrip())
    block = [first]
    for following in lines[line:line - 1 + limit]:
        if following.strip() and len(following) - len(following.lstrip()) <= indent:
            break
        block.append(following)
    while block and not block[-1].strip():
        block.pop()
    return textwrap.dedent('\n'.join(block))


def resolve_link(href, current_page, entry_names):
    """Where a docs link goes, as an Explain item: ('explain', name) for an
    entry the docs index knows, ('page', page, anchor) for a part of a docs
    page, None for the web (left as text). Paths are relative to current_page."""
    if not href or href.startswith(('http:', 'https:', 'mailto:', 'ftp:')):
        return None
    path, _, anchor = href.partition('#')
    if anchor and anchor in entry_names:
        return ('explain', anchor)
    if path:
        page = posixpath.normpath(posixpath.join(posixpath.dirname(current_page), path))
    else:
        page = current_page
    return ('page', page, anchor)


def split_arguments(inside, optional_brackets=False):
    """'a, b=(1, 2), *args' -> ['a', 'b=(1, 2)', '*args']: commas at the top
    level only (not inside brackets or quotes). optional_brackets: the docs'
    notation, where [ ] around arguments means optional (range([start, ]stop)):
    those brackets are dropped, while brackets in a default value still nest."""
    parts, depth, quote, current = [], 0, None, []
    for character in inside:
        if quote:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if optional_brackets and character in '[]' and '=' not in ''.join(current):
            continue
        if character in '\'"':
            quote = character
        elif character in '([{':
            depth += 1
        elif character in ')]}':
            depth -= 1
        elif character == ',' and depth <= 0:
            parts.append(''.join(current).strip())
            current = []
            continue
        current.append(character)
    if ''.join(current).strip():
        parts.append(''.join(current).strip())
    return parts


def signature_inputs(signature_text):
    """[(name, default or None)] from a signature written as text, such as
    the docs' 'os.path.dirname(path)' or 'range([start, ]stop[, step])'.
    The bare / and * markers are left out."""
    text = signature_text.strip()
    if '(' not in text or ')' not in text:
        return []
    inside = text[text.index('(') + 1:text.rindex(')')]
    found = []
    for part in split_arguments(inside, optional_brackets=True):
        part = part.strip().strip('[]').strip()
        if not part or part in ('/', '*', '...'):
            continue
        name, _, default = part.partition('=')
        found.append((name.strip(), default.strip() or None))
    return found


PRE = re.compile(r'<pre\b[^>]*>(.*?)</pre>', re.DOTALL | re.IGNORECASE)


def code_blocks(fragment):
    """The code in each <pre> block of some docs HTML, as plain text."""
    return [html_module.unescape(re.sub(r'<[^>]+>', '', block)).strip('\n')
            for block in PRE.findall(fragment)]


def insertable(example):
    """An example as code to type: doctest prompts (>>> and ...) taken off
    and their output lines left out; anything else as it is."""
    lines = example.split('\n')
    if not any(line.startswith('>>>') for line in lines):
        return example
    kept = []
    for line in lines:
        if line.startswith(('>>> ', '... ')):
            kept.append(line[4:])
        elif line in ('>>>', '...'):
            kept.append('')
    return '\n'.join(kept)


# --- Names worth a chip ----------------------------------------------------
# Explain's name chips only offer names a tap can explain. Words in strings,
# comments and docstrings, and plain variables, had pages with nothing on.

BUILTIN_NAMES = frozenset(name for name in dir(builtins) if not name.startswith('_'))
IMPORT_LINE = re.compile(r'^\s*import\s+([^#]+)')
FROM_LINE = re.compile(r'^\s*from\s+[\w.]+\s+import\s+\(?([^)#]+)')
DEFINE_LINE = re.compile(r'^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)')


def code_names(source):
    """[(line, dotted)] for every dotted name in the code itself, in order.
    Strings, comments and docstrings are left out, attribute chains stay
    whole (os.path.join), and a chain hanging off a call or a subscript
    (f().x, rows[0].y) is left out. Half-typed code: names up to where it
    stops tokenizing."""
    found = []
    chain, line, loose = [], 0, False
    previous = ''

    def flush():
        if chain and not loose:
            found.append((line, '.'.join(chain)))

    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            kind, text = token.type, token.string
            if kind in (tokenize.NL, tokenize.COMMENT):
                continue
            if kind == tokenize.NAME:
                if chain and previous == '.':
                    chain.append(text)
                else:
                    flush()
                    if keyword.iskeyword(text):
                        chain, loose = [], False
                    else:
                        chain, line, loose = [text], token.start[0], previous == '.'
            elif not (kind == tokenize.OP and text == '.'):
                flush()
                chain, loose = [], False
            previous = text if kind == tokenize.OP else ''
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    flush()
    return found


def bound_names(source):
    """(imported, defined): the names import lines bind (import os.path binds
    os; from json import dumps as to_json binds to_json) and the names def
    and class lines define. Read line by line, so half-typed code counts."""
    imported, defined = set(), set()
    for text in source.splitlines():
        match = FROM_LINE.match(text) or IMPORT_LINE.match(text)
        if match:
            for part in match.group(1).split(','):
                words = part.split()
                if not words or words[0] == '*':
                    continue
                bound = words[2] if len(words) == 3 and words[1] == 'as' else words[0]
                root = bound.split('.')[0]
                if root.isidentifier():
                    imported.add(root)
        match = DEFINE_LINE.match(text)
        if match:
            defined.add(match.group(1))
    return imported, defined


def useful_names(found, imported, defined, limit=None):
    """The dotted names in found ([(line, dotted)]) a tap can explain, each
    once, first seen first: rooted in an import or a builtin, or your own
    def or class. Plain variables and self.x are left out."""
    kept = []
    for _, dotted in found:
        root = dotted.split('.', 1)[0]
        if dotted in kept:
            continue
        if root in imported or root in defined or root in BUILTIN_NAMES:
            kept.append(dotted)
            if limit and len(kept) >= limit:
                break
    return kept

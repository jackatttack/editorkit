"""What a line of code is, in words: Explain's view when the cursor is on no name.

    facts = line_facts.describe(source, 12)
    facts.title       'def explainer_page()'
    facts.kind        'function'
    facts.first       the first line of the statement the line belongs to
    facts.last        its last line
    facts.doc         its docstring (a def, a class, or a docstring line itself)
    facts.code        the statement's lines to show (a def or class: its header)
    facts.sentence    one plain sentence, with `code` in backticks

Pure: no UI, and it never runs or imports the code it reads.
"""
import ast
import collections
import textwrap

# --- Settings -------------------------------------------------------------

CODE_LINES = 12          # most lines of a statement shown
SHORT = 48               # longest piece of code quoted in a sentence
TITLE_LENGTH = 60
BLOCK_WORDS = {ast.If: 'if', ast.For: 'for', ast.AsyncFor: 'for', ast.While: 'while',
               ast.With: 'with', ast.AsyncWith: 'with', ast.Try: 'try'}
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)

Facts = collections.namedtuple('Facts', 'title kind first last doc code sentence')


# --- Reading one line -----------------------------------------------------

def describe(source, line, parsed=None):
    """Facts for 1-based line of source. parsed: (tree, parents) when the
    caller has parsed the source already (walk does, once)."""
    lines = source.split('\n')
    text = lines[line - 1] if 0 < line <= len(lines) else ''
    stripped = text.strip()
    if not stripped:
        return Facts('Blank line', 'blank', line, line, '', '', '')
    if stripped.startswith('#'):
        return Facts('Comment', 'comment', line, line, stripped.lstrip('#').strip(), '', '')
    if parsed is None:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return Facts(clip(stripped, TITLE_LENGTH), 'line', line, line, '', stripped,
                         'The file does not parse yet, so this is the line as text.')
        parsed = (tree, parents_of(tree))
    tree, parents = parsed
    node = innermost_statement(tree, line)
    if node is None:
        return Facts(clip(stripped, TITLE_LENGTH), 'line', line, line, '', stripped, '')
    return facts_for(node, parents, lines, stripped)


def facts_for(node, parents, lines, stripped):
    """Facts for one statement: what it is, then a sentence about it."""
    parent = parents.get(node)
    first, last = first_line(node), node.end_lineno
    code = code_lines(lines, first, last)
    title = clip(stripped, TITLE_LENGTH)
    if is_docstring(node, parent):
        if isinstance(parent, ast.Module):
            title, owner = 'Module docstring', 'file'
        else:
            title = 'Docstring of %s' % parent.name
            owner = 'class' if isinstance(parent, ast.ClassDef) else 'function'
        return Facts(title, 'docstring', first, last, ast.get_docstring(parent) or '', '',
                     'The first string in a %s is its docstring: help() and Explain read it.'
                     % owner)
    if isinstance(node, FUNCTIONS):
        what = 'method' if isinstance(parent, ast.ClassDef) else 'function'
        return Facts('def %s(%s)' % (node.name, short(node.args)), what, first, last,
                     ast.get_docstring(node) or '', header_lines(lines, node),
                     'Defines the %s `%s`; its body runs when it is called.' % (what, node.name))
    if isinstance(node, ast.ClassDef):
        bases = ', '.join(short(base) for base in node.bases)
        return Facts('class %s%s' % (node.name, '(%s)' % bases if bases else ''), 'class',
                     first, last, ast.get_docstring(node) or '', header_lines(lines, node),
                     'Defines the class `%s`.' % node.name)
    if isinstance(node, ast.Import):
        return Facts(title, 'import', first, last, '', code,
                     'Imports %s.' % names_of(node))
    if isinstance(node, ast.ImportFrom):
        module = '.' * node.level + (node.module or '')
        return Facts(title, 'import', first, last, '', code,
                     'From `%s` imports %s.' % (module, names_of(node)))
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        named = ', '.join(short(target) for target in targets)
        return Facts(title, 'assignment', first, last, '', code, set_sentence(named, node.value))
    if isinstance(node, ast.AugAssign):
        return Facts(title, 'assignment', first, last, '', code,
                     'Updates `%s` from its old value.' % short(node.target))
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return Facts(title, 'call', first, last, '', code,
                     'Calls `%s()`.' % short(node.value.func))
    if isinstance(node, ast.Return):
        owner = enclosing_function(node, parents)
        if node.value is None:
            return Facts(title, 'return', first, last, '', code, 'Leaves the function here.')
        return Facts(title, 'return', first, last, '', code,
                     'Hands `%s` back to whoever called %s.'
                     % (short(node.value), '`%s`' % owner if owner else 'the function'))
    word = next((word for kind, word in BLOCK_WORDS.items() if isinstance(node, kind)), None)
    if word:
        return Facts('%s block' % word, word, first, last, '', code, block_sentence(node))
    return Facts(title, type(node).__name__.lower(), first, last, '', code, '')


def block_sentence(node):
    """What a block does, in words."""
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return 'Repeats the lines under it for each `%s` in `%s`.' % (short(node.target),
                                                                     short(node.iter))
    if isinstance(node, ast.While):
        return 'Repeats the lines under it while `%s`.' % short(node.test)
    if isinstance(node, ast.If):
        return 'Runs the lines under it only when `%s`.' % short(node.test)
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return 'Runs the lines under it with `%s`.' % ', '.join(
            short(item.context_expr) for item in node.items)
    return 'Tries the lines under it; `except` catches what goes wrong.'


# --- Walking through a selection -----------------------------------------------

WALK_LIMIT = 14              # statements described for one selection


def walk(source, first, last, limit=WALK_LIMIT):
    """[(line, facts)]: each statement in lines first..last once, in order
    (blank lines left out). The source is parsed once."""
    try:
        tree = ast.parse(source)
        parsed = (tree, parents_of(tree))
    except SyntaxError:
        parsed = None
    found, seen = [], set()
    for line in range(first, last + 1):
        facts = describe(source, line, parsed) if parsed else describe(source, line)
        if facts.kind == 'blank':
            continue
        key = (facts.first, facts.last, facts.title)
        if key in seen:
            continue
        seen.add(key)
        found.append((line, facts))
        if len(found) >= limit:
            break
    return found


def step_words(facts):
    """One statement in a walk, in words."""
    if facts.kind == 'docstring':
        return 'The docstring: %s' % (facts.doc.strip().split('\n')[0] or '…')
    if facts.kind == 'comment':
        return 'A comment: %s' % facts.doc
    return facts.sentence or '`%s`' % facts.title


# --- Helpers --------------------------------------------------------------

def parents_of(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def first_line(node):
    """A statement's first line, counting its decorators."""
    return min([node.lineno] + [item.lineno for item in getattr(node, 'decorator_list', ())])


def innermost_statement(tree, line):
    """The smallest statement covering line (the deeper one when two tie)."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and first_line(node) <= line <= node.end_lineno:
            if best is None or span(node) <= span(best):
                best = node
    return best


def span(node):
    return node.end_lineno - first_line(node)


def is_docstring(node, parent):
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and isinstance(parent, (ast.Module, ast.ClassDef) + FUNCTIONS)
            and parent.body and parent.body[0] is node)


def code_lines(lines, first, last):
    shown = lines[first - 1:min(last, first + CODE_LINES - 1)]
    return textwrap.dedent('\n'.join(shown)).strip('\n')


def header_lines(lines, node):
    """A def's or class's lines up to its body (at least its own line)."""
    body_start = node.body[0].lineno if node.body else node.lineno + 1
    return code_lines(lines, first_line(node), max(node.lineno, body_start - 1))


def names_of(node):
    return ', '.join('`%s%s`' % (alias.name, ' as %s' % alias.asname if alias.asname else '')
                     for alias in node.names)


def set_sentence(named, value):
    if value is None:
        return 'Says what type `%s` holds, without a value yet.' % named
    if isinstance(value, ast.Call):
        return 'Calls `%s()` and names the result `%s`.' % (short(value.func), named)
    return 'Sets `%s` to `%s`.' % (named, short(value))


def enclosing_function(node, parents):
    while node in parents:
        node = parents[node]
        if isinstance(node, FUNCTIONS):
            return node.name
    return ''


def short(node):
    """Code for node on one line, cut at SHORT."""
    try:
        words = ' '.join(ast.unparse(node).split())
    except Exception:
        return '…'
    return clip(words, SHORT)


def clip(words, length):
    return words if len(words) <= length else words[:length - 1] + '…'
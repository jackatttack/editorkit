"""Code files for tools: walk a folder and search what is in it.

    from editorkit import files
    for hit in files.search('render_board', root):
        print(hit.path, hit.line, hit.text)

Pure Python (no ui, objc_util or editor), so it runs on any thread,
headless and in tests. search() is a generator: a tool can show hits as
they arrive and stop early.
"""
import collections
import os
import re


# --- Settings -------------------------------------------------------------

# Files worth searching, by extension.
CODE_EXTENSIONS = ('.py', '.txt', '.md', '.json', '.pyui', '.js', '.html', '.css')

# Folders never entered, like Forge's ACTIVE_ONLY. Hidden folders (a leading
# dot) are skipped too. site-packages-3 and release hold installed or staged
# copies, which would double every hit; parked and _to_delete hold retired code.
SKIP_FOLDERS = ('__pycache__', 'archive', 'archives', 'backup', 'backups',
                'script_snapshots', 'site-packages', 'site-packages-3',
                'release', 'parked', '_to_delete')

MAX_FILE_BYTES = 500000      # larger files are skipped
MAX_HITS = 500               # a search stops after this many


# --- Results --------------------------------------------------------------

Hit = collections.namedtuple('Hit', 'path line start end text')
Hit.__doc__ = """One match: path, line (1-based), start and end (columns in
the line, Python indices) and text (the whole line, right-stripped)."""


# --- Walking --------------------------------------------------------------

def skip_folder(name):
    return name.startswith('.') or name in SKIP_FOLDERS


def code_files(root):
    """Every searchable file under root in a stable order: a folder's files
    by name, then its subfolders by name."""
    for folder, folder_names, file_names in os.walk(root):
        folder_names[:] = sorted(name for name in folder_names if not skip_folder(name))
        for name in sorted(file_names):
            # Hidden files (a leading dot) are indexes and settings, not code.
            if not name.startswith('.') and name.lower().endswith(CODE_EXTENSIONS):
                yield os.path.join(folder, name)


def read_text(path):
    """The file's text, or None when it is too big, unreadable or binary."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    except OSError:
        return None
    if '\0' in text:
        return None
    return text


# --- Searching ------------------------------------------------------------

def make_pattern(term, case_sensitive=False, whole_word=False, regex=False):
    """The compiled pattern for a search, with Find's three switches.
    Raises ValueError for an empty term or a regex that does not compile."""
    if not term:
        raise ValueError('nothing to search for')
    source = term if regex else re.escape(term)
    if whole_word:
        source = r'\b(?:%s)\b' % source
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(source, flags)
    except re.error as error:
        raise ValueError('not a valid pattern: %s' % error)


def search_text(text, pattern, path=''):
    """Hits for pattern in one text, line by line."""
    for number, line in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(line):
            if match.end() == match.start():
                continue          # an empty regex match marks nothing
            yield Hit(path, number, match.start(), match.end(), line.rstrip())


def search(term, root, case_sensitive=False, whole_word=False, regex=False,
           limit=MAX_HITS):
    """Every hit for term in the code files under root, file by file, at
    most limit of them, as a generator.

    The pattern is checked straight away, so a bad term raises ValueError
    here rather than on the first next()."""
    pattern = make_pattern(term, case_sensitive, whole_word, regex)
    return _hits(pattern, root, limit)


def _hits(pattern, root, limit):
    count = 0
    for path in code_files(root):
        text = read_text(path)
        if text is None:
            continue
        for hit in search_text(text, pattern, path):
            yield hit
            count += 1
            if count >= limit:
                return
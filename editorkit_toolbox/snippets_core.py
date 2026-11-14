
"""Snippets core: the library, clipboard parsing and live fields.

Pure Python with no Pythonista imports, so every rule here can be tested
without any UI. Snippets (snippets.py) builds on this module.

Storage promises:
- Writes are atomic: a crash mid-save leaves the previous file intact.
- The previous version is kept beside the library as a .bak file.
- An unreadable library is never replaced with an empty one.
- A save is refused if another running copy (the app or the keyboard
  extension) changed the file after this copy loaded it.
"""

import datetime
import hashlib
import json
import os
import re
import tempfile
import uuid


# ---------------------------------------------------------------------------
# Settings you can edit
# ---------------------------------------------------------------------------

LIBRARY_FILENAME = "snippets_library.json"
DEFAULT_COLUMN_NAME = "Snippets"
TITLE_MAX_LENGTH = 32
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"

# New columns take these colours in order, then the list repeats.
COLUMN_COLOURS = [
    "#8E6CEF",  # purple
    "#2F80ED",  # blue
    "#27AE60",  # green
    "#F2994A",  # orange
    "#EB5757",  # red
    "#F2C94C",  # yellow
    "#56CCF2",  # sky
]


# ---------------------------------------------------------------------------
# Format rules: saved libraries and the smoke tests depend on these
# ---------------------------------------------------------------------------

LIBRARY_FORMAT_VERSION = 1
TITLE_MARKER = "@"
LIVE_FIELD = re.compile(r"\$\{(date|time|clipboard|cursor)\}")
COLUMN_COMMAND = re.compile(r"\*\*(.+?)\*\*")
HEX_COLOUR = re.compile(r"#[0-9A-Fa-f]{6}")
GRID_OPTION = "grid"
TARGET_MARKER = ">"
BLOCK_SEPARATOR = "---"
# Any line of 2+ dashes separates blocks: hyphens, en or em dashes in any mix,
# because iOS Smart Punctuation turns typed "---" into "—-" or "——".
SEPARATOR_LINE = re.compile("[-\u2010-\u2015\u2212]{2,}")


class LibraryError(Exception):
    """The library file could not be read or safely written."""


class LibraryChangedElsewhere(LibraryError):
    """Another running copy saved the library after this copy loaded it."""


# ---------------------------------------------------------------------------
# Clipboard parsing
# ---------------------------------------------------------------------------

def trim_blank_lines(text):
    """Remove blank lines from both ends. Indentation inside is kept."""
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def parse_clipboard(text):
    """Split one block into (title, body). See parse_snippet for the rules."""
    title, body, target = parse_snippet(text)
    return title, body

def parse_snippet(text):
    """Split one block into (title, body, target_column).

    "@Title@ body" saves with that title. The text must start with the marker
    and the title must close on the first line. The body is the rest of that
    line plus every line below it.

    "@Title@ >Column" on the first line sends the snippet to that column;
    its body goes on the lines below.

    Anything else returns (None, body, None), and the keyboard treats it as
    untitled. A title with no body is also treated as plain text.

        "@Zoom@ https://zoom.us/j/123"   -> ("Zoom", "https://zoom.us/j/123", None)
        "@Deploy@ >Forge", newline, "RUN x.py" -> ("Deploy", "RUN x.py", "Forge")
        "@property", newline, "def x"    -> (None, the whole text, None)
    """
    body = trim_blank_lines(text or "")
    # Copying from chat often adds a stray leading space, so ignore it here.
    candidate = body.lstrip()
    if not candidate.startswith(TITLE_MARKER):
        return None, body, None

    first_line, _, rest = candidate.partition("\n")
    closing = first_line.find(TITLE_MARKER, 1)
    if closing == -1:
        return None, body, None

    title = first_line[1:closing].strip()
    remainder = first_line[closing + 1:].strip()
    target = None
    if remainder.startswith(TARGET_MARKER):
        target = remainder[len(TARGET_MARKER):].strip() or None
        remainder = ""
    content = trim_blank_lines(remainder + ("\n" + rest if rest else ""))
    if not title or not content:
        return None, body, None
    return title, content, target


def suggest_title(body):
    """A title from the first non-blank line, shortened to fit a button."""
    first = next((line.strip() for line in body.splitlines() if line.strip()), "")
    title = " ".join(first.split())
    if len(title) > TITLE_MAX_LENGTH:
        title = title[:TITLE_MAX_LENGTH - 1].rstrip() + "…"
    return title or "Untitled"

def parse_column_command(text):
    """Return (name, colour, grid) when the clipboard asks for a new column, else None.

        **Addresses**                       -> ("Addresses", None, False)
        **Links**, newline, #7fcaee         -> ("Links", "#7fcaee", False)
        **Symbols**, newline, #7fcaee grid  -> ("Symbols", "#7fcaee", True)

    The optional second line holds a colour, the word grid, or both, in any
    order. Grid columns pack snippets three to a row, like Maths.
    Anything else is an ordinary snippet, so bold text copied with more
    content is never mistaken for a command.
    """
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not 1 <= len(lines) <= 2:
        return None
    match = COLUMN_COMMAND.fullmatch(lines[0])
    if not match or not match.group(1).strip():
        return None

    colour = None
    grid = False
    if len(lines) == 2:
        for option in lines[1].split():
            if HEX_COLOUR.fullmatch(option) and colour is None:
                colour = option
            elif option.lower() == GRID_OPTION and not grid:
                grid = True
            else:
                return None
    return match.group(1).strip(), colour, grid

# ---------------------------------------------------------------------------
# Batches: several blocks separated by --- lines
# ---------------------------------------------------------------------------

def is_separator(line):
    """True for a line made only of dashes, at least two long."""
    return SEPARATOR_LINE.fullmatch(line.strip()) is not None


def is_block_start(line):
    """True for a line that begins a snippet (@Title@) or column (**Name**) block."""
    stripped = line.strip()
    if COLUMN_COMMAND.fullmatch(stripped):
        return True
    return stripped.startswith(TITLE_MARKER) and stripped.find(TITLE_MARKER, 1) > 1


def next_block_starts(lines, start):
    for line in lines[start:]:
        if line.strip():
            return is_block_start(line)
    return False


def is_valid_block(block):
    return parse_column_command(block) is not None or parse_snippet(block)[0] is not None


def split_blocks(text):
    """Split clipboard text into blocks on --- lines.

    A --- line only splits when the next non-blank line starts a block, and
    if any resulting piece is not a valid block the whole text stays as one.
    Together these keep ordinary documents (markdown rules and all) as a
    single snippet.
    """
    lines = (text or "").replace("\r\n", "\n").split("\n")
    blocks = []
    current = []
    for index, line in enumerate(lines):
        if is_separator(line) and next_block_starts(lines, index + 1):
            blocks.append(current)
            current = []
        else:
            current.append(line)
    blocks.append(current)

    texts = ["\n".join(block) for block in blocks if "\n".join(block).strip()]
    if len(texts) > 1 and not all(is_valid_block(block) for block in texts):
        return [text] if (text or "").strip() else []
    return texts


# ---------------------------------------------------------------------------
# Live fields
# ---------------------------------------------------------------------------

def expand_live_fields(text, read_clipboard, now=None):
    """Fill in live fields. Returns (text, cursor_index).

    ${date} and ${time} use the formats in the settings above.
    ${clipboard} calls read_clipboard, but only when the field is present,
    so plain snippets never touch the clipboard.
    ${cursor} is removed, and cursor_index says where the first one was
    (None when absent). Any other ${...} text is left exactly as written.
    """
    now = now or datetime.datetime.now()
    clipboard_text = None
    cursor_index = None
    pieces = []
    position = 0

    for match in LIVE_FIELD.finditer(text):
        pieces.append(text[position:match.start()])
        name = match.group(1)
        if name == "cursor":
            if cursor_index is None:
                cursor_index = sum(len(piece) for piece in pieces)
            value = ""
        elif name == "date":
            value = now.strftime(DATE_FORMAT)
        elif name == "time":
            value = now.strftime(TIME_FORMAT)
        else:
            if clipboard_text is None:
                clipboard_text = read_clipboard() or ""
            value = clipboard_text
        pieces.append(value)
        position = match.end()

    pieces.append(text[position:])
    return "".join(pieces), cursor_index

def uses_clipboard(text):
    """True when typing this text would read the clipboard."""
    return any(match.group(1) == "clipboard" for match in LIVE_FIELD.finditer(text))


# ---------------------------------------------------------------------------
# Library storage
# ---------------------------------------------------------------------------

def default_library_path():
    """The library lives beside this file, local to the device."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), LIBRARY_FILENAME)


def new_id():
    return uuid.uuid4().hex[:12]


def new_column_data(name, colour, grid=False):
    return {"id": new_id(), "name": name, "colour": colour, "grid": grid, "snippets": []}


def empty_library_data():
    return {
        "version": LIBRARY_FORMAT_VERSION,
        "columns": [new_column_data(DEFAULT_COLUMN_NAME, COLUMN_COLOURS[0])],
    }


def validate(data):
    """Raise LibraryError unless data is a well-formed library."""
    if not isinstance(data, dict) or data.get("version") != LIBRARY_FORMAT_VERSION:
        raise LibraryError("Unsupported library format")
    columns = data.get("columns")
    if not isinstance(columns, list):
        raise LibraryError("Columns must be a list")

    seen_ids = set()
    for column in columns:
        if not isinstance(column, dict):
            raise LibraryError("Invalid column record")
        for key in ("id", "name", "colour"):
            if not isinstance(column.get(key), str):
                raise LibraryError("Column needs text field: " + key)
        if not isinstance(column.get("snippets"), list):
            raise LibraryError("Column snippets must be a list")
        if not isinstance(column.get("grid", False), bool):
            raise LibraryError("Column grid must be true or false")
        for snippet in column["snippets"]:
            if not isinstance(snippet, dict):
                raise LibraryError("Invalid snippet record")
            for key in ("id", "title", "text"):
                if not isinstance(snippet.get(key), str):
                    raise LibraryError("Snippet needs text field: " + key)
            if snippet["id"] in seen_ids:
                raise LibraryError("Duplicate snippet id: " + snippet["id"])
            seen_ids.add(snippet["id"])
    return data


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bytes_or_none(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as stream:
        return stream.read()


def atomic_write(path, raw):
    """Write to a temporary file, then swap it into place in one step."""
    folder = os.path.dirname(os.path.abspath(path))
    handle, temporary = tempfile.mkstemp(prefix=".snippets-", dir=folder)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Library:
    """An ordered list of columns, each holding an ordered list of snippets.

    Changes stay in memory until save() is called.
    """

    def __init__(self, path=None):
        self.path = path or default_library_path()
        self.backup_path = self.path + ".bak"
        raw = read_bytes_or_none(self.path)
        if raw is None:
            self.data = empty_library_data()
            self.loaded_digest = None
            return
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError as error:
            raise LibraryError("Library is unreadable: {}".format(error))
        self.data = validate(data)
        self.loaded_digest = digest(raw)

    @property
    def columns(self):
        return self.data["columns"]

    # Finding -------------------------------------------------------------

    def column(self, column_id):
        for column in self.columns:
            if column["id"] == column_id:
                return column
        raise KeyError("No column with id " + column_id)

    def locate(self, snippet_id):
        """Return (column, index) for a snippet."""
        for column in self.columns:
            for index, snippet in enumerate(column["snippets"]):
                if snippet["id"] == snippet_id:
                    return column, index
        raise KeyError("No snippet with id " + snippet_id)

    def snippet(self, snippet_id):
        column, index = self.locate(snippet_id)
        return column["snippets"][index]

    # Columns -------------------------------------------------------------

    def add_column(self, name, colour=None, grid=False):
        """Add a column at the end. Without a colour, the next palette colour is used.

        A grid column packs its snippets three to a row, for short ones like symbols.
        """
        colour = colour or COLUMN_COLOURS[len(self.columns) % len(COLUMN_COLOURS)]
        column = new_column_data(name.strip() or "Untitled", colour, grid)
        self.columns.append(column)
        return column

    def rename_column(self, column_id, name):
        self.column(column_id)["name"] = name.strip() or "Untitled"

    def delete_column(self, column_id, include_snippets=False):
        """Delete a column. The last column can never be deleted.

        A column that still holds snippets is only deleted when
        include_snippets is True, and its snippets go with it.
        """
        column = self.column(column_id)
        if column["snippets"] and not include_snippets:
            raise LibraryError("Move or delete the snippets in this column first")
        if len(self.columns) == 1:
            raise LibraryError("The library needs at least one column")
        self.columns.remove(column)

    def move_column(self, column_id, to_index):
        column = self.column(column_id)
        self.columns.remove(column)
        to_index = max(0, min(to_index, len(self.columns)))
        self.columns.insert(to_index, column)

    # Snippets ------------------------------------------------------------

    def add_snippet(self, column_id, title, text):
        """Add a snippet to the end of a column and return it."""
        snippet = {
            "id": new_id(),
            "title": title.strip() or suggest_title(text),
            "text": text,
        }
        self.column(column_id)["snippets"].append(snippet)
        return snippet

    def find_column(self, name):
        """The column with this name (ignoring case), or None."""
        wanted = name.strip().casefold()
        for column in self.columns:
            if column["name"].strip().casefold() == wanted:
                return column
        return None

    def save_snippet(self, column_id, title, text):
        """Add a snippet, or update one with the same title in that column.

        Returns (snippet, was_update).
        """
        for snippet in self.column(column_id)["snippets"]:
            if snippet["title"] == title.strip():
                snippet["text"] = text
                return snippet, True
        return self.add_snippet(column_id, title, text), False

    def update_snippet(self, snippet_id, title=None, text=None):
        snippet = self.snippet(snippet_id)
        if title is not None:
            snippet["title"] = title.strip() or suggest_title(snippet["text"])
        if text is not None:
            snippet["text"] = text

    def delete_snippet(self, snippet_id):
        column, index = self.locate(snippet_id)
        del column["snippets"][index]

    def move_snippet(self, snippet_id, column_id, to_index):
        """Move a snippet to a position in any column.

        to_index counts positions in the target column after the snippet has
        been lifted out, which is how a drag sees the list.
        """
        source, index = self.locate(snippet_id)
        snippet = source["snippets"].pop(index)
        target = self.column(column_id)["snippets"]
        to_index = max(0, min(to_index, len(target)))
        target.insert(to_index, snippet)

    # Saving --------------------------------------------------------------

    def save(self):
        """Write the library, keeping the previous version as a backup."""
        on_disk = read_bytes_or_none(self.path)
        current_digest = digest(on_disk) if on_disk is not None else None
        if current_digest != self.loaded_digest:
            raise LibraryChangedElsewhere(
                "The library was changed by another copy. Reload before saving.")
        raw = encode(validate(self.data))
        if on_disk is not None:
            atomic_write(self.backup_path, on_disk)
        atomic_write(self.path, raw)
        self.loaded_digest = digest(raw)


# ---------------------------------------------------------------------------
# Import and export: the clipboard format an AI can read and write
# ---------------------------------------------------------------------------

def import_text(library, text, current_column_id):
    """Apply clipboard text to the library: one snippet, a column command, or a batch.

    Blocks are handled in order. A column block creates that column (or
    updates its colour and grid) and sends the snippets after it there.
    "@Title@ >Column" sends one snippet to a named column, creating it if
    needed, without changing where later snippets go. A titled snippet whose
    title already exists in its column is updated in place; untitled
    snippets are always added.

    Returns {"added": [titles], "updated": [titles], "new_columns": [names],
    "column_id": where saving should continue}.
    """
    # "untitled" lists ids saved under a suggested title, so the keyboard can offer a rename.
    result = {"added": [], "updated": [], "new_columns": [], "untitled": [],
              "column_id": current_column_id}
    for block in split_blocks(text):
        command = parse_column_command(block)
        if command:
            name, colour, grid = command
            column = library.find_column(name)
            if column is None:
                column = library.add_column(name, colour, grid)
                result["new_columns"].append(name)
            else:
                if colour:
                    column["colour"] = colour
                if grid:
                    column["grid"] = True
            result["column_id"] = column["id"]
            continue

        title, body, target = parse_snippet(block)
        column_id = result["column_id"]
        if target:
            column = library.find_column(target)
            if column is None:
                column = library.add_column(target)
                result["new_columns"].append(target)
            column_id = column["id"]

        if title is None:
            snippet, was_update = library.add_snippet(column_id, "", body), False
            result["untitled"].append(snippet["id"])
        else:
            snippet, was_update = library.save_snippet(column_id, title, body)
        result["updated" if was_update else "added"].append(snippet["title"])
    return result


def summarise_import(result):
    """A short status line for what import_text did."""
    added, updated, columns = result["added"], result["updated"], result["new_columns"]
    if len(added) == 1 and not updated and not columns:
        return "Saved: " + added[0]
    if len(updated) == 1 and not added and not columns:
        return "Updated: " + updated[0]
    if columns and not added and not updated:
        return "New column: " + ", ".join(columns)
    parts = []
    if added:
        parts.append("{} added".format(len(added)))
    if updated:
        parts.append("{} updated".format(len(updated)))
    if columns:
        parts.append("{} new column{}".format(len(columns), "" if len(columns) == 1 else "s"))
    return ", ".join(parts) or "Nothing to save"


def export_snippet(snippet):
    return "{0}{1}{0}\n{2}".format(TITLE_MARKER, snippet["title"], snippet["text"])


def export_column(column):
    """A column block followed by its snippets, ready to import again.

    Known limit: a title containing @, or a body containing a --- line
    followed by an @Title@ line, will not survive the round trip.
    """
    options = [column["colour"]] + ([GRID_OPTION] if column.get("grid") else [])
    blocks = ["**{}**\n{}".format(column["name"], " ".join(options))]
    blocks += [export_snippet(snippet) for snippet in column["snippets"]]
    return ("\n" + BLOCK_SEPARATOR + "\n").join(blocks)


def export_library(library):
    return ("\n" + BLOCK_SEPARATOR + "\n").join(
        export_column(column) for column in library.columns)
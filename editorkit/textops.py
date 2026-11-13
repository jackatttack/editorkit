"""Pure text edits for tiles.TextBox: indent and outdent whole lines.

No ui, no editor: tests/smoke_textops.py checks them. Positions are Python
string indices. Each edit returns (new text, selection start, selection
end): a bare cursor moves with its line; a selection is reselected over
the whole shifted block.
"""

INDENT = '    '


def line_block(text, start, end):
    """(block start, block end) of the whole lines the selection touches,
    without the last line's newline. A selection ending just after a
    newline ends on that line."""
    block_start = text.rfind('\n', 0, start) + 1
    stop = end - 1 if end > start and text[end - 1:end] == '\n' else end
    newline = text.find('\n', max(stop, start))
    return block_start, (len(text) if newline == -1 else newline)


def indent(text, start, end, unit=INDENT):
    """Indent the touched lines (blank lines stay blank)."""
    block_start, block_end = line_block(text, start, end)
    lines = text[block_start:block_end].split('\n')
    block = '\n'.join(unit + line if line.strip() else line for line in lines)
    new_text = text[:block_start] + block + text[block_end:]
    if start == end:
        moved = start + len(unit) if lines[0].strip() else start
        return new_text, moved, moved
    return new_text, block_start, block_start + len(block)


def outdent(text, start, end, unit=INDENT):
    """Take one indent off the touched lines: a tab, or up to len(unit) spaces."""
    block_start, block_end = line_block(text, start, end)
    lines = text[block_start:block_end].split('\n')
    removed_first = 0
    out = []
    for number, line in enumerate(lines):
        if line.startswith('\t'):
            cut = 1
        else:
            cut = min(len(line) - len(line.lstrip(' ')), len(unit))
        if number == 0:
            removed_first = cut
        out.append(line[cut:])
    block = '\n'.join(out)
    new_text = text[:block_start] + block + text[block_end:]
    if start == end:
        moved = max(block_start, start - removed_first)
        return new_text, moved, moved
    return new_text, block_start, block_start + len(block)
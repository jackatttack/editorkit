"""What is under the cursor or the selection: a number or a colour.

    thing = detect.what_is_here(text, start, end)
    thing.kind          'number', 'colour', or None (nothing it knows)
    thing.start, .end   the characters it covers in text
    thing.text          as written
    thing.value         a number (int or float), or a colour (r, g, b, a) in 0..1
    thing.form          how it is written, so a tool writes it back the same way

    format_number(value, form), number_step(form)
    format_colour(rgba, form)

A colour wins over the numbers inside it. A selection is searched for the
first colour or number inside it; a bare cursor takes the one it touches
(either end counts). Pure (no ui, no editor):
tests/smoke_detect.py checks it.
"""
import re
from collections import namedtuple


Thing = namedtuple('Thing', 'kind start end text value form')
NOTHING = Thing(None, 0, 0, '', None, None)


# --- Patterns ---------------------------------------------------------------

# A number standing on its own: not part of a name (v2), an attribute or a
# hex literal (0x1F).
NUMBER = re.compile(r'(?<![\w.])-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?(?![\w.])')

# '#RGB', '#RRGGBB' or '#RRGGBBAA', only straight after a quote (so a
# comment like "# add" is never a colour).
HEX = re.compile(r'(?<=[\'"])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])')

PART = r'(\d+(?:\.\d*)?|\.\d+)'
TUPLE = re.compile(r'\(\s*%s\s*,\s*%s\s*,\s*%s\s*(?:,\s*%s\s*)?\)' % (PART, PART, PART, PART))


# --- Numbers --------------------------------------------------------------------

def number_form(raw):
    """How a number is written: float or int, and its decimal places."""
    if 'e' in raw.lower():
        return {'float': True, 'decimals': None}
    if '.' in raw:
        return {'float': True, 'decimals': len(raw.split('.', 1)[1])}
    return {'float': False, 'decimals': 0}


def numbers_in(segment, offset):
    found = []
    for match in NUMBER.finditer(segment):
        raw = match.group(0)
        form = number_form(raw)
        value = float(raw) if form['float'] else int(raw)
        found.append(Thing('number', offset + match.start(), offset + match.end(),
                           raw, value, form))
    return found


def number_step(form):
    """One step: the place of the last digit written (0.35 steps by 0.01)."""
    if not form['float']:
        return 1
    decimals = form['decimals']
    if not decimals:
        return 0.1
    return 10 ** -decimals


def format_number(value, form):
    """value written the way the original was (same decimal places)."""
    if not form['float']:
        return str(int(round(value)))
    decimals = form['decimals']
    if decimals is None:
        return repr(float(value))
    return '%.*f' % (max(1, decimals), value)


# --- Colours ----------------------------------------------------------------------

def colours_in(segment, offset):
    found = []
    for match in HEX.finditer(segment):
        raw = match.group(0)
        digits = raw[1:]
        if len(digits) == 3:
            digits = ''.join(digit * 2 for digit in digits)
        parts = [int(digits[index:index + 2], 16) / 255.0 for index in range(0, len(digits), 2)]
        alpha = parts[3] if len(parts) == 4 else 1.0
        form = {'kind': 'hex', 'length': len(raw) - 1,
                'upper': any(letter.isupper() for letter in raw)}
        found.append(Thing('colour', offset + match.start(), offset + match.end(),
                           raw, (parts[0], parts[1], parts[2], alpha), form))
    for match in TUPLE.finditer(segment):
        raws = [part for part in match.groups() if part is not None]
        numbers = [float(part) for part in raws]
        decimal = any('.' in part for part in raws)
        if decimal and all(0.0 <= number <= 1.0 for number in numbers):
            scale = 'unit'
            values = numbers
        elif not decimal and all(0 <= number <= 255 for number in numbers) and max(numbers) > 1:
            scale = '255'
            values = [number / 255.0 for number in numbers]
        else:
            continue                          # just numbers in brackets
        decimals = max([len(part.split('.', 1)[1]) for part in raws if '.' in part] or [0])
        alpha = values[3] if len(values) == 4 else 1.0
        form = {'kind': 'tuple', 'scale': scale, 'count': len(values),
                'decimals': max(1, decimals)}
        found.append(Thing('colour', offset + match.start(), offset + match.end(),
                           match.group(0), (values[0], values[1], values[2], alpha), form))
    return found


def format_colour(rgba, form):
    """rgba (0..1 each) written the way the original colour was."""
    rgba = [min(1.0, max(0.0, part)) for part in rgba]
    if form['kind'] == 'hex':
        parts = rgba if form['length'] == 8 else rgba[:3]
        if form['length'] == 3 and all(round(part * 255) % 17 == 0 for part in parts):
            text = '#' + ''.join('%X' % (round(part * 255) // 17) for part in parts)
        else:
            text = '#' + ''.join('%02X' % round(part * 255) for part in parts)
        return text if form['upper'] else text.lower()
    parts = rgba[:form['count']]
    if form['scale'] == '255':
        return '(%s)' % ', '.join(str(int(round(part * 255))) for part in parts)
    return '(%s)' % ', '.join('%.*f' % (form['decimals'], part) for part in parts)


# --- What is here ---------------------------------------------------------------

def things_in(segment, offset):
    """Colours first: they win over the numbers inside them."""
    return colours_in(segment, offset) + numbers_in(segment, offset)


def what_is_here(text, start, end=None):
    """The colour or number at the cursor (start), or the first inside the
    selection start..end; NOTHING when there is none."""
    end = start if end is None else end
    if end > start:
        found = things_in(text[start:end], start)
        return found[0] if found else NOTHING
    line_start = text.rfind('\n', 0, start) + 1
    line_end = text.find('\n', start)
    if line_end < 0:
        line_end = len(text)
    found = things_in(text[line_start:line_end], line_start)
    for thing in found:
        low, high = reach(thing)
        if low <= start <= high:
            return thing
    # Touching nothing: the line's colour, if it has one (numbers are too
    # common for this: foo(3) would light up from anywhere on the line).
    colours = [thing for thing in found if thing.kind == 'colour']
    return colours[0] if colours else NOTHING


def reach(thing):
    """The cursor positions that count as touching thing: its own span,
    plus the quotes around a hex colour (a cursor after the closing quote
    still means it)."""
    if thing.kind == 'colour' and thing.form['kind'] == 'hex':
        return thing.start - 1, thing.end + 1
    return thing.start, thing.end
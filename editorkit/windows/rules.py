"""Pure rules for windows: layout maths and what kind of page a thing makes.
No ui and no Pythonista, so tests/smoke_windows.py checks them headless."""

PAGE_STYLE = ('<meta name="viewport" content="width=device-width, initial-scale=1">'
              '<style>body{background:%s;color:%s;font-family:-apple-system,sans-serif;'
              'margin:0;padding:12px}a{color:%s}</style>')


# ---- Layout -----------------------------------------------------------------


def overlaps(first, second):
    """True when two (x, y, w, h) rectangles share any area."""
    return (first[0] < second[0] + second[2] and second[0] < first[0] + first[2]
            and first[1] < second[1] + second[3] and second[1] < first[1] + first[3])


def inset(rect, by):
    """rect shrunk by `by` on every side."""
    x, y, width, height = rect
    return (x + by, y + by, max(0, width - 2 * by), max(0, height - 2 * by))


def clear_top(rect, blockers, gap, limit):
    """The top for rect, moved down until it overlaps none of blockers: each
    time it hits some, it jumps to just below the lowest of them plus gap.
    If it would pass limit (the bottom of the area), it stays where it was."""
    x, y, width, height = rect
    while y + height <= limit:
        hit = [block for block in blockers if overlaps((x, y, width, height), block)]
        if not hit:
            return y
        y = max(block[1] + block[3] for block in hit) + gap
    return rect[1]


def clamp(frame, area, least, edge):
    """frame kept at least `least` (width, height) and inside area (width,
    height) with an edge margin all round."""
    x, y, width, height = frame
    area_width, area_height = area
    least_width, least_height = least
    width = min(max(least_width, width), area_width - 2 * edge)
    height = min(max(least_height, height), area_height - 2 * edge)
    x = max(edge, min(x, area_width - edge - width))
    y = max(edge, min(y, area_height - edge - height))
    return (x, y, width, height)


def place_from_frame(frame, area_width, pin_height, snap, edge):
    """A pin place (side, inset, top) from a pin's whole frame: snapped to the
    nearer side's edge, or kept where it is. The rim around the pill (touch
    pad plus any lift) is worked out from the frame's height."""
    x, y, width, height = frame
    rim = (height - pin_height) / 2.0
    pill_x, pill_y, pill_width = x + rim, y + rim, width - 2 * rim
    side = 'right' if pill_x + pill_width / 2.0 > area_width / 2.0 else 'left'
    if snap:
        inset = edge
    elif side == 'right':
        inset = area_width - (pill_x + pill_width)
    else:
        inset = pill_x
    return (side, max(edge, inset), pill_y)


def fling_side(speed_x, threshold):
    """'right' or 'left' for a sideways fling at least threshold fast, else None."""
    if speed_x > threshold:
        return 'right'
    if speed_x < -threshold:
        return 'left'
    return None


def overhang(frame, home, area_width, rim=0.0):
    """How far a frame's visible part pokes past the edge it would cross: the
    right edge over the editor, the left edge in the console. Negative: inside."""
    x, _, width, _ = frame
    if home == 'editor':
        return (x + width - rim) - area_width
    return -(x + rim)


# ---- Content ----------------------------------------------------------------

def looks_like_html(text):
    stripped = text.strip()
    return stripped.startswith('<') and stripped.endswith('>')


def is_short_line(text, limit):
    """One short line reads best big and centred, like a display."""
    stripped = text.strip()
    return bool(stripped) and '\n' not in stripped and len(stripped) <= limit


def line_count(text):
    return len(text.strip().split('\n')) if text.strip() else 0


def is_pyui_path(thing):
    return isinstance(thing, str) and thing.strip().endswith('.pyui')


def page_html(text, background, colour, accent):
    """Full pages pass through; a fragment gets the theme's style."""
    lowered = text.lower()
    if '<html' in lowered or '<body' in lowered:
        return text
    return PAGE_STYLE % (background, colour, accent) + text
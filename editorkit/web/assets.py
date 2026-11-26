"""Pictures and other files inside a page: data URIs, read once.

Role: gather, present · Part of: editorkit/web · Pure

A page is loaded from a string, so it cannot reach files by path: a
picture goes in as a data URI.

    from editorkit.web import assets
    assets.data_uri('library/datasets/sprites/25.png')    # 'data:image/png;base64,...'
    assets.picture(path, size=44, alt='Pikachu')          # an <img> for a page

Each file is read once per run and kept while its size and time are
unchanged. A missing file gives '' (picture: '').
"""
import base64
import html
import os

# ---- Settings (editable) ---------------------------------------------------

TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
         '.svg': 'image/svg+xml', '.webp': 'image/webp', '.woff2': 'font/woff2', '.mp3': 'audio/mpeg'}
LARGEST_BYTES = 2 * 1024 * 1024      # files bigger than this are refused (a page should stay light)

_cache = {}                           # path -> (size, mtime, uri)


def data_uri(path):
    """path's bytes as a data URI, or '' when it is missing or too big."""
    try:
        state = os.stat(path)
    except OSError:
        return ''
    if state.st_size > LARGEST_BYTES:
        return ''
    kept = _cache.get(path)
    if kept and kept[0] == state.st_size and kept[1] == state.st_mtime:
        return kept[2]
    kind = TYPES.get(os.path.splitext(path)[1].lower(), 'application/octet-stream')
    with open(path, 'rb') as handle:
        uri = 'data:%s;base64,%s' % (kind, base64.b64encode(handle.read()).decode('ascii'))
    _cache[path] = (state.st_size, state.st_mtime, uri)
    return uri


def picture(path, size=None, alt='', pixelated=False):
    """An <img> showing path (size: px square), or '' when it is missing."""
    uri = data_uri(path)
    if not uri:
        return ''
    style = []
    if size:
        style.append('width:%dpx;height:%dpx' % (size, size))
    if pixelated:
        style.append('image-rendering:pixelated')
    return '<img src="%s" alt="%s"%s>' % (uri, html.escape(alt, quote=True),
                                          ' style="%s"' % ';'.join(style) if style else '')
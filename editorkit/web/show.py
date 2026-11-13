"""HTML for ek.show: fragments on editorkit's page shell.

    ek.show('<h2>Hello</h2><p>Some words.</p>')

A fragment becomes a web tile (Cards) on the page shell, so it gets fast
taps, the page-owned pinch (reflow) and the theme's colours, live. Inside
it, var(--text), --muted, --accent, --wash and the rest work (web-views
guide).

A full document (<html> or <body>), or any HTML with its own <script>,
keeps a plain web view instead: the shell shows content through innerHTML,
which never runs scripts, so moving those pages onto it would quietly
break them. A full page is yours, quirks included.

The core reaches this through a hook (windows.content.make_html_page),
wired by editorkit's root, so the core never imports the web package.
"""
from .tiles import Cards


# --- Look (editable) ------------------------------------------------------

# Prose rather than code: the shell's default font is Menlo.
FRAGMENT_CSS = """
#results { font: 15px -apple-system, sans-serif; line-height: 1.4;
    white-space: normal; padding: 8px 4px; }
#results a { color: var(--accent); }
"""


def keeps_plain_view(html):
    """True for HTML the page shell cannot show as it is: a full document,
    or anything with its own scripts."""
    lowered = html.lower()
    return '<html' in lowered or '<body' in lowered or '<script' in lowered


def page_for_html(html, window):
    """A web tile showing an HTML fragment, or None to keep the plain web
    view (see keeps_plain_view)."""
    if keeps_plain_view(html):
        return None
    tile = Cards(window, extra_css=FRAGMENT_CSS)
    tile.set_html(html)
    return tile
"""Night: a dark editor theme, installed with ek.install_theme and switched to.

Change a colour below and run it again to see it in the editor."""
import editorkit as ek

# --- The colours ---------------------------------------------------------------

PANEL, BAR, EDGE = '#121318', '#16181d', '#22252d'
PINK, TEAL, YELLOW, ORANGE, LILAC = '#e8335a', '#5fd3bc', '#f5c26b', '#ff9e64', '#c4a7ff'
TEXT, MUTED = '#e6e6e6', '#6b7280'

# The app around the code: backgrounds, tabs, gutter, selection.
COLOURS = {
    'background': PANEL, 'bar_background': BAR, 'tab_background': '#0f1014',
    'library_background': BAR, 'gutter_background': '#14161b', 'gutter_border': EDGE,
    'interstitial': '#1e2128', 'separator_line': '#0d0e11', 'thumbnail_border': EDGE,
    'default_text': TEXT, 'tab_title': TEXT, 'library_tint': TEXT,
    'line_number': '#5b6070', 'error_text': '#f87171',
    'tint': PINK, 'text_selection_tint': PINK, 'dark_keyboard': True,
}

# The code itself, by syntax scope.
SCOPES = {
    'default': {'color': TEXT},
    'keyword': {'color': PINK},
    'string': {'color': YELLOW},
    'docstring': {'color': '#d9c89e'},
    'number': {'color': ORANGE},
    'comment': {'color': MUTED, 'font-style': 'italic'},
    'function': {'color': TEAL}, 'builtinfunction': {'color': TEAL},
    'class': {'color': TEAL}, 'module': {'color': TEAL},
    'functiondef': {'color': TEAL, 'font-style': 'bold'},
    'classdef': {'color': TEAL, 'font-style': 'bold'},
    'decorator': {'color': LILAC},
}

stem = ek.install_theme('Night', COLOURS, SCOPES)
print('installed %s; now showing: %s' % (stem, ek.current_theme()))

"""Themes: list them, switch live, and make your own.

A theme is a JSON file: 20 colour and font keys plus 'scopes' for syntax
colours. Built-in themes live in the app and go by file name
('Theme08_Oceanic'). Your own live in the user themes folder and Pythonista
refers to them as 'User:<file name>'. Switching restyles the whole app live.
"""
import json
import os
import re

from objc_util import ObjCClass, ns

from . import _app

DARK_STYLE = 2
USER_PREFIX = 'User:'


def _theme():
    return ObjCClass('PA2UITheme').sharedTheme()


def _defaults():
    return ObjCClass('NSUserDefaults').standardUserDefaults()


def _dark_mode():
    return ObjCClass('UIScreen').mainScreen().traitCollection().userInterfaceStyle() == DARK_STYLE


def _slot():
    """The setting for the theme showing now (dark and light have their own)."""
    return 'ThemeNameDarkMode' if _dark_mode() else 'ThemeNameLightMode'


def build_theme(base, name, colours=None, scopes=None):
    """A new theme dict: base with colours replaced and scopes merged in."""
    result = json.loads(json.dumps(base))
    result.update(colours or {})
    result['name'] = name
    merged = dict(result.get('scopes', {}))
    for scope, style in (scopes or {}).items():
        entry = dict(merged.get(scope, {}))
        entry.update(style)
        merged[scope] = entry
    result['scopes'] = merged
    return result


def theme_file_name(name):
    return 'editorkit-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def theme_id(name, user_stems):
    """The name Pythonista stores for a theme: built-ins by file name, your own
    as 'User:<file name>'."""
    if name.startswith(USER_PREFIX):
        return name
    return USER_PREFIX + name if name in user_stems else name


def _stems(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(entry[:-5] for entry in os.listdir(folder) if entry.endswith('.json'))


def _folders():
    built_in = os.path.dirname(str(_theme().pathForTheme_('Default')))
    return built_in, str(_theme().userThemesPath())


@_app.on_main
def theme_names():
    """Every theme use_theme accepts: built-in names, then 'User:...' for yours."""
    built_in, user = _folders()
    return _stems(built_in) + [USER_PREFIX + stem for stem in _stems(user)]


@_app.on_main
def current_theme():
    value = _defaults().objectForKey_(_slot())
    return str(value) if value is not None else None


@_app.on_main
def theme_colours():
    """The current theme's colours as a plain dict, e.g. {'background': '#1e1e24'}.

    Read live from the loaded theme, so it follows theme switches and the
    dark and light slots. Only '#...' values are kept: fonts and syntax
    scopes are left out.
    """
    current = _theme().themeDict()
    colours = {}
    if current is None:
        return colours
    text_class = ObjCClass('NSString')
    for key in current.allKeys():
        value = current.objectForKey_(key)
        if value is not None and value.isKindOfClass_(text_class):
            text = str(value)
            if text.startswith('#'):
                colours[str(key)] = text
    return colours


# codeview's syntax classes and the theme scope each takes its colour from.
SYNTAX_SCOPES = {
    'kw': 'keyword',
    'fn': 'function',
    'cls': 'class',
    'builtin': 'builtinfunction',
    'self': 'builtinfunction',
    'str': 'string',
    'num': 'number',
    'com': 'comment',
}


@_app.on_main
def syntax_colours():
    """codeview's syntax classes coloured from the current theme's scopes,
    e.g. {'kw': '#e8335a', 'str': '#f5c26b'}; classes the theme leaves out
    are missing (codeview keeps its own for those). '#rrggbbaa' is cut to
    '#rrggbb' for the old web view."""
    current = _theme().themeDict()
    scopes = current.objectForKey_('scopes') if current is not None else None
    found = {}
    if scopes is None:
        return found
    for css_class, scope in SYNTAX_SCOPES.items():
        entry = scopes.objectForKey_(scope)
        if entry is None:
            continue
        colour = entry.objectForKey_('color')
        text = str(colour) if colour is not None else ''
        if text.startswith('#') and len(text) in (7, 9):
            found[css_class] = text[:7]
    return found


@_app.on_main
def refresh_theme():
    """Tell every part of the app to restyle."""
    root = _app.root()
    detail = root.detailViewController()
    library = root.masterViewController().viewControllers().objectAtIndex_(0)
    for hook in (lambda: root.themeChanged_(None),
                 lambda: detail.themeDidChange_(None),
                 lambda: library.themeDidChange_(None),
                 lambda: _theme().styleEditorView_(_app.editor_view())):
        try:
            hook()
        except Exception:
            pass


@_app.on_main
def use_theme(name):
    """Switch to a theme, live. Built-ins by file name ('Theme08_Oceanic');
    your own by file name or 'User:<file name>'. Returns the theme's title."""
    built_in, user = _folders()
    stored = theme_id(name, _stems(user))
    theme = _theme()
    theme.loadThemeNamed_(stored)
    if stored.startswith(USER_PREFIX):
        # If Pythonista did not load it by name, apply the file directly.
        path = os.path.join(user, stored[len(USER_PREFIX):] + '.json')
        with open(path, encoding='utf-8') as handle:
            wanted = json.load(handle)
        current = theme.themeDict()
        loaded = current.objectForKey_('name') if current is not None else None
        if loaded is None or str(loaded) != wanted.get('name'):
            theme.setThemeDict_(ns(wanted))
    _defaults().setObject_forKey_(stored, _slot())
    refresh_theme()
    loaded = theme.themeDict().objectForKey_('name')
    return str(loaded) if loaded is not None else None


@_app.on_main
def install_theme(name, colours=None, scopes=None, base='PythonistaDark', use=True):
    """Write a theme built on base to your themes folder; switch to it if use.
    Returns its name for use_theme ('User:editorkit-...')."""
    with open(str(_theme().pathForTheme_(base)), encoding='utf-8') as handle:
        base_dict = json.load(handle)
    data = build_theme(base_dict, name, colours, scopes)
    folder = str(_theme().userThemesPath())
    os.makedirs(folder, exist_ok=True)
    stem = theme_file_name(name)
    with open(os.path.join(folder, stem + '.json'), 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)
    if use:
        use_theme(stem)
    return USER_PREFIX + stem
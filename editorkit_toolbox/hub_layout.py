"""Your own Toolbox home view: the order of its cards, tools moved into
groups or hidden, and a few switches.

Kept in Documents/Toolbox/hub_settings.json beside the plugin folders, so
it is yours to read, back up or delete: no file (or a deleted one) is the
hub as it ships. Pure Python, no editorkit and no ui, so
tests/smoke_hub_layout.py checks it headless.

    order       card names in the order the home view shows them; cards
                not listed (new tools) follow in their own order
    groups      {tool name: group name}: any tool, Toolbox's own too, into a
                group; '' brings a plugin's tool out of its group
    hidden      card names left off the home view (Find still finds them)
    intro       the intro line at the top of the home view
    recent      recent scripts under the tools (0 for none)
    card_size   'small', 'medium' or 'large'
"""
import json
import os

DOCUMENTS = os.path.expanduser('~/Documents')
SETTINGS_PATH = os.path.join(DOCUMENTS, 'Toolbox', 'hub_settings.json')


# --- Settings -------------------------------------------------------------

RECENT_CHOICES = (0, 6, 12, 20)
# (key, label, narrowest card width before the grid drops a column)
CARD_SIZES = (('small', 'Small', 110), ('medium', 'Medium', 130), ('large', 'Large', 160))
DEFAULTS = {'order': [], 'groups': {}, 'hidden': [], 'intro': True, 'recent': 12,
            'card_size': 'medium'}


def defaults():
    """A fresh copy of DEFAULTS (its lists and dicts are never shared)."""
    return json.loads(json.dumps(DEFAULTS))


def right_kind(value, default):
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, type(default))


def load(path=SETTINGS_PATH):
    """Your settings over the defaults. A missing or unreadable file, or a
    value of the wrong kind, falls back to its default: the hub must open."""
    settings = defaults()
    try:
        with open(path, encoding='utf-8') as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return settings
    if not isinstance(stored, dict):
        return settings
    for key, default in DEFAULTS.items():
        if key in stored and right_kind(stored[key], default):
            settings[key] = stored[key]
    settings['order'] = [name for name in settings['order'] if isinstance(name, str)]
    settings['hidden'] = [name for name in settings['hidden'] if isinstance(name, str)]
    settings['groups'] = {name: group for name, group in settings['groups'].items()
                          if isinstance(name, str) and isinstance(group, str)}
    if settings['card_size'] not in [key for key, label, width in CARD_SIZES]:
        settings['card_size'] = DEFAULTS['card_size']
    return settings


def save(settings, path=SETTINGS_PATH):
    """Write settings whole: a temporary file, then os.replace."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(settings, handle, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(temporary, path)


def reset(path=SETTINGS_PATH):
    """The hub as it ships, saved over your settings. Returns them."""
    settings = defaults()
    save(settings, path)
    return settings


# --- The home view ------------------------------------------------------------

def arrange(cards, settings, include_hidden=False):
    """cards (dicts with 'name') in your order: the names you placed first,
    then the rest in their own order. Hidden cards are left out unless
    include_hidden."""
    by_name = {}
    for card in cards:
        by_name.setdefault(card['name'], card)
    ordered, placed = [], set()
    for name in settings['order']:
        if name in by_name and name not in placed:
            ordered.append(by_name[name])
            placed.add(name)
    ordered += [card for card in cards if card['name'] not in placed]
    if include_hidden:
        return ordered
    hidden = set(settings['hidden'])
    return [card for card in ordered if card['name'] not in hidden]


def swap(settings, cards, first, second):
    """Swap two cards. The whole order is written down, so the rest stay
    put when tools come and go."""
    names = [card['name'] for card in arrange(cards, settings, include_hidden=True)]
    if first in names and second in names:
        a, b = names.index(first), names.index(second)
        names[a], names[b] = names[b], names[a]
    settings['order'] = names
    return settings


def move(settings, name, group):
    """Put the tool named name into group ('' or None: the home view)."""
    settings['groups'][name] = group or ''
    return settings


def set_hidden(settings, name, hidden):
    names = [other for other in settings['hidden'] if other != name]
    if hidden:
        names.append(name)
    settings['hidden'] = names
    return settings


def card_width(settings):
    """The narrowest a tool card gets, from card_size."""
    for key, label, width in CARD_SIZES:
        if key == settings.get('card_size'):
            return width
    return dict((key, width) for key, label, width in CARD_SIZES)[DEFAULTS['card_size']]
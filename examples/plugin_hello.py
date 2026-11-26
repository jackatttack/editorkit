"""A Toolbox plugin in one file: the smallest working example.

A plugin is any module with a function that opens an editorkit window.
The Toolbox hub finds it through a small JSON card in
~/Documents/Toolbox/tools/. Run this script once: it writes that card (if
there is none yet) and opens the tool. Then open the hub: a Hello card is
there, no restart needed.

Copy this file to start your own tool: change the settings, then build
your pages in main(). The whole contract is in docs/PLUGINS.md.
"""

import json
import os

import editorkit as ek

# --- Settings: what the hub shows -------------------------------------------
NAME = 'Hello'
EMOJI = '👋'
WHAT = 'a plugin example'          # the short line under the card's name
ABOUT = 'The smallest Toolbox plugin: a window with one page.'
WINDOW_KEY = 'plugin_hello'        # same key, same window: a rerun replaces it

# --- Where cards live: the hub reads every .json in this folder -------------
DOCUMENTS = os.path.expanduser('~/Documents')
TOOLBOX_TOOLS = os.path.join(DOCUMENTS, 'Toolbox', 'tools')
CARD_PATH = os.path.join(TOOLBOX_TOOLS, 'plugin_hello.json')


def main():
    """Open the tool. The hub calls this when the card is tapped."""
    window = ek.Window(NAME, emoji=EMOJI, key=WINDOW_KEY)
    window.add_page('Hello', 'Hello from a plugin. Edit main() to build your tool.')
    window.show()
    return window


def card():
    """The card the hub reads.

    folder goes first on sys.path when the card is tapped, so module is
    just this file's name. A folder inside Documents is written relative to
    it, so the same card works on every device."""
    here = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.relpath(here, DOCUMENTS) if here.startswith(DOCUMENTS) else here
    return {
        'name': NAME,
        'emoji': EMOJI,
        'what': WHAT,
        'about': ABOUT,
        'folder': folder,
        'module': os.path.splitext(os.path.basename(__file__))[0],
        'function': 'main',
    }


def write_card():
    """Write the card when the Toolbox is installed and has none yet.

    Never overwrites: the card may have been moved into a group from the
    hub's Settings. Writes a temporary file first, so the hub never reads
    half a card. Returns True when it wrote one."""
    toolbox_installed = os.path.isdir(os.path.dirname(TOOLBOX_TOOLS))
    if not toolbox_installed or os.path.isfile(CARD_PATH):
        return False
    os.makedirs(TOOLBOX_TOOLS, exist_ok=True)
    temporary = CARD_PATH + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(card(), handle, indent=2, ensure_ascii=False)
    os.replace(temporary, CARD_PATH)
    return True


if __name__ == '__main__':
    if write_card():
        print('Card written: ' + CARD_PATH)
    main()

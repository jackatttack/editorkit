"""editorkit.web: web pages as tool surfaces, built for Pythonista.

editorkit puts windows over Pythonista; web pages are the best thing to
fill them. Pythonista's ui.WebView is the old UIWebView, with quirks that
cost real time to find (library/guides/web-views.md). This package holds
what makes a page feel native inside editorkit's windows:

    codeview     the page shell (fast taps, theme CSS) and section builders
    cards        the card kit: Page, headings, chips, buttons, card grids
    render       anything as HTML (text, rows, tables, pictures, errors)
    tapeview     the calculator tape page
    tiles        the web tiles: Code, Cards (the page-owned pinch), Feed, Tape
    touch        window.ekTouch on every page: taps and drags by element
    bridge       ekSend / tile.on_message, ekPatch / tile.patch, ekready
    preview      any page as a stand-alone HTML file, to test off the device
    assets       pictures and files inside a page (data URIs, read once)

    from editorkit.web import cards, tiles
    board = tiles.Cards(window, on_pick=picked)

The layering: editorkit's core never imports this package (checked by
tests/smoke_web_fence.py); this package may use the core (tiles.base,
stores, trace, files). The old paths (editorkit.codeview,
editorkit.tiles.Cards and the rest) still work as aliases until Toolbox
imports the new ones.
"""
from . import assets, bridge, cards, codeview, preview, render, tapeview, tiles
from .show import page_for_html
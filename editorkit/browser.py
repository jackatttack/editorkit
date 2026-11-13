"""The file browser (Pythonista's library panel)."""
from . import _app


@_app.on_main
def browser_visible():
    return bool(_app.root().masterVisible())


@_app.on_main
def toggle_browser():
    _app.root().toggleMaster()


def show_browser():
    if not browser_visible():
        toggle_browser()


def hide_browser():
    if browser_visible():
        toggle_browser()
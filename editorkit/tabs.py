"""Open tabs and files."""
import os
from ctypes import c_void_p

import editor as pythonista_editor
from objc_util import ObjCBlock, ObjCClass, sel

from . import _app


@_app.on_main
def open_tabs():
    """Paths of every open tab, in the tab bar's order."""
    detail = _app.root().detailViewController()
    try:
        paths = []
        for tab in detail.tabViewControllers():
            if tab.respondsToSelector_(sel('filePath')):
                path = tab.filePath()
                if path is not None:
                    paths.append(str(path))
        return paths
    except Exception:
        # Older route: a set, so no order.
        paths = detail.allOpenFilePaths()
        items = paths.allObjects() if paths.respondsToSelector_('allObjects') else paths
        return sorted(str(items.objectAtIndex_(i)) for i in range(items.count()))


@_app.on_main
def selected_tab():
    """Path of the tab showing now, or ''."""
    try:
        path = _app.root().detailViewController().selectedFilePath()
    except Exception:
        return ''
    return str(path) if path is not None else ''


def select_tab(path):
    """Switch to the tab showing path (opening one if needed), leaving the
    console where it is."""
    pythonista_editor.open_file(path, True)


def current_file():
    return pythonista_editor.get_path()


def open_file(path, new_tab=True):
    pythonista_editor.open_file(path, new_tab)


@_app.on_main
def tab_view_for(path):
    """Pythonista's view for the tab showing path (a PA2TabView), or None."""
    from . import tabpull               # tabpull imports tabs: import here, not at the top
    wanted = os.path.realpath(path)
    for view in tabpull.tab_views():
        found = tabpull.path_for(view)
        if found and os.path.realpath(found) == wanted:
            return view
    return None


@_app.on_main
def close_tab(path):
    """Close the tab showing path, as a tap on its close button would (so
    Pythonista saves and picks the next tab its own way). True when the tab
    was found."""
    tab = tab_view_for(path)
    if tab is None:
        return False
    button_class = ObjCClass('UIButton')
    for child in tab.subviews():
        if child.isKindOfClass_(button_class):
            child.sendActionsForControlEvents_(1 << 6)         # touch up inside
            return True
    return False


@_app.on_main
def tab_frame(path, view):
    """The tab's frame in view's coordinates (a ui.View or an ObjC view),
    as (x, y, width, height), or None when the tab is not on screen."""
    tab = tab_view_for(path)
    if tab is None:
        return None
    target = getattr(view, 'objc_instance', view)
    rect = tab.convertRect_toView_(tab.bounds(), target)
    return (rect.origin.x, rect.origin.y, rect.size.width, rect.size.height)


@_app.on_main
def new_tab_slot(view, width):
    """Where a newly opened tab lands (just after the last file tab, where
    the Console tab sits), in view's coordinates: (x, y, width, height),
    kept on screen when the row is scrolled. None with no tab row."""
    from . import tabpull
    shown = tabpull.tab_views()
    files = [tab for tab in shown if tabpull.tab_label(tab) != 'Console'] or shown
    if not files:
        return None
    target = getattr(view, 'objc_instance', view)
    last = files[-1]
    rect = last.convertRect_toView_(last.bounds(), target)
    x = rect.origin.x + rect.size.width + 4
    limit = target.bounds().size.width - width - 4
    return (max(4, min(x, limit)), rect.origin.y, width, rect.size.height)


@_app.on_main
def set_tab_alpha(path, alpha):
    tab = tab_view_for(path)
    if tab is not None:
        tab.setAlpha_(alpha)


# Blocks handed to UIKit must outlive their animation: keep the last few.
_animation_blocks = []


@_app.on_main
def fade_tab_in(path, seconds=0.35):
    """The tab fades in (a window landing in the tab row). True when found."""
    tab = tab_view_for(path)
    if tab is None:
        return False
    tab.setAlpha_(0.0)

    def change(_block):
        tab.setAlpha_(1.0)
    block = ObjCBlock(change, restype=None, argtypes=[c_void_p])
    _animation_blocks.append(block)
    del _animation_blocks[:-4]
    ObjCClass('UIView').animateWithDuration_animations_(seconds, block)
    return True
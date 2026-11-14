"""Uninstall Toolbox for Pythonista and the editorkit library.

Run this script. It takes Toolbox out of the wrench menu and moves what the
installer put in place into Documents/_to_delete. Nothing is deleted: empty
that folder yourself once you are sure.

    site-packages-3/editorkit, site-packages-3/editorkit_toolbox
    Documents/Toolbox (the lessons, the examples, your edits, this script)

Your saved data (snippets, window places, Packages' records) stays in
Documents/.editorkit unless MOVE_SAVED_DATA is True. Packages you installed
with 📦 Packages stay in site-packages-3: remove them in Packages first if
you want them gone too.
"""
import os
import shutil
import sys
import time

# --- Settings ------------------------------------------------------------------

MOVE_SAVED_DATA = False          # True: Documents/.editorkit goes to _to_delete too

DOCUMENTS = os.path.expanduser('~/Documents')
SITE_PACKAGES = os.path.join(DOCUMENTS, 'site-packages-3')
HOME = os.path.join(DOCUMENTS, 'Toolbox')
SAVED_DATA = os.path.join(DOCUMENTS, '.editorkit')
SET_ASIDE = os.path.join(DOCUMENTS, '_to_delete')
PACKAGES = ('editorkit', 'editorkit_toolbox')
LAUNCHER = os.path.join(HOME, 'Toolbox.py')


def set_aside(path):
    """Move path into Documents/_to_delete, stamped with the time."""
    os.makedirs(SET_ASIDE, exist_ok=True)
    moved = os.path.join(SET_ASIDE, '%s_%s' % (time.strftime('%Y%m%d_%H%M%S'),
                                               os.path.basename(path)))
    shutil.move(path, moved)
    return os.path.relpath(moved, DOCUMENTS)


def stop_and_unlist():
    """Close every window and take Toolbox out of the wrench menu, while
    editorkit is still there to do it."""
    try:
        import editorkit
        editorkit.close_windows(at_once=True)
        from editorkit import wrench
        if wrench.remove_wrench_action(LAUNCHER):
            print('  ✓ Toolbox is out of the wrench menu')
    except Exception as error:
        print('  ! could not tidy the wrench menu (%s): remove Toolbox there by hand' % error)


def forget_modules():
    for name in list(sys.modules):
        if name.split('.')[0] in PACKAGES:
            del sys.modules[name]


def main():
    stop_and_unlist()
    forget_modules()
    for package in PACKAGES:
        folder = os.path.join(SITE_PACKAGES, package)
        if os.path.isdir(folder):
            print('  ✓ %s moved to %s' % (package, set_aside(folder)))
    if MOVE_SAVED_DATA and os.path.isdir(SAVED_DATA):
        print('  ✓ saved data moved to %s' % set_aside(SAVED_DATA))
    if os.path.isdir(HOME):
        print('  ✓ Documents/Toolbox moved to %s' % set_aside(HOME))
    print('\nToolbox is uninstalled. Restart Pythonista to finish.')
    if not MOVE_SAVED_DATA:
        print('Your saved data is still in Documents/.editorkit.')


if __name__ == '__main__':
    main()
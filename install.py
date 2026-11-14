"""Install or update Toolbox for Pythonista and the editorkit library.

Run this script; run it again any time to update. It:
  - puts the editorkit library and the Toolbox app in site-packages-3,
  - makes Documents/Toolbox/ with the Toolbox launcher, examples and
    lessons,
  - adds Toolbox to the editor's wrench menu (once; reruns update it),
  - moves aside packages earlier releases installed and this one does not
    (RETIRED).
Documents/Toolbox/Uninstall.py takes it all out again.

Run beside the packages (a downloaded or staged copy of the repo), it
installs from there; otherwise it downloads the repo from GitHub.
Your settings and saved data are kept: they live elsewhere. Lessons and
examples you changed are kept too: an update moves your version to
Documents/_to_delete before the new one lands (update_learn_folder).
"""
import filecmp
import io
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

REPO = 'jackatttack/editorkit'
BRANCH = 'main'
ZIP_URL = 'https://github.com/%s/archive/refs/heads/%s.zip' % (REPO, BRANCH)
DOCUMENTS = os.path.expanduser('~/Documents')
SITE_PACKAGES = os.path.join(DOCUMENTS, 'site-packages-3')
HOME = os.path.join(DOCUMENTS, 'Toolbox')
PACKAGES = ('editorkit', 'editorkit_toolbox')
FOLDERS = ('examples', 'lessons')
LAUNCHER = 'Toolbox.py'
UNINSTALLER = 'Uninstall.py'
# Packages earlier releases installed and this one does not, by the files
# that prove a folder is ours: moved to _to_delete on update.
RETIRED = {'codesense': ('assist.py', 'context.py', 'units.py', 'timing.py')}
WRENCH_TITLE = 'Toolbox'
WRENCH_ICON = 'Primaries_Home'
WRENCH_COLOUR = '#F26EFF'
LEARN_FOLDERS = ('examples', 'lessons')     # yours to change: updated with care
ORIGINALS = os.path.join(HOME, '.originals')   # the release's untouched copies (Learn's ♻️ Restore)
SET_ASIDE = os.path.join(DOCUMENTS, '_to_delete')


def here():
    path = globals().get('__file__') or ''
    return os.path.dirname(os.path.abspath(path)) if path else os.getcwd()


def has_packages(folder):
    return all(os.path.isdir(os.path.join(folder, name)) for name in PACKAGES)


def source_folder():
    """(folder holding the repo's files, temporary folder to remove or None)."""
    local = here()
    if has_packages(local):
        print('Installing from %s' % local)
        return local, None
    print('Downloading %s ...' % REPO)
    data = urllib.request.urlopen(ZIP_URL, timeout=90).read()
    temp = tempfile.mkdtemp(prefix='toolbox_')
    zipfile.ZipFile(io.BytesIO(data)).extractall(temp)
    for name in os.listdir(temp):
        candidate = os.path.join(temp, name)
        if os.path.isdir(candidate) and has_packages(candidate):
            return candidate, temp
    raise RuntimeError('The download did not contain %s' % ', '.join(PACKAGES))


def replace_tree(source, target):
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.git'))


def same_file(first, second):
    return (os.path.isfile(first) and os.path.isfile(second)
            and filecmp.cmp(first, second, shallow=False))


def set_aside(path):
    """Move path into Documents/_to_delete, stamped with the time: never deleted."""
    os.makedirs(SET_ASIDE, exist_ok=True)
    moved = os.path.join(SET_ASIDE, '%s_%s' % (time.strftime('%Y%m%d_%H%M%S'),
                                               os.path.basename(path)))
    shutil.move(path, moved)
    return moved


def retire_old_packages():
    """Move packages earlier releases installed, and this one does not, into
    Documents/_to_delete. Only a folder holding all of that package's own
    files counts as ours. Returns where they went."""
    moved = []
    for name, own_files in sorted(RETIRED.items()):
        folder = os.path.join(SITE_PACKAGES, name)
        if os.path.isdir(folder) and all(os.path.isfile(os.path.join(folder, own))
                                         for own in own_files):
            moved.append(set_aside(folder))
    return moved


def update_learn_folder(source, folder):
    """Bring Toolbox/<folder> up to date without losing anything you wrote.

    Every file in the release arrives. One you changed (it differs from the
    last release's untouched copy) is moved to Documents/_to_delete first. A
    file the release dropped goes only if you never changed it. Files you
    added are left alone. Then .originals/<folder> holds this release's
    untouched copies, for the next update and for Learn's ♻️ Restore.
    Returns the paths of your versions that were set aside."""
    installed_folder = os.path.join(HOME, folder)
    old_originals = os.path.join(ORIGINALS, folder)
    os.makedirs(installed_folder, exist_ok=True)
    new_names = set(name for name in os.listdir(source)
                    if os.path.isfile(os.path.join(source, name)))
    kept = []
    for name in sorted(new_names):
        new = os.path.join(source, name)
        installed = os.path.join(installed_folder, name)
        if os.path.exists(installed) and not same_file(installed, new):
            if not same_file(installed, os.path.join(old_originals, name)):
                kept.append(set_aside(installed))
        shutil.copy2(new, installed)
    if os.path.isdir(old_originals):
        for name in os.listdir(old_originals):
            installed = os.path.join(installed_folder, name)
            if name not in new_names and same_file(installed, os.path.join(old_originals, name)):
                os.remove(installed)
    replace_tree(source, os.path.join(ORIGINALS, folder))
    return kept


def forget_modules():
    """Drop loaded copies, so the fresh install is what imports next."""
    for name in list(sys.modules):
        if any(name == package or name.startswith(package + '.') for package in PACKAGES):
            del sys.modules[name]


def main():
    root, temp = source_folder()
    try:
        os.makedirs(SITE_PACKAGES, exist_ok=True)
        for path in retire_old_packages():
            print('  ↪ an older package moved to %s' % os.path.relpath(path, DOCUMENTS))
        for package in PACKAGES:
            replace_tree(os.path.join(root, package), os.path.join(SITE_PACKAGES, package))
            print('  ✓ %s' % package)
        os.makedirs(HOME, exist_ok=True)
        shutil.copy2(os.path.join(root, 'launchers', LAUNCHER), os.path.join(HOME, LAUNCHER))
        print('  ✓ Toolbox/%s' % LAUNCHER)
        shutil.copy2(os.path.join(root, 'launchers', UNINSTALLER), os.path.join(HOME, UNINSTALLER))
        print('  ✓ Toolbox/%s' % UNINSTALLER)
        for folder in FOLDERS:
            source = os.path.join(root, folder)
            if not os.path.isdir(source):
                continue
            if folder in LEARN_FOLDERS:
                for path in update_learn_folder(source, folder):
                    print('  ↪ your version kept in %s' % os.path.relpath(path, DOCUMENTS))
            else:
                replace_tree(source, os.path.join(HOME, folder))
            print('  ✓ Toolbox/%s' % folder)
        forget_modules()
        import editorkit
        from editorkit import wrench
        wrench.add_wrench_action(os.path.join(HOME, LAUNCHER), WRENCH_TITLE,
                                 icon=WRENCH_ICON, colour=WRENCH_COLOUR)
        print('  ✓ wrench menu: %s' % WRENCH_TITLE)
        print('\nToolbox %s is ready: tap the wrench, then %s.'
              % (getattr(editorkit, '__version__', ''), WRENCH_TITLE))
    finally:
        if temp:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == '__main__':      # the README's bootstrap runs it as __main__ too
    main()
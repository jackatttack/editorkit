"""Install or update Toolbox for Pythonista and the editorkit library.

Run this script; run it again any time to update. It:
  - puts the editorkit library, the Toolbox app and codesense (the code
    analysis behind Lens) in site-packages-3,
  - makes Documents/Toolbox/ with the Toolbox launcher, examples, lessons
    and docs,
  - adds Toolbox to the editor's wrench menu (once; reruns update it).

Run beside the packages (a downloaded or staged copy of the repo), it
installs from there; otherwise it downloads the repo from GitHub.
Your settings and saved data are kept: they live elsewhere.
"""
import io
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

REPO = 'jackatttack/editorkit'
BRANCH = 'main'
ZIP_URL = 'https://github.com/%s/archive/refs/heads/%s.zip' % (REPO, BRANCH)
DOCUMENTS = os.path.expanduser('~/Documents')
SITE_PACKAGES = os.path.join(DOCUMENTS, 'site-packages-3')
HOME = os.path.join(DOCUMENTS, 'Toolbox')
PACKAGES = ('editorkit', 'editorkit_toolbox', 'codesense')
FOLDERS = ('examples', 'lessons', 'docs')
LAUNCHER = 'Toolbox.py'
WRENCH_TITLE = 'Toolbox'
WRENCH_ICON = 'Primaries_Home'
WRENCH_COLOUR = '#F26EFF'


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


def forget_modules():
    """Drop loaded copies, so the fresh install is what imports next."""
    for name in list(sys.modules):
        if any(name == package or name.startswith(package + '.') for package in PACKAGES):
            del sys.modules[name]


def main():
    root, temp = source_folder()
    try:
        os.makedirs(SITE_PACKAGES, exist_ok=True)
        for package in PACKAGES:
            replace_tree(os.path.join(root, package), os.path.join(SITE_PACKAGES, package))
            print('  ✓ %s' % package)
        os.makedirs(HOME, exist_ok=True)
        shutil.copy2(os.path.join(root, 'launchers', LAUNCHER), os.path.join(HOME, LAUNCHER))
        print('  ✓ Toolbox/%s' % LAUNCHER)
        for folder in FOLDERS:
            source = os.path.join(root, folder)
            if os.path.isdir(source):
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


main()
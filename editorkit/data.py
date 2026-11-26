"""Shared data files: this device's library first, iCloud second, never waiting.

Role: gather, store · Part of: editorkit/data

    import editorkit as ek
    path = ek.data.find('datasets/pokemon.csv')     # a path, or None
    ek.data.status('datasets/pokemon.csv')           # 'here', 'icloud', 'not downloaded', 'missing'
    ek.data.copy_to_device()                         # iCloud library/ -> this device (run by hand)

The convention (2026-11-26, from mathskit's Charts): data shared between
devices lives in Pythonista's iCloud Drive folder under library/. Each
device keeps its own copy in Documents/library/, made by copy_to_device()
(or the stand-alone library/copy_to_this_device.py kept in iCloud), and
tools read that copy. A tool never waits on iCloud: reading or downloading
iCloud files inside a running tool froze Pythonista on the iPad. find()
falls back to an iCloud file only when it is already downloaded.

The iCloud folder is asked of iOS (objc_util), never written in, so no
device path ships. Off Pythonista (PythonIDE, Juno, a desktop) there is no
iCloud folder and only Documents/library is used. Every function takes
roots=(local, icloud) for tests.
"""
import os
import shutil
import time

# ---- Settings (editable) ---------------------------------------------------

LIBRARY = 'library'                      # the shared folder's name, in both places
DOWNLOAD_WAIT_SECONDS = 180              # copy_to_device: longest wait for iCloud in all
SKIP_NAMES = {'__pycache__', '.DS_Store', 'copy_to_this_device.py'}

# ---- Where the libraries are ----------------------------------------------------

_icloud = []                             # the iCloud Documents folder, once asked ('' for none)


def local_library():
    """This device's Documents/library."""
    return os.path.join(os.path.expanduser('~'), 'Documents', LIBRARY)


def icloud_documents():
    """Pythonista's iCloud Drive Documents folder, asked of iOS, or ''."""
    if not _icloud:
        found = ''
        try:
            from objc_util import ObjCClass
            container = ObjCClass('NSFileManager').defaultManager().URLForUbiquityContainerIdentifier_(None)
            if container is not None:
                found = os.path.join(str(container.path()), 'Documents')
        except Exception:
            found = ''
        _icloud.append(found if found and os.path.isdir(found) else '')
    return _icloud[0]


def icloud_library():
    """library/ in iCloud Drive, or '' where there is no iCloud folder."""
    cloud = icloud_documents()
    return os.path.join(cloud, LIBRARY) if cloud else ''


def default_roots():
    return local_library(), icloud_library()


def placeholder(path):
    """iCloud's stand-in for a file not downloaded yet: .name.icloud beside it."""
    folder, name = os.path.split(path)
    return os.path.join(folder, '.%s.icloud' % name)


# ---- Finding ------------------------------------------------------------------------


def find(relative, roots=None):
    """The path to library/<relative> on this device, else in iCloud when
    already downloaded, else None. Never waits."""
    local, cloud = roots or default_roots()
    for root in (local, cloud):
        if root:
            path = os.path.join(root, relative)
            if os.path.exists(path):
                return path
    return None


def status(relative, roots=None):
    """'here' (on this device), 'icloud' (only in iCloud, downloaded),
    'not downloaded' (iCloud has it, this device does not yet) or 'missing'."""
    local, cloud = roots or default_roots()
    if local and os.path.exists(os.path.join(local, relative)):
        return 'here'
    if cloud and os.path.exists(os.path.join(cloud, relative)):
        return 'icloud'
    if cloud and os.path.exists(placeholder(os.path.join(cloud, relative))):
        return 'not downloaded'
    return 'missing'


def advice(relative, roots=None):
    """One sentence for a person when relative cannot be read here, or ''."""
    state = status(relative, roots)
    if state == 'not downloaded':
        return ('%s is in iCloud but not on this device yet. Run library/copy_to_this_device.py '
                '(in iCloud Drive, Pythonista 3) once with a connection.' % relative)
    if state == 'missing':
        return ('No %s. Put it in library/ in Pythonista\'s iCloud Drive folder, then run '
                'library/copy_to_this_device.py on each device.' % relative)
    return ''


# ---- Copying iCloud's library to this device (run by hand) -----------------------------


def request_download(path):
    """Ask iCloud to bring path down to this device (Pythonista only)."""
    try:
        from objc_util import ObjCClass, nsurl
        ObjCClass('NSFileManager').defaultManager().startDownloadingUbiquitousItemAtURL_error_(nsurl(path), None)
        return True
    except Exception:
        return False


def cloud_files(cloud):
    """(relative path, downloaded) for every file under the iCloud library."""
    for folder, folders, names in os.walk(cloud):
        folders[:] = [name for name in folders if name not in SKIP_NAMES and not name.startswith('.')]
        for name in names:
            if name in SKIP_NAMES:
                continue
            if name.startswith('.') and name.endswith('.icloud'):
                yield os.path.relpath(os.path.join(folder, name[1:-len('.icloud')]), cloud), False
            elif not name.startswith('.'):
                yield os.path.relpath(os.path.join(folder, name), cloud), True


def needs_copy(source, target):
    if not os.path.isfile(target):
        return True
    a, b = os.stat(source), os.stat(target)
    return a.st_size != b.st_size or a.st_mtime > b.st_mtime + 1


def copy_to_device(roots=None, wait_seconds=DOWNLOAD_WAIT_SECONDS, say=print):
    """Mirror the iCloud library into this device's library: download what
    iCloud has not brought down (waiting up to wait_seconds), copy files that
    are new or changed, never delete. Blocks: run it by hand, never inside a
    tool's page. Returns {'copied', 'same', 'missing': [relative, ...]}."""
    local, cloud = roots or default_roots()
    if not cloud or not os.path.isdir(cloud):
        raise RuntimeError('No iCloud library here (iCloud Drive > Pythonista 3 > library).')
    files = list(cloud_files(cloud))
    waiting = [relative for relative, downloaded in files if not downloaded]
    if waiting:
        say('Asking iCloud for %d file(s) not on this device yet...' % len(waiting))
        for relative in waiting:
            request_download(os.path.join(cloud, relative))
        deadline = time.time() + wait_seconds
        while waiting and time.time() < deadline:
            time.sleep(1)
            waiting = [relative for relative in waiting if not os.path.isfile(os.path.join(cloud, relative))]
    missing = set(waiting)
    copied = same = 0
    for relative, _ in files:
        if relative in missing:
            continue
        source, target = os.path.join(cloud, relative), os.path.join(local, relative)
        if needs_copy(source, target):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        else:
            same += 1
    say('Copied %d, already up to date %d, into %s' % (copied, same, local))
    if missing:
        say('iCloud did not bring down %d file(s) in time: run this again with a connection.' % len(missing))
    return {'copied': copied, 'same': same, 'missing': sorted(missing)}
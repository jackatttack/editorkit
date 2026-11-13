"""Breadcrumbs: a small rolling log for finding what happened before a freeze.

    from editorkit import trace
    trace.note('pair summon')

Each note is one line, written and flushed at once, so a freeze or a
force-quit keeps everything up to the last note. M or T marks the main
thread or another. The log rolls over at MAX_BYTES (the previous one is
kept as .1). After a freeze: READ scratch/editorkit_trace.log.
"""
import os
import threading
import time


# --- Settings -------------------------------------------------------------

ENABLED = False              # True while hunting a freeze
LOG_PATH = os.path.expanduser('~/Documents/scratch/editorkit_trace.log')
MAX_BYTES = 200000


def note(*parts):
    if not ENABLED:
        return
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_BYTES:
            os.replace(LOG_PATH, LOG_PATH + '.1')
        thread = 'M' if threading.current_thread() is threading.main_thread() else 'T'
        line = '%s %s %s\n' % (time.strftime('%H:%M:%S'), thread,
                               ' '.join(str(part) for part in parts))
        with open(LOG_PATH, 'a', encoding='utf-8') as handle:
            handle.write(line)
    except Exception:
        pass
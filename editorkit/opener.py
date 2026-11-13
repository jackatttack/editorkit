"""Opener: open a file at a line and select there, across a tab switch.

    opener = ek.Opener(window)              # ticks itself on the window's clock
    opener.go(path, 12, start=4, end=9)     # opens (or switches to) its tab

A new tab can take a moment to show its text, so go() selects at once when
it can, and otherwise tick() selects once the tab's line matches the file
on disk (or SETTLE_SECONDS pass: unsaved edits). The line is then revealed
near the top of the code, clear of a window resting lower down.
"""
import os
import time

from . import files
from .script import reveal, select, text
from .tabs import current_file, open_file


# --- Settings -------------------------------------------------------------

PICK_TIMEOUT = 3.0           # how long to wait for the file's tab to show
SETTLE_SECONDS = 0.6         # how long to wait for that tab's text to match
REVEAL_TOP = 60              # where the line lands: points below the code's top


def same_file(first, second):
    return bool(first) and os.path.realpath(first) == os.path.realpath(second)


class Opener:

    def __init__(self, window=None, reveal_top=REVEAL_TOP):
        self.reveal_top = reveal_top
        self.wanted = None           # (path, line, start, end, line text on disk)
        self.since = 0.0
        if window is not None:
            window.every(self.tick)  # finishes on the window's clock

    def go(self, path, line=1, start=0, end=0):
        """Open path (or switch to its tab) and select start..end (columns)
        on line (1-based); start == end puts the cursor there."""
        disk = (files.read_text(path) or '').splitlines()
        expected = disk[line - 1].rstrip() if 1 <= line <= len(disk) else None
        if not same_file(current_file(), path):
            open_file(path)
        self.wanted = (path, line, start, end, expected)
        self.since = time.time()
        self.tick()

    def tick(self, now=None):
        if self.wanted is None:
            return
        path, line, start, end, expected = self.wanted
        waited = time.time() - self.since
        if not same_file(current_file(), path):
            if waited > PICK_TIMEOUT:
                self.wanted = None
            return
        lines = text().splitlines(True)
        settled = line <= len(lines) and lines[line - 1].rstrip() == expected
        if not settled and waited < SETTLE_SECONDS:
            return
        self.wanted = None
        if line > len(lines):
            return
        line_start = sum(len(part) for part in lines[:line - 1])
        select(line_start + start, line_start + end)
        reveal(line_start + start, top=self.reveal_top)
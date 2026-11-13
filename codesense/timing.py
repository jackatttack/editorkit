"""A ledger of how long each analysis step takes, so slowness is visible
instead of just felt.

Each step keeps its count, last, worst and mean time, and the median of its
recent runs. Judge budgets by the median: on a phone one garbage collection
or a busy main thread can make a single run look ten times slower.
"""
import time
from collections import deque
from contextlib import contextmanager

RECENT_RUNS = 100           # samples kept per step for the median


class Ledger(object):
    def __init__(self):
        self.steps = {}

    def record(self, step, milliseconds):
        entry = self.steps.get(step)
        if entry is None:
            entry = self.steps[step] = {'count': 0, 'last': 0.0, 'worst': 0.0,
                                        'total': 0.0, 'recent': deque(maxlen=RECENT_RUNS)}
        entry['count'] += 1
        entry['last'] = milliseconds
        entry['worst'] = max(entry['worst'], milliseconds)
        entry['total'] += milliseconds
        entry['recent'].append(milliseconds)

    def median(self, step):
        recent = sorted(self.steps[step]['recent'])
        middle = len(recent) // 2
        if len(recent) % 2:
            return recent[middle]
        return (recent[middle - 1] + recent[middle]) / 2.0

    @contextmanager
    def timed(self, step):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record(step, (time.perf_counter() - start) * 1000)

    def report(self):
        """One line per step, alphabetical."""
        lines = []
        for step in sorted(self.steps):
            entry = self.steps[step]
            lines.append('%-14s median %7.2f ms  last %7.2f  worst %7.2f  mean %7.2f  (%d runs)'
                         % (step, self.median(step), entry['last'], entry['worst'],
                            entry['total'] / entry['count'], entry['count']))
        return lines


@contextmanager
def _untimed():
    yield


def maybe_timed(ledger, step):
    """ledger.timed(step), or nothing when no ledger was given."""
    return ledger.timed(step) if ledger is not None else _untimed()
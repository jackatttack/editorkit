"""Job: background work, handed over on a window's clock.

    job = ek.Job(window, work, on_items=shown, on_done=finished, on_error=failed)
    job.start(term, folder)          # runs work(run, term, folder) on a thread
    job.start_later(0.35, term)      # the same after a quiet spell (typing)
    job.cancel()

    def work(run, term, folder):
        for item in ...:
            if run.cancelled:        # a newer start() or cancel() happened
                return
            run.put(item)
        return result                # on_done(result)

The work never touches ui. Items, the result and any error (on_error gets
the traceback text) arrive on the main thread from the window's clock,
items batched per beat (on_items(list)). A new start() cancels the run
before it, and a cancelled run's late items are dropped, so a stale scan
never shows. Only needs window.every, so tests can pass a stand-in.
"""
import threading
import time
import traceback


class Run:
    """One start() of a Job, as its work sees it."""

    def __init__(self, job, generation):
        self.job = job
        self.generation = generation

    @property
    def cancelled(self):
        return self.generation != self.job.generation

    def put(self, item):
        self.job._post(self.generation, 'item', item)


class Job:

    def __init__(self, window, work, on_items=None, on_done=None, on_error=None):
        self.work = work
        self.on_items = on_items
        self.on_done = on_done
        self.on_error = on_error
        self.generation = 0
        self.running = False
        self.due = None              # (time, args) of a start_later
        self.queue = []              # (generation, kind, value) from threads
        self.lock = threading.Lock()
        window.every(self.tick)

    def start(self, *args):
        """Cancel any run, then run work(run, *args) on a thread."""
        self.due = None
        self.generation += 1
        run = Run(self, self.generation)
        self.running = True

        def main():
            try:
                self._post(run.generation, 'done', self.work(run, *args))
            except Exception:
                self._post(run.generation, 'error', traceback.format_exc())

        threading.Thread(target=main, daemon=True).start()
        return run

    def start_later(self, seconds, *args):
        """start(*args) after seconds; a newer call moves it on (debounce)."""
        self.due = (time.time() + seconds, args)

    def cancel(self):
        self.due = None
        self.generation += 1
        self.running = False

    def _post(self, generation, kind, value):
        with self.lock:
            self.queue.append((generation, kind, value))

    def tick(self, now=None):
        if self.due is not None and time.time() >= self.due[0]:
            args = self.due[1]
            self.start(*args)
        with self.lock:
            batch, self.queue = self.queue, []
        current = [entry for entry in batch if entry[0] == self.generation]
        items = [value for _, kind, value in current if kind == 'item']
        if items and self.on_items:
            self.on_items(items)
        for _, kind, value in current:
            if kind == 'done':
                self.running = False
                if self.on_done:
                    self.on_done(value)
            elif kind == 'error':
                self.running = False
                if self.on_error:
                    self.on_error(value)
                else:
                    print('editorkit job failed:\n%s' % value)
"""The timeline: steps booked for later and run by the windows clock, so a
move with several steps needs no completion callbacks and no ui.delay
(pythonista-ui-stability guide). Pure Python: no ui, headless-testable."""
import time


class Timeline:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.steps = []               # (due time, name, step, owner)
        self.busy_until = {}          # id(owner) -> time its current move ends

    def book(self, delay, name, step, owner=None):
        self.steps.append((self.clock() + delay, name, step, owner))

    def due(self):
        """Take out and return the steps whose time has come, earliest first."""
        now = self.clock()
        ready = sorted((step for step in self.steps if step[0] <= now), key=lambda step: step[0])
        if ready:
            self.steps = [step for step in self.steps if step[0] > now]
        return ready

    def cancel(self, owner):
        self.steps = [step for step in self.steps if step[3] is not owner]
        self.busy_until.pop(id(owner), None)

    def hold(self, owner, seconds):
        """owner is mid-move for seconds: its public moves are refused till then."""
        self.busy_until[id(owner)] = self.clock() + seconds

    def busy(self, owner):
        return self.clock() < self.busy_until.get(id(owner), 0.0)
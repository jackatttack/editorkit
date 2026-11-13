"""A stopwatch: a small live tool to keep over your code, dock in the
keyboard's place (⌨) or send to the console (>_).

Shows: a ui.View subclass as a page, with its own update() clock and
buttons. Everything its methods need is kept on self, because this
script's globals are cleared when it ends.
"""
import time


import ui

import editorkit as ek


class Stopwatch(ui.View):
    def __init__(self, window, clock=time.time):
        self.clock = clock                 # kept on self: globals are cleared later
        self.started = None                # clock time when it was started, while running
        self.elapsed = 0.0                 # seconds from earlier runs
        palette = window.palette
        self.display = ui.Label(font=('Menlo', 40), alignment=ui.ALIGN_CENTER,
                                text_color=palette.text)
        self.display.touch_enabled = False
        self.add_subview(self.display)
        self.start_button = self.make_button('Start', self.toggle, palette)
        self.reset_button = self.make_button('Reset', self.reset, palette)
        self.update_interval = 0.05
        self.show_time()

    def make_button(self, title, action, palette):
        button = ui.Button(title=title, font=('<system-bold>', 16))
        button.tint_color = palette.accent
        button.background_color = palette.background
        button.corner_radius = 8
        button.action = action
        self.add_subview(button)
        return button

    def seconds(self):
        running = self.clock() - self.started if self.started is not None else 0.0
        return self.elapsed + running

    def show_time(self):
        total = self.seconds()
        self.display.text = '%02d:%05.2f' % (int(total // 60), total % 60)

    def toggle(self, sender):
        if self.started is None:
            self.started = self.clock()
            sender.title = 'Stop'
        else:
            self.elapsed = self.seconds()
            self.started = None
            sender.title = 'Start'
        self.show_time()

    def reset(self, sender):
        self.started = None
        self.elapsed = 0.0
        self.start_button.title = 'Start'
        self.show_time()

    def update(self):
        if self.started is not None and self.objc_instance.superview() is not None:
            self.show_time()

    def layout(self):
        width, height = self.width, self.height
        self.display.frame = (0, 0, width, max(0, height - 48))
        half = (width - 8) / 2.0
        self.start_button.frame = (0, height - 40, half, 40)
        self.reset_button.frame = (half + 8, height - 40, half, 40)


stopwatch = ek.Window('Stopwatch', emoji='⏱', size=(260, 200), min_size=(180, 150))
stopwatch.add_page('Time', Stopwatch)
stopwatch.show()
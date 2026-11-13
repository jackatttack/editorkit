r"""The big snippet library that comes with Toolbox: Pythonista's own
modules, editorkit, everyday Python, web and data, maths and plots, and
whole-file templates. Snippets offers each one once (snippets.seeds_to_add),
so new ones reach libraries that already exist, and one you delete stays
deleted.

Edit freely. SEEDS is [(group, colour, [(title, text), ...])]; snippet()
dedents a block, so write each one as it should read. ${cursor} marks where
the cursor lands; ${date}, ${time} and ${clipboard} are filled in when typed.
tests/smoke_snippet_library.py parses every snippet as Python.
"""
import textwrap


def snippet(title, text):
    return title, textwrap.dedent(text).strip('\n') + '\n'


PYTHONISTA = ('Pythonista', '#8E6CEF', [
    snippet('View with layout and touch', r'''
        import ui


        class Board(ui.View):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.background_color = 'white'
                self.label = ui.Label(text='Tap me', alignment=ui.ALIGN_CENTER)
                self.add_subview(self.label)

            def layout(self):
                # Runs whenever the size changes: place subviews from self.bounds.
                self.label.frame = self.bounds

            def touch_began(self, touch):
                x, y = touch.location
                self.label.text = 'Tapped at %.0f, %.0f' % (x, y)
                ${cursor}


        Board(name='Board').present('fullscreen')
        '''),
    snippet('Draw with ui.Path', r'''
        import ui


        class Canvas(ui.View):
            def draw(self):
                # Runs when the view needs painting; set_needs_display() asks again.
                ui.set_color('#E8365A')
                ui.Path.oval(20, 20, 100, 100).fill()
                ui.set_color('black')
                square = ui.Path.rect(140, 20, 100, 100)
                square.line_width = 3
                square.stroke()
                ${cursor}


        Canvas(background_color='white').present('sheet')
        '''),
    snippet('Button with an action', r'''
        def tapped(sender):
            ${cursor}print('Tapped', sender.title)


        button = ui.Button(title='Go', action=tapped)
        button.frame = (20, 20, 120, 44)
        button.background_color = '#5FD3BC'
        button.tint_color = 'white'
        button.corner_radius = 8
        view.add_subview(button)
        '''),
    snippet('Table of items', r'''
        import ui

        items = ['Apples', 'Pears', 'Lemons']
        source = ui.ListDataSource(items)


        def picked(source):
            ${cursor}print(source.items[source.selected_row])


        source.action = picked
        table = ui.TableView(data_source=source, delegate=source, name='Fruit')
        table.present('sheet')
        '''),
    snippet('Text field that reacts', r'''
        import ui


        class FieldDelegate:
            def textfield_did_change(self, textfield):
                ${cursor}print(textfield.text)

            def textfield_should_return(self, textfield):
                textfield.end_editing()
                return True


        field = ui.TextField(frame=(20, 20, 280, 36), placeholder='Type here')
        field.delegate = FieldDelegate()
        '''),
    snippet('Run later (ui.delay)', r'''
        def later():
            ${cursor}print('half a second later, on the main thread')


        ui.delay(later, 0.5)          # ui.cancel_delays() cancels every pending one
        '''),
    snippet('Slow work from a button', r'''
        @ui.in_background
        def tapped(sender):
            # Off the main thread: slow work and console dialogs are fine here.
            ${cursor}pass
        '''),
    snippet('Load a .pyui view', r'''
        import ui

        view = ui.load_view('${cursor}MyView')     # MyView.pyui beside this script
        view.present('sheet')
        '''),
    snippet('Alert with buttons', r'''
        import console

        try:
            choice = console.alert('${cursor}Title', 'Message', 'Yes', 'No')
        except KeyboardInterrupt:
            choice = None                  # Cancel raises KeyboardInterrupt
        if choice == 1:
            print('Yes')
        '''),
    snippet('Ask for some text', r'''
        import console

        try:
            name = console.input_alert('${cursor}Name', 'What should it be called?', 'untitled', 'OK')
        except KeyboardInterrupt:
            name = None                    # cancelled
        '''),
    snippet('Form of settings', r'''
        import dialogs

        fields = [{'type': 'text', 'key': 'name', 'title': 'Name'},
                  {'type': 'switch', 'key': 'loud', 'title': 'Loud', 'value': False},
                  {'type': 'number', 'key': 'count', 'title': 'Count'}]
        answers = dialogs.form_dialog('${cursor}Settings', fields)
        if answers is not None:            # None when cancelled
            print(answers['name'], answers['loud'], answers['count'])
        '''),
    snippet('Pick from a list', r'''
        import dialogs

        choice = dialogs.list_dialog('${cursor}Pick one', ['Small', 'Medium', 'Large'])
        if choice is not None:
            print(choice)
        '''),
    snippet('Quick message (HUD)', r'''
        import console

        console.hud_alert('${cursor}Saved', 'success', 1.0)     # or 'error'
        '''),
    snippet('Share text out', r'''
        import dialogs

        dialogs.share_text(${cursor}'Text to share')
        '''),
    snippet('Pick a photo', r'''
        import photos

        asset = photos.pick_asset()
        if asset is not None:
            image = asset.get_image()      # a PIL image
            ${cursor}
        '''),
    snippet('Play a sound', r'''
        import sound

        sound.play_effect('${cursor}arcade:Coin_1')
        '''),
    snippet('Speak', r'''
        import speech

        speech.say('${cursor}Hello there', 'en-GB')
        '''),
    snippet('Keychain password', r'''
        import keychain

        keychain.set_password('${cursor}my_service', 'me', 'secret')
        password = keychain.get_password('my_service', 'me')
        '''),
    snippet('Where am I (location)', r'''
        import location

        location.start_updates()
        place = location.get_location()    # latitude, longitude, altitude, ...
        location.stop_updates()
        ${cursor}
        '''),
    snippet('Device tilt (motion)', r'''
        import time

        import motion

        motion.start_updates()
        time.sleep(0.2)                    # give the sensors a moment
        roll, pitch, yaw = motion.get_attitude()
        motion.stop_updates()
        ${cursor}
        '''),
    snippet('Reminder notification', r'''
        import notification

        notification.schedule('${cursor}Time to stretch', delay=20 * 60)
        '''),
    snippet('Open a URL or app', r'''
        import webbrowser
        from urllib.parse import quote

        webbrowser.open('${cursor}https://omz-software.com/pythonista/docs/')
        webbrowser.open('shortcuts://run-shortcut?name=' + quote('My Shortcut'))
        '''),
    snippet('Change the open script (editor)', r'''
        import editor

        text = editor.get_text()
        start, end = editor.get_selection()
        editor.replace_text(start, end, text[start:end].upper())
        ${cursor}
        '''),
    snippet('Script arguments', r'''
        import sys

        arguments = sys.argv[1:]           # set them with a long press on ▶
        ${cursor}
        '''),
    snippet('Objective-C on the main thread', r'''
        from objc_util import ObjCClass, on_main_thread


        @on_main_thread
        def set_brightness(value):
            ObjCClass('UIScreen').mainScreen().setBrightness_(${cursor}value)
        '''),
])


EDITORKIT = ('editorkit', '#F26EFF', [
    snippet('Tool skeleton', r'''
        """${cursor}My tool: what it does, in one line."""


        def main():
            # Pythonista clears a script's names when it ends, but windows live
            # on: everything the callbacks use is local to main(), so they keep it.
            import editorkit as ek
            from editorkit.web import cards
            from editorkit.web import tiles as web_tiles

            window = ek.Window('My tool', emoji='🛠', key='my-tool')
            board = web_tiles.Cards(window, on_pick=lambda item: print(item), zoom_key='my-tool')
            window.add_page('Main', board)
            page = cards.Page()
            page.heading('Hello')
            page.grid([cards.Card('One', item=1), cards.Card('Two', item=2)])
            board.show(page)
            window.show()


        main()
        '''),
    snippet('Show anything in a window', r'''
        import editorkit as ek

        ek.show(${cursor}'Hello', title='Result', key='result')   # text, HTML, PIL image, figure
        '''),
    snippet('Window with pages', r'''
        window = ek.Window('${cursor}Notes', emoji='📝', key='notes')
        window.add_page('Today', 'Plain text')
        window.add_page('HTML', '<h2>Hello</h2><p>Takes the theme colours.</p>')
        window.show()
        '''),
    snippet('Header button', r'''
        def added(window):
            ${cursor}window.set_title('Added')


        window.add_button('＋', added, name='add')
        '''),
    snippet('Page of cards', r'''
        page = cards.Page()
        page.heading('${cursor}Things')
        page.note('Tap one.')
        page.grid([cards.Card(name, item=name, body=cards.text('about ' + name))
                   for name in ('one', 'two', 'three')])
        board.show(page)
        '''),
    snippet('Chips that filter', r'''
        page.chips([cards.Chip(name, item=('show', name), on=name == showing)
                    for name in ('All', 'Mine', 'Recent')])
        ${cursor}
        '''),
    snippet('Buttons on a page', r'''
        page.buttons([cards.Action('${cursor}Save', ('save',)),
                      cards.Action('Cancel', ('cancel',))])
        '''),
    snippet('Code on a card', r'''
        cards.Card('${cursor}Example', body=cards.code("print('hello')", lines=6))
        '''),
    snippet('Background job', r'''
        def work(run, term):
            # On a thread: never touch views here.
            for item in ${cursor}range(1000):
                if run.cancelled:          # a newer start() happened
                    return None
                run.put(item)
            return term


        def arrived(items):                # on the window's clock: views are safe
            print(len(items), 'more')


        job = ek.Job(window, work, on_items=arrived, on_done=print, on_error=print)
        job.start('term')                  # job.start_later(0.35, term) while typing
        '''),
    snippet('Remember between runs', r'''
        memory = ek.store('${cursor}my_tool')    # Documents/.editorkit/store/my_tool.json
        memory['runs'] = memory.get('runs', 0) + 1
        # After changing a list in place, assign it back or call memory.save().
        '''),
    snippet('Clock on a page', r'''
        import ui


        class Ticker(ui.View):
            def tick(self, now):
                # The window calls this every beat, shown or not: no update_interval.
                ${cursor}pass
        '''),
    snippet('Search files on a thread', r'''
        from editorkit import files

        for hit in files.search('${cursor}TODO', os.path.expanduser('~/Documents')):
            print(hit.path, hit.line, hit.text.strip())
        '''),
    snippet('Open a file at a line', r'''
        opener = ek.Opener(window)            # keep it: it ticks on the window's clock
        opener.go(${cursor}path, 12)
        '''),
    snippet('Watch the cursor', r'''
        def moved(event):
            chosen = ek.selection()
            if chosen:
                ${cursor}print('cursor at', chosen[0])


        listener = ek.on_change(moved, kinds=['selection'], key='my-watch')
        window.on('close', lambda _window: ek.remove_listener(listener))
        '''),
    snippet('Read and edit the code', r'''
        text = ek.text()
        start, end = ek.selection()
        ek.replace(start, end, text[start:end].upper())   # undo works
        ek.insert(${cursor}'print()')                      # at the cursor
        '''),
    snippet('Replace many, last first', r'''
        matches = ek.find_all('${cursor}old')
        for start, end in reversed(matches):    # last first: earlier indices stay right
            ek.replace(start, end, 'new')
        '''),
    snippet('Select and scroll to', r'''
        ek.select(${cursor}start, end)
        ek.reveal(start)                       # near the top, clear of windows
        '''),
    snippet('Note beside a line', r'''
        ek.annotate(${cursor}12, 'Check this', style='warning')   # ok, warning, error, note
        # ek.clear_annotations() takes them all away
        '''),
    snippet('Highlight a word', r'''
        ek.highlight('${cursor}TODO')
        # ek.clear_highlights() when done
        '''),
    snippet('Toolbar button', r'''
        def pressed(sender):
            ${cursor}print('pressed')


        ek.toolbar_button('⚡', pressed)
        # ek.remove_toolbar_button(...) or ek.clear_toolbar() puts it back
        '''),
    snippet('Keys above the keyboard', r'''
        ek.keyboard(second_row=['${cursor}self', 'def ', 'return ', ('True', 'False', 'None')])
        # ek.reset_keyboard() puts Pythonista's own back
        '''),
    snippet('Window in the keyboard\'s place', r'''
        from editorkit.web import tiles as web_tiles

        window = ek.Window('${cursor}Pad', emoji='🔤', key='my-pad', home='dock')
        board = web_tiles.Cards(window, on_pick=ek.insert, zoom_key='my-pad', dismiss_keyboard=False)
        window.add_page('Pad', board)
        '''),
    snippet('View and its keys (Pair)', r'''
        def make_keys():
            keys = ek.Window('Keys', emoji='⌨', key='my-keys', home='dock')
            ${cursor}
            return keys


        ek.Pair(view, make_keys).show()        # fill=True: the view fills above its keys
        '''),
    snippet('Sheet over a page', r'''
        window.show_sheet(${cursor}view)          # give it an opaque background
        window.close_sheet()
        '''),
    snippet('Pieces of one app', r'''
        piece = ek.Window('${cursor}Piece', emoji='🧩', key='my-app-piece', owner=app_window)
        # It folds into the app's box; closing the app closes it.
        '''),
    snippet('Clipboard while windows run', r'''
        from editorkit import clip      # the clipboard module can freeze with windows open

        text = clip.text()
        clip.set_text(${cursor}text.upper())
        '''),
    snippet('Theme colours', r'''
        colours = ek.theme_colours()          # {'background': '#1e1e24', ...}
        background = colours.get('background')
        ${cursor}
        '''),
    snippet('Add to the wrench menu', r'''
        ek.add_wrench_action(${cursor}__file__, 'My tool', icon='Primaries_Home', colour='#F26EFF')
        '''),
])


PYTHON = ('Python', '#5FD3BC', [
    snippet('Main guard', r'''
        def main():
            ${cursor}pass


        if __name__ == '__main__':
            main()
        '''),
    snippet('Dataclass', r'''
        from dataclasses import dataclass, field


        @dataclass
        class ${cursor}Item:
            name: str
            count: int = 0
            tags: list = field(default_factory=list)
        '''),
    snippet('Class with a property', r'''
        class Temperature:
            def __init__(self, celsius):
                self.celsius = celsius

            @property
            def fahrenheit(self):
                return self.celsius * 9 / 5 + 32

            def __repr__(self):
                return 'Temperature(%r)' % self.celsius
        ${cursor}
        '''),
    snippet('Enum', r'''
        from enum import Enum


        class ${cursor}Colour(Enum):
            RED = 'red'
            GREEN = 'green'
        '''),
    snippet('Named tuple', r'''
        from typing import NamedTuple


        class ${cursor}Point(NamedTuple):
            x: float
            y: float
        '''),
    snippet('Context manager', r'''
        from contextlib import contextmanager


        @contextmanager
        def ${cursor}opened_for_a_while():
            print('start')
            try:
                yield
            finally:
                print('always runs')
        '''),
    snippet('Timing decorator', r'''
        import functools
        import time


        def timed(function):
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                started = time.perf_counter()
                try:
                    return function(*args, **kwargs)
                finally:
                    print('%s took %.3f s' % (function.__name__, time.perf_counter() - started))
            return wrapper
        ${cursor}
        '''),
    snippet('Retry decorator', r'''
        import functools
        import time


        def retry(times=3, wait=1.0):
            def decorate(function):
                @functools.wraps(function)
                def wrapper(*args, **kwargs):
                    for attempt in range(times):
                        try:
                            return function(*args, **kwargs)
                        except Exception:
                            if attempt == times - 1:
                                raise
                            time.sleep(wait)
                return wrapper
            return decorate
        ${cursor}
        '''),
    snippet('Cache results', r'''
        from functools import lru_cache


        @lru_cache(maxsize=None)
        def ${cursor}fibonacci(n):
            return n if n < 2 else fibonacci(n - 1) + fibonacci(n - 2)
        '''),
    snippet('Read and write a text file', r'''
        with open('${cursor}notes.txt', encoding='utf-8') as handle:
            text = handle.read()

        with open('notes.txt', 'w', encoding='utf-8') as handle:
            handle.write(text)
        '''),
    snippet('JSON load and safe save', r'''
        import json
        import os


        def load(path, default=None):
            try:
                with open(path, encoding='utf-8') as handle:
                    return json.load(handle)
            except (OSError, ValueError):
                return default


        def save(path, data):
            temporary = path + '.tmp'
            with open(temporary, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, indent=2)
            os.replace(temporary, path)     # never leaves half a file
        ${cursor}
        '''),
    snippet('CSV read and write', r'''
        import csv

        with open('${cursor}data.csv', newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))

        with open('out.csv', 'w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        '''),
    snippet('Walk a folder', r'''
        from pathlib import Path

        for path in sorted(Path('~/Documents').expanduser().rglob('*.py')):
            if '${cursor}' not in path.parts:
                print(path.name, path.stat().st_size)
        '''),
    snippet('Dates and times', r'''
        from datetime import date, datetime, timedelta

        now = datetime.now()
        print(now.strftime('%Y-%m-%d %H:%M'))
        later = now + timedelta(days=7)
        parsed = datetime.strptime('${cursor}2026-11-13', '%Y-%m-%d')
        days_left = (date(now.year, 12, 25) - date.today()).days
        '''),
    snippet('Count things', r'''
        from collections import Counter

        counts = Counter(${cursor}'mississippi')
        print(counts.most_common(3))
        '''),
    snippet('Group into lists', r'''
        from collections import defaultdict

        by_first_letter = defaultdict(list)
        for word in ${cursor}['apple', 'avocado', 'banana']:
            by_first_letter[word[0]].append(word)
        '''),
    snippet('Sort by a key', r'''
        people = [{'name': 'Ana', 'age': 31}, {'name': 'Bo', 'age': 25}]
        by_age = sorted(people, key=lambda person: person['age'], reverse=${cursor}False)
        '''),
    snippet('Generator', r'''
        def ${cursor}chunks(items, size):
            for start in range(0, len(items), size):
                yield items[start:start + size]
        '''),
    snippet('Comprehensions', r'''
        squares = [n * n for n in range(10) if n % 2 == 0]
        lengths = {word: len(word) for word in ['tea', 'coffee']}
        unique = {letter for letter in 'banana'}
        ${cursor}
        '''),
    snippet('Try, else, finally', r'''
        try:
            ${cursor}value = int('42')
        except ValueError as problem:
            print('Not a number:', problem)
        else:
            print('Worked:', value)
        finally:
            print('Always runs')
        '''),
    snippet('Worker thread and queue', r'''
        import queue
        import threading

        jobs = queue.Queue()


        def worker():
            while True:
                job = jobs.get()
                if job is None:
                    break
                ${cursor}print('working on', job)


        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        jobs.put('first')
        jobs.put(None)                     # tells the worker to stop
        '''),
    snippet('Time some code', r'''
        import time

        started = time.perf_counter()
        ${cursor}
        print('%.3f seconds' % (time.perf_counter() - started))
        '''),
    snippet('Random choices', r'''
        import random

        random.seed(${cursor}1)            # the same picks every run, for testing
        pick = random.choice(['red', 'green', 'blue'])
        hand = random.sample(range(1, 53), 5)
        roll = random.randint(1, 6)
        '''),
    snippet('Logging', r'''
        import logging

        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        log = logging.getLogger('${cursor}my_tool')
        log.info('started')
        '''),
    snippet('Unit tests', r'''
        import unittest


        class ${cursor}TestThings(unittest.TestCase):
            def test_adds(self):
                self.assertEqual(1 + 1, 2)


        unittest.main(argv=['tests'], exit=False)
        '''),
])


WEB = ('Web & data', '#4FA3FF', [
    snippet('Get JSON (requests)', r'''
        import requests

        response = requests.get('${cursor}https://api.github.com/repos/python/cpython', timeout=15)
        response.raise_for_status()
        data = response.json()
        '''),
    snippet('Post JSON (requests)', r'''
        import requests

        response = requests.post('${cursor}https://httpbin.org/post', json={'name': 'value'}, timeout=15)
        response.raise_for_status()
        print(response.json())
        '''),
    snippet('Get a page (standard library)', r'''
        import urllib.request

        request = urllib.request.Request('${cursor}https://example.com', headers={'User-Agent': 'Pythonista'})
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode('utf-8')
        '''),
    snippet('Scrape with BeautifulSoup', r'''
        import requests
        from bs4 import BeautifulSoup

        page = requests.get('${cursor}https://example.com', timeout=15)
        soup = BeautifulSoup(page.text, 'html.parser')
        title = soup.title.string if soup.title else ''
        links = [(link.get_text(strip=True), link.get('href')) for link in soup.select('a[href]')]
        '''),
    snippet('Download a file', r'''
        import requests

        with requests.get('${cursor}https://example.com/file.zip', stream=True, timeout=30) as response:
            response.raise_for_status()
            with open('file.zip', 'wb') as handle:
                for chunk in response.iter_content(chunk_size=65536):
                    handle.write(chunk)
        '''),
    snippet('Query string', r'''
        from urllib.parse import urlencode

        url = '${cursor}https://example.com/search?' + urlencode({'q': 'pythonista', 'page': 2})
        '''),
    snippet('SQLite database', r'''
        import sqlite3

        connection = sqlite3.connect('${cursor}data.db')
        connection.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, text TEXT)')
        with connection:                    # commits, or rolls back on an error
            connection.execute('INSERT INTO notes (text) VALUES (?)', ('hello',))
        rows = connection.execute('SELECT id, text FROM notes ORDER BY id').fetchall()
        connection.close()
        '''),
    snippet('Regex with named groups', r'''
        import re

        pattern = re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})')
        for match in pattern.finditer('${cursor}Due 2026-11-13 and 2026-12-01'):
            print(match.group('year'), match.group('month'), match.group('day'))
        '''),
    snippet('Escape HTML', r'''
        import html

        safe = html.escape(${cursor}'<b>not bold</b>')
        '''),
    snippet('Hash and base64', r'''
        import base64
        import hashlib

        digest = hashlib.sha256(b'${cursor}text').hexdigest()
        encoded = base64.b64encode(b'text').decode('ascii')
        decoded = base64.b64decode(encoded)
        '''),
])


MATHS = ('Maths & plots', '#F5C26B', [
    snippet('Plot in a window', r'''
        import matplotlib.pyplot as plt
        import numpy as np

        import editorkit as ek

        x = np.linspace(-5, 5, 200)
        figure, axes = plt.subplots()
        axes.plot(x, ${cursor}x ** 2, label='y = x²')
        axes.axhline(0, color='grey', linewidth=0.8)
        axes.grid(True)
        axes.legend()
        ek.show(figure, title='Plot', key='plot')
        '''),
    snippet('Plot in the console', r'''
        import matplotlib.pyplot as plt

        plt.plot([1, 2, 3, 4], [${cursor}1, 4, 9, 16], marker='o')
        plt.title('Squares')
        plt.show()
        '''),
    snippet('NumPy basics', r'''
        import numpy as np

        values = np.array([${cursor}3, 1, 4, 1, 5, 9])
        print(values.mean(), values.std(), values.max())
        grid = np.arange(12).reshape(3, 4)
        evens = values[values % 2 == 0]
        '''),
    snippet('Statistics', r'''
        import statistics

        data = [${cursor}2, 4, 4, 4, 5, 5, 7, 9]
        print(statistics.mean(data), statistics.median(data), statistics.stdev(data))
        '''),
    snippet('Exact fractions', r'''
        from fractions import Fraction

        total = Fraction(${cursor}1, 3) + Fraction(1, 6)     # 1/2, exactly
        print(total, float(total))
        '''),
    snippet('Exact decimals', r'''
        from decimal import Decimal, ROUND_HALF_UP

        price = Decimal('${cursor}19.995').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        '''),
    snippet('Algebra (sympy)', r'''
        import sympy as sp

        x = sp.symbols('x')
        print(sp.solve(${cursor}x**2 - 5*x + 6, x))
        print(sp.factor(x**2 - 5*x + 6), sp.diff(sp.sin(x) * x, x), sp.integrate(x**2, x))
        '''),
    snippet('Number helpers', r'''
        import math

        print(math.gcd(${cursor}12, 18), math.lcm(4, 6), math.comb(5, 2), math.isqrt(50))
        print(round(math.pi, 3), math.hypot(3, 4))
        '''),
])


TEMPLATES = ('Templates', '#FF9E64', [
    snippet('App: a ui view', r'''
        """${cursor}My app: what it does, in one line."""
        import ui

        # --- Settings -------------------------------------------------------
        TITLE = 'My app'
        BACKGROUND = '#1e1e24'


        class App(ui.View):
            def __init__(self):
                self.name = TITLE
                self.background_color = BACKGROUND
                self.label = ui.Label(text='Hello', text_color='white', alignment=ui.ALIGN_CENTER)
                self.add_subview(self.label)

            def layout(self):
                self.label.frame = self.bounds


        if __name__ == '__main__':
            App().present('fullscreen')
        '''),
    snippet('Game: a scene', r'''
        """${cursor}My game: tap to move."""
        from scene import *


        class Game(Scene):
            def setup(self):
                self.background_color = '#1e1e24'
                self.player = SpriteNode('emj:Smiling_1', position=self.size / 2, parent=self)

            def update(self):
                # Every frame; self.dt is the time since the last one.
                pass

            def touch_began(self, touch):
                self.player.run_action(Action.move_to(touch.location.x, touch.location.y, 0.3))


        run(Game(), PORTRAIT)
        '''),
    snippet('Share-sheet extension', r'''
        """${cursor}Share sheet: run from Pythonista's share extension."""
        import appex
        import console


        def main():
            if not appex.is_running_extension():
                print('Run this from the share sheet.')
                return
            text = appex.get_text()
            url = appex.get_url()
            print(text, url)
            console.hud_alert('Done')


        main()
        '''),
    snippet('Keyboard script', r'''
        """${cursor}Keyboard: run from the Pythonista keyboard's scripts."""
        import keyboard

        if keyboard.is_keyboard():
            selected = keyboard.get_selected_text()
            keyboard.insert_text(selected.upper())
        else:
            print('Run this from the Pythonista keyboard.')
        '''),
    snippet('Lesson (editorkit)', r'''
        """Lesson: ${cursor}Topic.

        Run this script. A lesson window opens over the code, and the editor
        shows the step it is explaining.
        """
        import editorkit as ek
        from editorkit.lessons import Lesson

        lesson = Lesson('Topic', __file__)


        @lesson.step('A first step')
        def first():
            """The idea, in a sentence or two.

            Try it, then look at what changed."""
            ek.show('Hello', title='Step 1', key='lesson-step-1', owner=lesson.window)
            return 'A window opened.'


        lesson.run()
        '''),
    snippet('Script with settings', r'''
        """${cursor}What this script does, in one line."""

        # --- Settings: change these -------------------------------------------
        FOLDER = '~/Documents'
        LIMIT = 20


        # --- The work ---------------------------------------------------------------

        def main():
            print('Working in', FOLDER, 'up to', LIMIT)


        if __name__ == '__main__':
            main()
        '''),
])


SEEDS = [PYTHONISTA, EDITORKIT, PYTHON, WEB, MATHS, TEMPLATES]
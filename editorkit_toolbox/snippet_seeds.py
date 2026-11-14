"""The starter snippets for a new Snippets library (editorkit_toolbox.snippets seeds a
library file that does not exist yet). Edit freely: (group, colour,
[(title, text), ...]). ${cursor} marks where the cursor lands; ${date},
${time} and ${clipboard} are filled in when a snippet is typed.
"""

SEEDS = [
    ('Pythonista', '#8E6CEF', [
        ('ui.View class',
         "import ui\n\n\nclass Panel(ui.View):\n    def __init__(self):\n        self.name = 'Panel'\n        self.background_color = '#1e1e24'\n        ${cursor}\n\n    def layout(self):\n        pass\n\n\nPanel().present('fullscreen')\n"),
        ('Button',
         "button = ui.Button(title='${cursor}')\nbutton.frame = (10, 10, 120, 40)\nbutton.action = lambda sender: print(sender.title)\nself.add_subview(button)\n"),
        ('Main thread',
         "from objc_util import on_main_thread\n\n\n@on_main_thread\ndef ${cursor}():\n    pass\n"),
        ('Clipboard (safe)',
         "from objc_util import ObjCClass\n\npasteboard = ObjCClass('UIPasteboard').generalPasteboard()\ntext = str(pasteboard.string() or '')\npasteboard.setString_(${cursor})\n"),
        ('Scene',
         "from scene import Scene, run\n\n\nclass Game(Scene):\n    def setup(self):\n        ${cursor}\n\n    def update(self):\n        pass\n\n    def touch_began(self, touch):\n        pass\n\n\nrun(Game(), show_fps=True)\n"),
        ('HUD alert',
         "import console\n\nconsole.hud_alert('${cursor}', 'success', 1.0)\n"),
        ('Update tick',
         "self.update_interval = 0.5          # in __init__\n\ndef update(self):\n    ${cursor}\n"),
    ]),
    ('editorkit', '#2F80ED', [
        ('Window',
         "import editorkit as ek\n\nwin = ek.Window('${cursor}', emoji='🧪', key='lab-window')\nwin.add_page('Main', view)\nwin.add_button('▶', lambda w: print('tap'), name='run')\nwin.show()\n"),
        ('Background job',
         "def work(run, *args):\n    for item in items:\n        if run.cancelled:\n            return\n        run.put(item)\n\n\njob = ek.Job(window, work, on_items=shown, on_done=finished)\njob.start(${cursor})\n"),
        ('Edit text',
         "ek.edit_text(${cursor}'', title='Edit', name='', chips=('TODO',),\n             on_done=lambda text, name: print(name, text))\n"),
        ('Code rows',
         "rows = [codeview.Row('${cursor}', 'plain')]\ncode = web_tiles.Code(window, on_pick=picked)\ncode.set_section(codeview.rows_section(1, 'Label', rows))\n"),
    ]),
    ('Python', '#27AE60', [
        ('Main guard',
         "def main():\n    ${cursor}\n\n\nif __name__ == '__main__':\n    main()\n"),
        ('Settings block',
         "# --- Settings -------------------------------------------------------------\n\n${cursor}\n"),
        ('Timer',
         "import time\n\nstarted = time.time()\n${cursor}\nprint('took %.3f s' % (time.time() - started))\n"),
        ('Traceback guard',
         "import traceback\n\ntry:\n    ${cursor}\nexcept Exception:\n    traceback.print_exc()\n"),
        ('JSON save (atomic)',
         "import json\nimport os\n\n\ndef save_json(path, data):\n    temporary = path + '.tmp'\n    with open(temporary, 'w', encoding='utf-8') as handle:\n        json.dump(data, handle, indent=2)\n    os.replace(temporary, path)\n${cursor}"),
        ('Dataclass',
         "from dataclasses import dataclass, field\n\n\n@dataclass\nclass ${cursor}:\n    name: str\n    items: list = field(default_factory=list)\n"),
        ('Smoke check',
         "passed, failed = [], []\n\n\ndef check(name, got, wanted):\n    ok = got == wanted\n    (passed if ok else failed).append(name)\n    print('%s  %s' % ('PASS' if ok else 'FAIL', name))\n\n\n${cursor}\n\nprint('%d/%d' % (len(passed), len(passed) + len(failed)))\nif failed:\n    raise SystemExit(1)\n"),
    ]),

]
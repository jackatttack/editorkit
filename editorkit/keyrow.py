"""The row of extra keys above the keyboard: your own keys, and a second row.

A row is a list of keys. A key is a string (what it types), or a list whose
first string is the key and the rest its long-press options:

    ['def ', ('(', '[', '{'), ('.', 'self.', '->')]

'%special:undo' and '%special:redo' are Pythonista's undo and redo keys.
A small keeper applies the rows to whichever editor tab is open, and shows
the second row whenever the keyboard is up.
"""
import ui
from objc_util import ns

from . import _app

ROW_HEIGHT = 36
TICK_SECONDS = 0.25


def normalise_row(keys):
    row = []
    for key in keys:
        if isinstance(key, str):
            row.append([key])
        else:
            options = [str(option) for option in key]
            if not options:
                raise ValueError('a key needs at least one string')
            row.append(options)
    return row


def as_python(row):
    if row is None:
        return None
    return [[str(row.objectAtIndex_(i).objectAtIndex_(j))
             for j in range(row.objectAtIndex_(i).count())]
            for i in range(row.count())]


class Keeper(ui.View):
    """Applies the wanted rows to each editor's key row, once each."""

    def __init__(self):
        self.row1 = None
        self.row2 = None
        self.touched = {}     # accessory pointer -> what to restore
        self.background_color = (0, 0, 0, 0)
        self.frame = (0, 0, 1, 1)
        self.update_interval = TICK_SECONDS

    def update(self):
        try:
            self.tick()
        except Exception:
            pass

    def tick(self):
        editor = _app.editor_view()
        if editor is None:
            return
        accessory = editor.keyboardAccessoryView()
        text_view = editor.textView()
        if accessory is None:
            return
        entry = self.touched.get(accessory.ptr)
        if entry is None:
            entry = {'accessory': accessory, 'text_view': text_view,
                     'original': as_python(accessory.keyRow1()), 'container': None}
            self.touched[accessory.ptr] = entry
            if self.row1 is not None:
                accessory.setKeyRow1_(ns(self.row1))
            if self.row2 is not None:
                accessory.setKeyRow2_(ns(self.row2))
            accessory.setupButtons()
        if self.row2 is not None and text_view.isFirstResponder():
            current = text_view.inputAccessoryView()
            container = entry['container']
            if container is None or current is None or current.ptr != container.objc_instance.ptr:
                self.wrap(entry)

    def wrap(self, entry):
        """Our own two-row-tall container, with Pythonista's row inside it
        (the row itself snaps back to one row's height)."""
        accessory, text_view = entry['accessory'], entry['text_view']
        width = accessory.frame().size.width
        if entry['container'] is None:
            container = ui.View()
            container.frame = (0, 0, width, ROW_HEIGHT * 2)
            container.flex = 'W'
            container.objc_instance.setBackgroundColor_(accessory.backgroundColor())
            entry['container'] = container
        accessory.setClipsToBounds_(False)
        entry['container'].objc_instance.addSubview_(accessory)
        accessory.setFrame_(((0, 0), (width, ROW_HEIGHT)))
        text_view.setInputAccessoryView_(entry['container'].objc_instance)
        text_view.reloadInputViews()

    def restore_all(self):
        for entry in self.touched.values():
            accessory = entry['accessory']
            try:
                if entry['original'] is not None:
                    accessory.setKeyRow1_(ns(entry['original']))
                accessory.setKeyRow2_(None)
                accessory.setupButtons()
                if entry['container'] is not None:
                    accessory.removeFromSuperview()
                    entry['text_view'].setInputAccessoryView_(accessory)
                    entry['text_view'].reloadInputViews()
            except Exception:
                pass
        self.touched.clear()


def _keeper(create=True):
    objects = _app.store('objects')
    keeper = objects.get('keyboard')
    if keeper is not None and keeper.objc_instance.superview() is not None:
        return keeper
    if not create:
        return None
    keeper = Keeper()
    _app.prepare(keeper)
    _app.root().detailViewController().view().addSubview_(keeper.objc_instance)
    objects['keyboard'] = keeper
    return keeper


@_app.on_main
def keyboard(keys=None, second_row=None):
    """Set the key row (keys) and/or add a second row. None keeps Pythonista's."""
    keeper = _keeper()
    keeper.restore_all()
    keeper.row1 = normalise_row(keys) if keys is not None else None
    keeper.row2 = normalise_row(second_row) if second_row is not None else None
    keeper.tick()


@_app.on_main
def reset_keyboard():
    keeper = _keeper(create=False)
    if keeper is None:
        return
    keeper.restore_all()
    keeper.update_interval = 0
    keeper.objc_instance.removeFromSuperview()
    _app.store('objects').pop('keyboard', None)
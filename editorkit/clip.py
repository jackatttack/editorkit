"""The clipboard, through UIPasteboard.

Pythonista's clipboard module can freeze Pythonista while windows run
Python (a consolekit finding), so editorkit code and tools use these.

    from editorkit import clip
    clip.set_text('hello'); clip.text()
"""
from objc_util import ObjCClass


def text():
    """The clipboard's text, or '' when it holds none."""
    value = ObjCClass('UIPasteboard').generalPasteboard().string()
    return str(value) if value is not None else ''


def set_text(value):
    ObjCClass('UIPasteboard').generalPasteboard().setString_(value)
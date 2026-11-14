"""Line annotations: Pythonista's own banners beside a line of code.

Display only: the file is never changed. Lines are numbered from 1, as in
the editor.
"""
from objc_util import ns

from . import _app

STYLES = {'ok': 0, 'warning': 1, 'error': 2, 'note': 3}


def style_number(style):
    if style in STYLES.values() and not isinstance(style, bool):
        return style
    try:
        return STYLES[style]
    except (KeyError, TypeError):
        raise ValueError('style must be one of %s' % ', '.join(STYLES))


def annotation_dict(line, text, style='note'):
    """The dictionary Pythonista stores for one annotation."""
    if line < 1:
        raise ValueError('lines start at 1')
    return {'style': style_number(style), 'paragraphIndex': line - 1,
            'expanded': True, 'text': str(text)}


@_app.on_main
def annotate(line, text, style='note'):
    """Show text beside line (1-based). style: ok, warning, error or note."""
    editor = _app.editor_view()
    if editor is None:
        return False
    data = annotation_dict(line, text, style)
    editor.setLineAnnotation_forParagraphAtIndex_(ns(data), data['paragraphIndex'])
    editor.textView().setNeedsDisplay()
    return True


@_app.on_main
def clear_annotations():
    editor = _app.editor_view()
    if editor is not None:
        editor.removeAllLineAnnotations()
        editor.textView().setNeedsDisplay()


@_app.on_main
def remove_annotation(line):
    """Take away the note beside one line (1-based); every other note stays.
    Returns True if that line had one.

    Pythonista has no call that removes one note, so this keeps a copy of
    the others, clears them all, and puts the others back."""
    editor = _app.editor_view()
    if editor is None:
        return False
    store = editor.lineAnnotationsByParagraphIndex()
    if store is None:
        return False
    wanted = line - 1
    others = []
    found = False
    for key in store.allKeys():
        paragraph = int(key.intValue())
        if paragraph == wanted:
            found = True
        else:
            others.append((paragraph, store.objectForKey_(key).mutableCopy()))
    if not found:
        return False
    editor.removeAllLineAnnotations()
    for paragraph, data in others:
        editor.setLineAnnotation_forParagraphAtIndex_(data, paragraph)
    editor.textView().setNeedsDisplay()
    return True

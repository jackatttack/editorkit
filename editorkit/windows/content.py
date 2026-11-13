"""Turning things into page views (ported from consolekit's show, 2026-11-08).

    a ui.View                  used as it is
    builder(window)            called, and its result turned into a page
    'panel.pyui'               loaded (add_page loads it at once, so relative
                               paths and actions resolve against your script)
    ui.Image, PIL image,
    matplotlib figure, pyplot  an image, scaled to fit
    HTML                       a web page; fragments get the theme's style
    one short line             drawn big, like a display
    a few lines                a label (the window still drags through it)
    longer text                a scrolling, read-only text view
"""
import io
import os
import sys

import ui

from . import look, rules


# HTML pages: editorkit's root sets this to editorkit.web.page_for_html, so
# the core never imports the web package (the web fence, 2026-11-12). It
# takes (html, window) and returns a view, or None to keep the plain web
# view below. Left as None, the core still shows HTML on its own.
make_html_page = None


def view_for(thing, window):
    """A ui.View page for thing, in the window's colours."""
    if isinstance(thing, ui.View):
        return thing
    if callable(thing):
        return view_for(thing(window), window)
    if rules.is_pyui_path(thing) and os.path.isfile(os.path.abspath(thing.strip())):
        return load_pyui(thing)
    palette = window.palette
    image = image_for(thing)
    if image is not None:
        view = ui.ImageView()
        view.image = image
        view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        view.touch_enabled = False
        return view
    text = '' if thing is None else str(thing)
    if rules.looks_like_html(text):
        view = make_html_page(text, window) if make_html_page is not None else None
        if view is not None:
            return view
        view = ui.WebView()
        view.load_html(rules.page_html(text, palette.panel, palette.text, palette.accent))
        return view
    if rules.is_short_line(text, look.BIG_TEXT_LIMIT):
        return big_label(text.strip(), palette)
    if rules.line_count(text) <= look.LABEL_LINE_LIMIT:
        label = ui.Label(text=text, number_of_lines=0, alignment=ui.ALIGN_CENTER,
                         font=('<system>', 15), text_color=palette.text)
        label.touch_enabled = False
        return label
    view = ui.TextView()
    view.text = text
    view.editable = False
    view.font = ('Menlo', 13)
    view.text_color = palette.text
    view.background_color = look.CLEAR
    return view


def image_for(thing):
    """A ui.Image from a ui.Image, matplotlib figure (or pyplot) or PIL image, else None."""
    if isinstance(thing, ui.Image):
        return thing
    buffer = io.BytesIO()
    if hasattr(thing, 'savefig'):
        thing.savefig(buffer, format='png')
    elif hasattr(thing, 'save') and hasattr(thing, 'mode'):
        thing.save(buffer, 'PNG')
    else:
        return None
    return ui.Image.from_data(buffer.getvalue())


def big_label(text, palette):
    """A big centred label that shrinks to fit rather than cutting text off."""
    label = ui.Label(text=text, alignment=ui.ALIGN_CENTER, text_color=palette.text,
                     font=('<system-bold>', look.BIG_TEXT_SIZE))
    label.touch_enabled = False
    native = label.objc_instance
    native.setAdjustsFontSizeToFitWidth_(True)
    native.setMinimumScaleFactor_(0.25)
    return label


def load_pyui(path):
    """A view from a .pyui file. A relative path starts in the running script's
    folder; actions named in the file are looked up in the script that called."""
    full_path = os.path.abspath(path.strip())
    if not os.path.isfile(full_path):
        raise FileNotFoundError('No .pyui file at %s' % full_path)
    try:
        return ui.load_view(full_path, stackframe=caller_frame())
    except TypeError:                      # a ui module without stackframe
        return ui.load_view(full_path)


def caller_frame():
    """The first stack frame outside editorkit: the script that called us."""
    frame = sys._getframe(1)
    while frame is not None and str(frame.f_globals.get('__name__', '')).startswith('editorkit'):
        frame = frame.f_back
    return frame


def title_for(thing):
    """The title ek.show uses when it is given none."""
    if isinstance(thing, ui.View):
        return thing.name or 'Window'
    if rules.is_pyui_path(thing):
        return os.path.splitext(os.path.basename(thing.strip()))[0]
    if hasattr(thing, 'savefig'):
        return 'Chart'
    if isinstance(thing, ui.Image) or (hasattr(thing, 'save') and hasattr(thing, 'mode')):
        return 'Image'
    if rules.looks_like_html(str(thing)):
        return 'Page'
    return 'Text'
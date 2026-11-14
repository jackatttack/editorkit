"""The Console's card for a failed run, in the docs' look.

    html, items = traceback_card.problem_section(result.problem)

A danger callout titled with the error itself ("ZeroDivisionError:
division by zero"). Inside: the reader's own frames as docs-style rows,
the failing line first, each tappable to open its file there; frames in
libraries and Python itself folded into one quiet row; then buttons: Go to
line, ❓ Explain this line and ⧉ Copy. Taps hand back (path, line) for a
frame and an Action for a button.

Pure (no ui), so tests/smoke_traceback_card.py loads it by path. The
problem comes from editorkit_toolbox.runner (Problem, Frame).
"""
from collections import namedtuple

from editorkit.web import codeview, prose


# --- Words and look (editable) ----------------------------------------------

GO_LABEL = 'Go to line'
EXPLAIN_LABEL = '❓ Explain this line'
COPY_LABEL = '⧉ Copy'
LIBRARY_WORDS = '%d more in libraries and Python itself'

CSS = """
.tb-code { font: 13px/1.45 Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.tb-quiet { cursor: default; opacity: 0.7; }
.tb-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
"""


# --- What a button tap hands back -------------------------------------------

Action = namedtuple('Action', 'kind path line text')   # kind: go, explain or copy


# --- Building ------------------------------------------------------------------

def failing_frame(problem):
    """The frame to point at: the innermost of the reader's own frames that
    has a line, else the innermost frame; None when there are none."""
    own = [frame for frame in problem.frames if frame.own and frame.line]
    if own:
        return own[-1]
    return problem.frames[-1] if problem.frames else None


def where(frame):
    """'app.py, line 4 · in main': the words under a frame's code (the file
    name only; Go to line and a tap know the full path)."""
    name = frame.short.split('/')[-1]
    words = '%s, line %s' % (name, frame.line) if frame.line else name
    if frame.name and frame.name != '<module>':
        words += ' · in %s' % frame.name
    return words


def frame_row(frame, ids):
    """One frame: its code, syntax-coloured, over where it is. Tappable when
    its file can be opened."""
    item = (frame.path, frame.line) if frame.path and frame.line else None
    code = codeview.line_html(frame.code, codeview.syntax_classes(frame.code).get(1, []), [])
    signature = '<div class="tb-code">%s</div>' % code
    return prose.row(signature, where(frame), codeview.go_attribute(ids.go(item)))


def module_label(path):
    """'decoder.py', or the package's name for its __init__.py ('json')."""
    parts = path.split('/')
    if parts[-1] == '__init__.py' and len(parts) > 1:
        return parts[-2]
    return parts[-1]


def library_row(frames):
    """Frames outside the reader's code, folded into one quiet row."""
    names = []
    for frame in frames:
        name = module_label(frame.path or frame.short)
        if name not in names:
            names.append(name)
    return ('<div class="ek-row tb-quiet"><div>%s</div><div class="ek-row-text">%s</div></div>'
            % (prose.escape(LIBRARY_WORDS % len(frames)), prose.escape(', '.join(names))))


def action_buttons(problem, ids):
    frame = failing_frame(problem)
    actions = []
    if frame is not None and frame.path and frame.line:
        actions.append((GO_LABEL, Action('go', frame.path, frame.line, '')))
        actions.append((EXPLAIN_LABEL, Action('explain', frame.path, frame.line, '')))
    actions.append((COPY_LABEL, Action('copy', None, None, problem.text)))
    spans = ''.join('<span class="fd-act"%s>%s</span>'
                    % (codeview.go_attribute(ids.go(action)), prose.escape(label))
                    for label, action in actions)
    return '<div class="tb-actions">%s</div>' % spans


def problem_section(problem, section=0):
    """(html, items) for a failed run's card."""
    ids = codeview.SectionIds(section)
    own = [frame for frame in problem.frames if frame.own]
    library = [frame for frame in problem.frames if not frame.own]
    blocks = [frame_row(frame, ids) for frame in reversed(own)]
    if library:
        blocks.append(library_row(library))
    blocks.append(action_buttons(problem, ids))
    html = prose.article(prose.callout(problem.title, *blocks, kind='danger'))
    return html, ids.items
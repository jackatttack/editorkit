"""Highlight every match in the open script with the editor's own marks."""
from . import _app


@_app.on_main
def highlight(term, case_sensitive=False):
    editor = _app.editor_view()
    if editor is None:
        return False
    editor.highlightSearchTerm_caseInsensitive_afterDelay_(str(term), not case_sensitive, 0.0)
    return True


@_app.on_main
def clear_highlights():
    editor = _app.editor_view()
    if editor is not None:
        editor.clearHighlights_(None)
        editor.setSearchTerm_('')
"""Which editorkit a tool needs: a friendly refusal instead of a broken page.

Role: contracts · Part of: editorkit · Pure

    import editorkit as ek
    ek.require('0.7.0', 'Maths')     # raises EditorkitTooOld with what to do

A plugin that uses newer API (ekSend, tile.patch, ek.data) checks first, so
an older Toolbox says "update Toolbox" instead of failing half-way.
"""

UPDATE_HINT = 'Update Toolbox: run its installer again (github.com/jackatttack/editorkit).'


class EditorkitTooOld(RuntimeError):
    """This editorkit is older than a tool needs."""


def version_tuple(version):
    """'0.6.10' -> (0, 6, 10); anything not a number counts as 0."""
    parts = []
    for part in str(version).split('.'):
        digits = ''.join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def too_old(current, minimum, needed_by='This tool'):
    """The message when current is older than minimum, else ''."""
    if version_tuple(current) >= version_tuple(minimum):
        return ''
    return '%s needs editorkit %s or later; this is %s. %s' % (needed_by, minimum, current, UPDATE_HINT)


def require(current, minimum, needed_by='This tool'):
    message = too_old(current, minimum, needed_by)
    if message:
        raise EditorkitTooOld(message)
    return True
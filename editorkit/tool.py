"""run_tool: keep a tool's names alive after its script ends.

Pythonista clears a script's names when it finishes, but a tool's buttons
and callbacks run later, and a function that reaches a cleared name fails.
run_tool(main) copies the script's names, points its functions and its
classes' methods at the copy, and calls main there. Write the tool as an
ordinary script, settings and helpers at the top level, and end it with:

    ek.run_tool(main)

Lessons do the same through Lesson.run().
"""
import sys
import types


def _rebound(function, names):
    return types.FunctionType(function.__code__, names, function.__name__,
                              function.__defaults__, function.__closure__)


def _rebind_class(cls, original, names):
    for attribute, value in list(vars(cls).items()):
        if isinstance(value, (staticmethod, classmethod)):
            inner = value.__func__
            if isinstance(inner, types.FunctionType) and inner.__globals__ is original:
                setattr(cls, attribute, type(value)(_rebound(inner, names)))
        elif isinstance(value, types.FunctionType) and value.__globals__ is original:
            setattr(cls, attribute, _rebound(value, names))


def keep_names(original):
    """A copy of a script's names whose functions and classes use the copy."""
    names = dict(original)
    for key, value in list(names.items()):
        if isinstance(value, types.FunctionType) and value.__globals__ is original:
            names[key] = _rebound(value, names)
        elif isinstance(value, type) and value.__module__ == original.get('__name__'):
            _rebind_class(value, original, names)
    return names


def run_tool(main, *args, **kwargs):
    """Call main(*args, **kwargs) with the calling script's names kept alive
    after the script ends. Returns what main returns."""
    original = sys._getframe(1).f_globals
    names = keep_names(original)
    runner = names.get(main.__name__)
    if runner is None or not isinstance(runner, types.FunctionType):
        runner = _rebound(main, names)
    return runner(*args, **kwargs)
"""Lesson 4: Edit the code.

Run this script. The steps read and change the open script, and the lines
they change are the practice lines at the bottom of this file: watch them
as you go. The last step puts them back.
"""
import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('Edit the code', __file__)

# The practice lines sit between two marks. Each mark is built from two
# pieces, so the steps' own code never matches it: only the real marks do.
START_MARK = '# --- practice' + ': start'
END_MARK = '# --- practice' + ': end'
PRACTICE = ("title = 'My tool'\n"
            "colour = 'teal'\n"
            "speed = 1\n"
            "border_colour = 'teal'\n")
NO_PRACTICE = 'The practice lines are not showing: tap 📜 to bring this lesson back, then try again.'


def practice_span():
    """(start, end): where the practice lines are in the open script, as
    Python indices; None when this lesson is not the script showing."""
    text = ek.text() or ''
    start = text.find(START_MARK)
    end = text.find(END_MARK, start + 1)
    if start < 0 or end < 0:
        return None
    return text.index('\n', start) + 1, end


@lesson.step('The code as a string')
def read_code():
    """ek.text() is the open script as one Python string; ek.selection()
    is the cursor as (start, end), equal when nothing is selected. Both
    count the Python way, so an emoji never throws a position off.

    Tap ▶ Try it: the card says what they found."""
    text = ek.text()
    start, end = ek.selection()
    line = text.count('\n', 0, start) + 1
    first, last = ek.visible_lines()
    return '%d characters in %d lines. The cursor is on line %d; lines %d-%d are on screen.' % (
        len(text), text.count('\n') + 1, line, first, last)


@lesson.step('Find, then look')
def find_and_look():
    """ek.find_all(word) gives every match as (start, end). They are plain
    Python indices, so filter them like any list: here, only the matches
    inside the practice lines.

    Try it: the first match is selected with ek.select, and ek.reveal
    scrolls it into view."""
    span = practice_span()
    if span is None:
        return NO_PRACTICE
    matches = [match for match in ek.find_all('teal') if span[0] <= match[0] < span[1]]
    if not matches:
        return 'No teal left in the practice lines: try Put it back.'
    ek.select(*matches[0])
    ek.reveal(matches[0][0])
    return '%d matches in the practice lines; the first is selected.' % len(matches)


@lesson.step('Change one range')
def change_range():
    """ek.replace(start, end, new) swaps one range for new text. It goes
    through the editor, so Pythonista's own undo takes it back.

    Try it: the speed line changes. Look at the practice lines."""
    span = practice_span()
    if span is None:
        return NO_PRACTICE
    text = ek.text()
    found = text.find('speed = ', span[0], span[1])
    if found < 0:
        return 'No speed line left: try Put it back.'
    ek.replace(found, text.index('\n', found), 'speed = 5')
    ek.reveal(found)
    return 'speed = 5 now. Undo would take it back.'


@lesson.step('Insert at a place')
def insert_line():
    """ek.insert(text) types at the cursor, over any selection, like a
    paste. Put the cursor where you want it first with ek.select(index).

    Try it: a new line lands at the end of the practice lines."""
    span = practice_span()
    if span is None:
        return NO_PRACTICE
    ek.select(span[1])
    ek.insert('shadow = True\n')
    ek.reveal(span[1])
    return 'Added shadow = True at the end of the practice lines.'


@lesson.step('Many changes: last first')
def replace_many():
    """Every change moves the text after it, so indices found before a
    change are wrong after it. Change many places from the last to the
    first, and each index is still right when its turn comes.

    Try it: every teal in the practice lines becomes coral. For the whole
    script at once there is ek.replace_all(old, new)."""
    span = practice_span()
    if span is None:
        return NO_PRACTICE
    matches = [match for match in ek.find_all('teal') if span[0] <= match[0] < span[1]]
    for start, end in reversed(matches):
        ek.replace(start, end, 'coral')
    return 'Changed %d, last first.' % len(matches)


@lesson.step('Put it back')
def put_back():
    """A lesson that changes things puts them back: one ek.replace over
    the whole practice block restores it as it started.

    Try it, then Done ✓."""
    span = practice_span()
    if span is None:
        return NO_PRACTICE
    ek.replace(span[0], span[1], PRACTICE)
    ek.reveal(span[0])
    return 'The practice lines are as they started.'


# --- practice: start
title = 'My tool'
colour = 'teal'
speed = 1
border_colour = 'teal'
# --- practice: end


lesson.run()
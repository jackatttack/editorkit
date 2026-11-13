"""Annotations in all four styles on the open script, plus highlighting."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import editorkit as ek

ek.clear_annotations()
ek.annotate(1, 'All good', style='ok')
ek.annotate(2, 'Worth a look', style='warning')
ek.annotate(3, 'Something broke', style='error')
ek.annotate(4, 'A note to self', style='note')
ek.highlight('import')
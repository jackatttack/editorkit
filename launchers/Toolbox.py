"""Toolbox for Pythonista: opens the hub over the code.
The installer adds this to the wrench menu; run it again to reopen the hub."""
import sys

for name in list(sys.modules):
    if name == 'editorkit_toolbox' or name.startswith('editorkit_toolbox.'):
        del sys.modules[name]

from editorkit_toolbox import hub

hub.open_hub()

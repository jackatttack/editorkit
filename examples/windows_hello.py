"""editorkit windows, the shortest start: one line, one window.

Run it, then slide the console away.
- Tap 🐍 or – to fold the window into a pin. Tap the pin to open it again.
- Hold anywhere empty to move it. ◢ resizes it.
- Drag it down past the line to dock it in the keyboard's place.
- Hold it poking off the right edge to send it to the console.
- ✕ closes it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import editorkit as ek  # noqa: E402

ek.show('Hello', title='Hello')
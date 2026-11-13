"""ek.show takes almost anything: each kind here gets its own window.

Run it, then run it again: the windows stay where you left them and their
content updates in place, so ek.show can run in a loop.
"""


import ui

import editorkit as ek

ek.show('42', title='Answer')                       # one short line: drawn big
ek.show('<h2>Hello</h2><p>HTML fragments get your theme\'s colours.</p>', title='Page')
ek.show(ui.Image.named('test:Lenna'), title='Image')
ek.show('\n'.join('line %d' % number for number in range(1, 41)), title='Long text')

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
if plt is not None:
    figure, axes = plt.subplots()
    axes.plot([0, 1, 4, 9, 16, 25])
    axes.set_title('Squares')
    ek.show(figure, title='Chart')
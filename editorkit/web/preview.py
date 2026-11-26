"""Any editorkit page as a stand-alone HTML file, to test off the device.

Role: check · Part of: editorkit/web · Pure

    from editorkit.web import preview
    preview.write('chart.html', body_html, extra_css=..., extra_js=..., theme='dark')

Open the file in Safari or Chrome on a Mac (Responsive Design Mode for a
phone-sized window), or drive it headless with synthetic touches:

    google-chrome --headless=new --touch-events=enabled --virtual-time-budget=5000 \
        --dump-dom file:///path/chart.html

test_js runs after the page is ready, with window.ekTest:

    ekTest.tap(node)                 a one-finger tap on node's centre
    ekTest.drag(node, dx, dy, steps) a finger down on node, moved, lifted
    ekTest.say(words)                adds a line to #ek-test-log (read with --dump-dom)
    window.ekSent                    every ekSend(name, data) the page made

The page is the real shell (codeview.page_html: fast taps, ekTouch, the
bridge) in a stand-in theme; links back to Python go nowhere off device,
so ekSend is recorded instead. Why (2026-11-26): mathskit's chart touches
were checked this way before any device test, and caught real bugs.
"""
import json

from . import bridge, codeview


class Theme:
    """A stand-in palette (the fields page_html reads)."""

    def __init__(self, panel, background, text, dim, accent):
        self.panel, self.background, self.text, self.dim, self.accent = panel, background, text, dim, accent


THEMES = {
    'dark': Theme('#161b22', '#0d1117', '#e6edf3', '#8b949e', '#ff7b72'),
    'light': Theme('#ffffff', '#f6f8fa', '#1f2328', '#656d76', '#cf222e'),
}

TEST_SCRIPT = r"""
window.ekSent = [];
window.ekSend = function (name, data) { window.ekSent.push([name, data]); };
window.ekTest = (function () {
  function centre(node) {
    var r = node.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  }
  function fire(node, type, x, y) {
    var touch = new Touch({identifier: 1, target: node, clientX: x, clientY: y});
    var lifted = type === 'touchend';
    node.dispatchEvent(new TouchEvent(type, {touches: lifted ? [] : [touch], targetTouches: lifted ? [] : [touch],
                                              changedTouches: [touch], bubbles: true, cancelable: true}));
  }
  function tap(node) { var c = centre(node); fire(node, 'touchstart', c[0], c[1]); fire(node, 'touchend', c[0], c[1]); }
  function drag(node, dx, dy, steps) {
    steps = steps || 6;
    var c = centre(node);
    fire(node, 'touchstart', c[0], c[1]);
    for (var i = 1; i <= steps; i++) { fire(node, 'touchmove', c[0] + dx * i / steps, c[1] + dy * i / steps); }
    fire(node, 'touchend', c[0] + dx, c[1] + dy);
  }
  function say(words) {
    var log = document.getElementById('ek-test-log');
    if (!log) { log = document.createElement('pre'); log.id = 'ek-test-log'; document.body.insertBefore(log, document.body.firstChild); }
    log.textContent += words + '\n';
  }
  return {tap: tap, drag: drag, centre: centre, say: say};
})();
"""


def page(body_html, extra_css='', extra_js='', theme='dark', test_js=''):
    """The full HTML of a page showing body_html, as a tile would."""
    shell = codeview.page_html(THEMES.get(theme, THEMES['dark']), extra_css=extra_css, extra_js=extra_js)
    show = 'setResults(%s, false);' % json.dumps(body_html)
    tail = ('<script>%s\n%s\nwindow.ekWhenReady(function () { setTimeout(function () {\n%s\n}, 300); });'
            '</script></body>' % (bridge.safe_script(TEST_SCRIPT), bridge.safe_script(show), bridge.safe_script(test_js)))
    return shell.replace('</body>', tail, 1)


def write(path, body_html, **options):
    """Write page(...) to path; returns path."""
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(page(body_html, **options))
    return path
"""The bridge between a page and Python: messages, patches, and ready.

Role: contracts, present · Part of: editorkit/web · Pure

codeview.page_html puts SCRIPT and READY_SCRIPT in every page shell, after
the shell's own script and ekTouch, with the page's extra_js between them.
So on every editorkit page:

    ekSend(name, data)         page -> Python: tile.on_message(name, fn)
                               calls fn(data) on the window's clock. data is
                               anything JSON can carry; keep it small (it
                               travels in a link).
    ekPatch(selector, html)    Python -> page: tile.patch(selector, html)
                               replaces the inside of every match (outer=True:
                               the elements themselves), without redrawing
                               the page or moving its scroll. A rebuild
                               (resize, theme) replays the patches.
    ekready                    an event on document once the shell, ekTouch,
                               the bridge and extra_js have all run;
                               window.ekIsReady is then true, and
                               ekWhenReady(fn) runs fn now or at ready.

extra_js (tiles.Code, tiles.Cards, Feed and the rest take it) runs after
the shell, so it can use ekTouch, ekSend and ekPatch straight away. Script
that still rides in extra_css (the older style-tag trick) runs before the
shell: wait for ekready there, without polling:

    if (window.ekIsReady) { start(); } else { document.addEventListener('ekready', start); }

Why messages queue (2026-11-26): the old UIWebView keeps only the last of
several links set in one tick, so a page that sent two at once lost one.
ekSend sends one link every SEND_GAP_MS.
"""
import json
from urllib.parse import unquote

# ---- Settings (editable) ---------------------------------------------------

SEND_GAP_MS = 40                 # ms between queued messages (one link per tick)

# ---- Contracts -----------------------------------------------------------------

MESSAGE_PATH = 'msg/'            # editorkit-code://msg/<JSON>, after the scheme


def parse_message(rest):
    """(name, data) from a link's path after the scheme ('msg/...'), or None
    when it is not a message or cannot be read."""
    if not rest.startswith(MESSAGE_PATH):
        return None
    try:
        message = json.loads(unquote(rest[len(MESSAGE_PATH):]))
    except ValueError:
        return None
    if not isinstance(message, dict) or not isinstance(message.get('name'), str):
        return None
    return message['name'], message.get('data')


def safe_script(source):
    """Script that cannot end its script tag early."""
    return (source or '').replace('</script', '<\\/script').replace('</SCRIPT', '<\\/SCRIPT')


def patch_call(selector, html, outer=False):
    """The page call tile.patch sends (pure, for tests)."""
    return 'ekPatch(%s, %s, %s)' % (json.dumps(selector), json.dumps(html), 'true' if outer else 'false')


# ---- Page side ------------------------------------------------------------------

SCRIPT = r"""
/* The page side of editorkit's bridge (bridge.py says why and how).
   Role: present · Part of: editorkit/web */
var ekOutbox = [];
var ekSending = false;
function ekFlush() {
  if (!ekOutbox.length) { ekSending = false; return; }
  ekSending = true;
  window.location.href = ekOutbox.shift();
  setTimeout(ekFlush, __GAP__);
}
function ekSend(name, data) {
  var message = {name: String(name), data: data === undefined ? null : data};
  ekOutbox.push(SCHEME + 'msg/' + encodeURIComponent(JSON.stringify(message)));
  if (!ekSending) { ekSending = true; setTimeout(ekFlush, 0); }
}
function ekPatch(selector, html, outer) {
  var found = document.querySelectorAll(selector);
  for (var i = 0; i < found.length; i++) {
    if (outer) { found[i].outerHTML = html; } else { found[i].innerHTML = html; }
  }
  if (typeof hangIndents === 'function') { hangIndents(); }
  return found.length;
}
window.ekSend = ekSend;
window.ekPatch = ekPatch;
""".replace('__GAP__', str(SEND_GAP_MS))

READY_SCRIPT = r"""
/* Last in the shell: everything above has run. */
window.ekIsReady = true;
window.ekWhenReady = function (fn) {
  if (window.ekIsReady) { fn(); } else { document.addEventListener('ekready', fn); }
};
(function () {
  var event;
  try { event = new Event('ekready'); } catch (error) {
    event = document.createEvent('Event');
    event.initEvent('ekready', true, true);
  }
  document.dispatchEvent(event);
})();
"""
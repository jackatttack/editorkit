"""Touch for pages: drags and taps that land where the finger is, at any zoom.

Role: present · Part of: editorkit/web · Pure

SCRIPT rides in every page shell (codeview.page_html), so every editorkit
page has window.ekTouch. It is the touch handling algebrakit's board and
mathskit's charts worked out on device, made shareable (2026-11-26).

Why it is needed. Pythonista's ui.WebView is the old UIWebView, and
editorkit's pinch zoom is CSS zoom on the page. There, a touch's
clientX/Y can sit well off the page's own measure (worst after a rebuild:
zoomed and scrolled back), while two things stay true: WebKit hands the
touch to the right element, and the finger's movement is right once
divided by the page zoom. So ekTouch never asks where a finger is:

- a tap acts on the element it landed on (mark tappable things with an
  attribute, data-t by default, and read it back);
- a drag starts on a marked handle (data-h by default) and reports how far
  the finger has moved since, in CSS pixels;
- the element a drag started on must stay in the page until the finger
  lifts: a removed element stops its touch reaching the page. Redraw
  everything else freely; move handles, never rebuild them mid-drag.

The page side, in JavaScript:

    ekTouch.surface(element, {
      grab: function (id, node) { return true; },     // start dragging handle id?
      move: function (id, dx, dy) { ... },            // CSS px since the finger went down
      drop: function (id, moved) { ... },             // the finger lifted
      tapped: function (key, node) { ... },           // a data-t element was tapped
      handleTapped: function (id, node) { ... }       // a handle touched without moving
    });                                               // options: handle, tap, slop

    ekTouch.buttons('data-my-button', function (node) { ... });
        // page-handled buttons: act on finger-up (preventDefault, so the
        // shell's fast tap stands aside); click is the fallback, guarded
        // for 700 ms; a drift past slop is a scroll, not a tap.

    ekTouch.pageZoom(el)          screen points per CSS pixel up the tree
    ekTouch.measure(el)           {zoom, rect}: rect units per CSS pixel too
    ekTouch.anchor(touch, node)   offset from a stray clientX/Y to node's centre
    ekTouch.closest(node, attribute, stop)

A drawing in its own units (an SVG viewBox) converts a move with
dx * drawingWidth / element.offsetWidth. Guide: library web-views.
"""

SCRIPT = r"""
/* ekTouch: drags and taps by element, never by position.
   Role: present · Part of: editorkit/web
   Gives pages window.ekTouch (touch.py says why and how). */
(function () {
  if (window.ekTouch) { return; }
  var SLOP = 10;            // px a tap may drift before it is a drag or a scroll
  var CLICK_GUARD = 700;    // ms after a touch during which the browser's click is ignored

  // Screen points per CSS pixel: CSS zoom multiplied up the tree.
  function pageZoom(el) {
    var zoom = 1;
    for (var node = el; node && node.nodeType === 1; node = node.parentNode) {
      var value = parseFloat(window.getComputedStyle(node).zoom);
      if (value > 0) { zoom *= value; }
    }
    return zoom || 1;
  }

  // zoom as above; rect: getBoundingClientRect units per CSS pixel (this
  // old WebKit may or may not apply the zoom to rects, so it is measured).
  function measure(el) {
    var width = el.offsetWidth;
    var rect = width ? el.getBoundingClientRect().width / width : 1;
    return {zoom: pageZoom(el), rect: rect || 1};
  }

  // [0, 0] when the touch lands on node; else the offset from the touch to
  // node's centre, to add to every reading of that touch.
  function anchor(touch, node) {
    var r = node && node.getBoundingClientRect ? node.getBoundingClientRect() : null;
    if (!r || !r.width) { return [0, 0]; }
    var x = touch.clientX, y = touch.clientY, slack = 4;
    if (x >= r.left - slack && x <= r.right + slack && y >= r.top - slack && y <= r.bottom + slack) {
      return [0, 0];
    }
    return [r.left + r.width / 2 - x, r.top + r.height / 2 - y];
  }

  // The nearest element from node up to (not past) stop carrying attribute.
  function closest(node, attribute, stop) {
    if (node && node.nodeType !== 1) { node = node.parentNode; }
    while (node && node !== stop && node.nodeType === 1) {
      if (node.getAttribute && node.getAttribute(attribute) !== null) { return node; }
      node = node.parentNode;
    }
    return null;
  }

  function noop() {}

  // One finger on el: drag handles, tap marked things. See touch.py.
  function surface(el, options) {
    options = options || {};
    var handleAttr = options.handle || 'data-h';
    var tapAttr = options.tap || 'data-t';
    var slop = options.slop || SLOP;
    var grab = options.grab || function () { return true; };
    var move = options.move || noop, drop = options.drop || noop;
    var tapped = options.tapped || noop, handleTapped = options.handleTapped || noop;
    var drag = null, touch = null, lastTouch = 0;

    el.addEventListener('touchstart', function (event) {
      if (event.touches.length !== 1) { drag = null; touch = null; return; }
      var finger = event.touches[0];
      var handle = closest(event.target, handleAttr, el);
      if (handle && grab(handle.getAttribute(handleAttr), handle)) {
        drag = {id: handle.getAttribute(handleAttr), node: handle, x: finger.clientX, y: finger.clientY,
                zoom: pageZoom(el), moved: false};
        touch = null;
        event.preventDefault();          // hold the page still for a drag
        event.stopPropagation();         // and keep it from the page's pinch
        return;
      }
      var hit = closest(event.target, tapAttr, el);
      touch = {node: hit, x: finger.clientX, y: finger.clientY, moved: false};
    }, {passive: false});

    el.addEventListener('touchmove', function (event) {
      var finger = event.touches[0];
      if (!finger) { return; }
      if (drag) {
        var dx = finger.clientX - drag.x, dy = finger.clientY - drag.y;
        if (Math.abs(dx) > slop || Math.abs(dy) > slop) { drag.moved = true; }
        event.preventDefault();
        event.stopPropagation();
        if (drag.moved) { move(drag.id, dx / drag.zoom, dy / drag.zoom, drag.node); }
        return;
      }
      if (touch && (Math.abs(finger.clientX - touch.x) > slop || Math.abs(finger.clientY - touch.y) > slop)) {
        touch.moved = true;              // a scroll, not a tap
      }
    }, {passive: false});

    el.addEventListener('touchend', function (event) {
      lastTouch = Date.now();
      if (drag) {
        var was = drag;
        drag = null;
        event.preventDefault();
        if (was.moved) { drop(was.id, true, was.node); } else { handleTapped(was.id, was.node); drop(was.id, false, was.node); }
        return;
      }
      var tap = touch;
      touch = null;
      if (tap && !tap.moved && tap.node) {
        event.preventDefault();          // the shell's fast tap stands aside
        tapped(tap.node.getAttribute(tapAttr), tap.node);
      }
    }, {passive: false});

    el.addEventListener('touchcancel', function () {
      if (drag) { var was = drag; drag = null; drop(was.id, was.moved, was.node); }
      touch = null;
    });

    // Fallback for a click the browser sends (a touch the page did not see).
    el.addEventListener('click', function (event) {
      if (Date.now() - lastTouch < CLICK_GUARD) { return; }
      var handle = closest(event.target, handleAttr, el);
      if (handle) { handleTapped(handle.getAttribute(handleAttr), handle); return; }
      var hit = closest(event.target, tapAttr, el);
      if (hit) { tapped(hit.getAttribute(tapAttr), hit); }
    });

    return {busy: function () { return drag !== null; }};
  }

  // Page-handled buttons anywhere in the document, found by attribute.
  function buttons(attribute, act, slop) {
    slop = slop || SLOP;
    var pressed = null, lastPress = 0;
    function target(event) { return closest(event.target, attribute, null); }
    document.addEventListener('touchstart', function (event) {
      var node = target(event);
      pressed = node && event.touches.length === 1
        ? {node: node, x: event.touches[0].clientX, y: event.touches[0].clientY} : null;
    }, true);
    document.addEventListener('touchmove', function (event) {
      var finger = event.touches[0];
      if (pressed && finger && (Math.abs(finger.clientX - pressed.x) > slop || Math.abs(finger.clientY - pressed.y) > slop)) {
        pressed = null;
      }
    }, true);
    document.addEventListener('touchend', function (event) {
      if (!pressed) { return; }
      var was = pressed;
      pressed = null;
      event.preventDefault();
      lastPress = Date.now();
      act(was.node);
    }, true);
    document.addEventListener('click', function (event) {
      var node = target(event);
      if (!node || Date.now() - lastPress < CLICK_GUARD) { return; }
      act(node);
    }, true);
  }

  window.ekTouch = {pageZoom: pageZoom, measure: measure, anchor: anchor, closest: closest,
                    surface: surface, buttons: buttons, version: 1};
})();
"""
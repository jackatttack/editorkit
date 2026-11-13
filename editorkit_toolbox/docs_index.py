"""The docs index: Pythonista's Documentation.inv, parsed and searched, and
an entry's own part of its Sphinx page, pulled out for the card kit.

The inventory is plain text, one line per documented name:

    name<TAB>kind<TAB>page            ui.View  class  py3/ios/ui.html

    entries = docs_index.parse(text)
    docs_index.search(entries, 'view add')        # [Entry('ui.View.add_subview', ...)]
    signature, body = docs_index.find_section(html, 'ui.View')
    docs_index.summary(body)                       # its first sentence, as text

Sphinx marks each entry by id: a <dt id="ui.View"> (the signature) then its
<dd> (the text) for functions, classes and methods; a section or div with
id "module-ui" for a module. Pure (no ui, no files):
apps/deck/tests/smoke_docs_index.py checks it.
"""
import html as html_module
import re
from collections import namedtuple


Entry = namedtuple('Entry', 'name kind page')

MAX_RESULTS = 60
SUMMARY_LENGTH = 160


# --- The inventory --------------------------------------------------------------

def parse(text):
    entries = []
    for line in text.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3 and parts[0] and parts[2]:
            entries.append(Entry(parts[0], parts[1], parts[2]))
    return entries


def rank(name, first):
    """Lower is better: the exact name, then a last part equal to the first
    word (View finds ui.View), then a last part starting with it, then a
    name starting with it, then anything containing it; shorter names first."""
    low = name.lower()
    last = low.rsplit('.', 1)[-1]
    if low == first:
        tier = 0
    elif last == first:
        tier = 1
    elif last.startswith(first):
        tier = 2
    elif low.startswith(first):
        tier = 3
    else:
        tier = 4
    return (tier, len(low), low)


def search(entries, term, limit=MAX_RESULTS):
    """Entries whose names hold every typed word (any case, any order), best first."""
    words = term.lower().split()
    if not words:
        return []
    found = [entry for entry in entries
             if all(word in entry.name.lower() for word in words)]
    found.sort(key=lambda entry: rank(entry.name, words[0]))
    return found[:limit]


def named(entries, names):
    """The entries with exactly these names, in the order given (the starters)."""
    by_name = {}
    for entry in entries:
        by_name.setdefault(entry.name, entry)
    return [by_name[name] for name in names if name in by_name]


# --- An entry's part of its page ---------------------------------------------------

def inner(html, start, tag):
    """The inner HTML of the <tag ...> element opening at start, nested
    elements of the same tag included."""
    pattern = re.compile(r'<(/?)%s\b[^>]*>' % tag, re.IGNORECASE)
    depth = 0
    content_start = None
    for match in pattern.finditer(html, start):
        if match.group(1):
            depth -= 1
            if depth == 0:
                return html[content_start:match.start()]
        else:
            depth += 1
            if content_start is None:
                content_start = match.end()
    return html[content_start:] if content_start is not None else ''


def find_section(html, anchor):
    """(signature HTML, body HTML) for the entry with this id; ('', '') when
    the page has no such id."""
    found = re.search(r'<dt\b[^>]*\bid="%s"[^>]*>' % re.escape(anchor), html)
    if found:
        signature_end = html.find('</dt>', found.end())
        signature = html[found.end():signature_end] if signature_end >= 0 else ''
        body_start = html.find('<dd', max(signature_end, found.end()))
        body = inner(html, body_start, 'dd') if body_start >= 0 else ''
        return signature, body
    found = re.search(r'<(section|div)\b[^>]*\bid="(?:module-)?%s"[^>]*>' % re.escape(anchor),
                      html)
    if found:
        return '', inner(html, found.start(), found.group(1))
    return '', ''


def plain_text(fragment):
    text = re.sub(r'<[^>]+>', ' ', fragment)
    return re.sub(r'\s+', ' ', html_module.unescape(text)).strip()


def summary(body):
    """The first sentence of the first paragraph, as plain text."""
    paragraph = re.search(r'<p\b[^>]*>(.*?)</p>', body, re.DOTALL | re.IGNORECASE)
    text = plain_text(paragraph.group(1) if paragraph else body)
    sentence = re.split(r'(?<=[.!?])\s', text, 1)[0]
    if len(sentence) > SUMMARY_LENGTH:
        sentence = sentence[:SUMMARY_LENGTH - 1] + '…'
    return sentence


def replace_code(fragment, render):
    """Each <pre> block passed through render(text) -> HTML, in place. The
    text has Sphinx's own highlight markup stripped and its entities
    decoded, with indentation and blank lines kept exactly."""
    def swap(match):
        text = html_module.unescape(re.sub(r'<[^>]+>', '', match.group(1)))
        return render(text.rstrip('\n'))
    return re.sub(r'<pre\b[^>]*>(.*?)</pre>', swap, fragment, flags=re.DOTALL | re.IGNORECASE)


def clean(fragment):
    """Sphinx HTML made safe and quiet for a card: no scripts or styles, no
    ¶ header links, links kept as text."""
    fragment = re.sub(r'<(script|style)\b.*?</\1>', '', fragment, flags=re.DOTALL | re.IGNORECASE)
    fragment = re.sub(r'<a\b[^>]*class="headerlink"[^>]*>.*?</a>', '', fragment,
                      flags=re.DOTALL | re.IGNORECASE)
    fragment = re.sub(r'<a\b[^>]*>', '<span class="dc-link">', fragment, flags=re.IGNORECASE)
    fragment = re.sub(r'</a>', '</span>', fragment, flags=re.IGNORECASE)
    return fragment
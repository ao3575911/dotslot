"""Display-width model, vendored from /workspace/artifacts/slotfit/slotfit.py (experiment g).
wcwidth>=0.9 grapheme widths; tabs from the absolute column; ANSI = 0 cells."""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass
from wcwidth import wcswidth, wcwidth

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')
ZWJ = '\u200d'

def _extends(c: str) -> bool:
    """True if c attaches to the previous cluster (zero-width joiners/marks/modifiers)."""
    o = ord(c)
    return (c == ZWJ or unicodedata.combining(c) or unicodedata.category(c) in ('Mn', 'Me')
            or 0xFE00 <= o <= 0xFE0F or 0x1F3FB <= o <= 0x1F3FF or 0xE0020 <= o <= 0xE007F)

def clusters(s: str):
    """Yield display units: ANSI escapes, tabs, and grapheme-ish clusters."""
    i, n = 0, len(s)
    while i < n:
        m = ANSI.match(s, i)
        if m:
            yield m.group(0); i = m.end(); continue
        j = i + 1
        while j < n and (_extends(s[j]) or s[j - 1] == ZWJ):
            j += 1
        # regional-indicator pair = one flag
        if 0x1F1E6 <= ord(s[i]) <= 0x1F1FF and j < n and 0x1F1E6 <= ord(s[j]) <= 0x1F1FF:
            j += 1
        yield s[i:j]; i = j

def unit_width(u: str, col: int, tab: int) -> int:
    if u == '\t':
        return tab - (col % tab)
    if u.startswith('\x1b'):
        return 0
    w = wcswidth(u)
    if w < 0:  # contains a control char: count printable parts only
        w = sum(max(wcwidth(c), 0) for c in u)
    return w

def legacy_ends(parts, tab=8):
    """Per-part end columns under per-codepoint wcwidth (pyte, older xterm, many
    TUI libs): a ZWJ family, skin-tone emoji or flag counts 4-6 cells, VS16 adds 0."""
    col, ends = 0, []
    for text, _ in parts:
        i = 0
        while i < len(text):
            m = ANSI.match(text, i)
            if m:
                i = m.end(); continue
            c = text[i]
            col += tab - (col % tab) if c == '\t' else max(wcwidth(c), 0)
            i += 1
        ends.append(col)
    return ends

@dataclass
class Cell:
    text: str; col: int; width: int; src: str   # src: 'line' | slot name

def layout(parts, tab=8):
    """parts: [(text, src)] -> list[Cell] with absolute columns."""
    cells, col = [], 0
    for text, src in parts:
        for u in clusters(text):
            w = unit_width(u, col, tab)
            cells.append(Cell(u, col, w, src)); col += w
    return cells

def _end(_c, start, s, tab):
    col = start
    for u in clusters(s):
        col += unit_width(u, col, tab)
    return col - start

def display_width(s: str, start: int = 0, tab: int = 8) -> int:
    """Cells s occupies when it starts at column `start` (tabs depend on start)."""
    return _end(None, start, s, tab)

def wrap_point(cells, target):
    """Index of first cell that does not fit in `target` columns, or None."""
    for i, c in enumerate(cells):
        if c.col + c.width > target:
            return i
    return None

def preview(cells, target):
    k = wrap_point(cells, target)
    if k is None:
        return None
    straddle = cells[k].width == 2 and cells[k].col == target - 1
    vis = lambda cs: ''.join(' ' * c.width if c.text == '\t' else c.text for c in cs)
    hard = (vis(cells[:k]), vis(cells[k:]))
    # word wrap: last whitespace at or before k
    b = next((i for i in range(k, -1, -1) if cells[i].text in (' ', '\t')), None)
    if b is None or b == 0:
        word = hard; moved = None; how = 'no space before the edge: falls back to a hard break'
    else:
        line1 = vis(cells[:b]).rstrip(' ')
        rest = cells[b + 1:]
        line2 = vis(rest)
        moved = line2.split(' ')[0] if line2 else ''
        word = (line1, line2); how = f'word "{moved}" moves to the next line'
    return dict(target=target, hard_break_col=cells[k].col, hard=hard,
                straddle=straddle, word=word, moved_word=moved, note=how)


def cells(s: str) -> int:
    """Cells of s at column 0 ignoring tab-stop position (slot interiors forbid tabs)."""
    return display_width(s, 0)

def cut(s: str, n: int):
    """Longest prefix of s that fits in n cells -> (prefix, its cells)."""
    out, w = [], 0
    for u in clusters(s):
        uw = unit_width(u, w, 8)
        if w + uw > n: break
        out.append(u); w += uw
    return ''.join(out), w

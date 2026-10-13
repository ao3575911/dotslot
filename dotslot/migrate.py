"""Migrate v0.1 slots (`=` headers, space padding) to the current syntax, keeping every slot's width.
    <./status   >      -> <./status:__>       named, empty
    <./status=done >   -> <./status:done_>    named, filled
    <./~=42  >         -> <./~:42__>          policy, unnamed
    <./=42  >          -> <./42___>           unnamed (the '=' cell becomes padding)
    <./|more text >    -> <./|more text_>     continuation
Slots already in the current syntax (header ':' or '_' padding or escapes) are left alone, so migrate is idempotent."""
from __future__ import annotations
import re
from .core import SLOT, HEADER, IDENT, escape, markers_for, comment_start
from .width import cells

_FILLED = re.compile(rf'^({IDENT})?([!~+]?)=(.*)$')
_NAMED = re.compile(rf'^({IDENT})([!~+]?)( +)$')
_POL = re.compile(r'^([!~+])( +)$')

def convert(interior: str, pad: str = '_'):
    """-> new interior, or None when it is not a v0.1 slot. Raises ValueError when the width cannot be kept."""
    s = interior
    if not s or s.endswith('_') or '\\' in s or '\t' in s or HEADER.match(s): return None
    if s.strip(' ') == '':
        return pad * len(s) if pad != ' ' else None
    if s.startswith('|'):
        body = s[1:].rstrip(' ')
        new = '|' + escape(body, False) if body else '|'
    elif (m := _FILLED.match(s)):
        name, pol, val = m.group(1) or '', m.group(2), m.group(3).rstrip(' ')
        header = f'{name}{pol}:' if (name or pol) else ''
        new = header + escape(val, not header)
    elif (m := _NAMED.match(s)) or (m := _POL.match(s)):
        new = ''.join(g for g in m.groups()[:-1] if g) + ':'
    else:
        return None
    w, n = cells(s), cells(new)
    if n > w: raise ValueError(f'escaped form {new!r} is wider than the slot ({n} > {w} cells)')
    out = new + pad * (w - n)
    return None if out == s else out

def migrate_text(text: str, path: str = '-', mode: str = 'auto', pad: str = '_'):
    """-> (new_text, changes, problems); changes/problems are lists of (line, col, old, new|message)."""
    markers = markers_for(path, mode)
    lines, changes, problems = text.split('\n'), [], []
    for i, ln in enumerate(lines):
        cpos = comment_start(ln, markers) if markers else -1
        out, last = [], 0
        for m in SLOT.finditer(ln):
            if markers is not None and not (0 <= cpos < m.start()): continue
            try: new = convert(m.group(1), pad)
            except ValueError as e:
                problems.append((i + 1, m.start(), m.group(0), str(e))); continue
            if new is None: continue
            out.append(ln[last:m.start()] + '<./' + new + '>'); last = m.end()
            changes.append((i + 1, m.start(), m.group(0), '<./' + new + '>'))
        if out: lines[i] = ''.join(out) + ln[last:]
    return '\n'.join(lines), changes, problems

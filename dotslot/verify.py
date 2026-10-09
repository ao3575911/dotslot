"""Fill-safe verification: prove that only slot interiors changed between two texts."""
from __future__ import annotations
import difflib
from .core import scan_text

def _skeleton(text, slots):
    lines = text.split('\n')
    spans = {}
    for s in slots:
        key = s.name or f'@{s.index}'
        spans.setdefault(s.line, []).append((s.start, s.end, f'⟦{key}⟧'))
        for c in s.conts:
            spans.setdefault(c.line, []).append((c.start, c.end, f'⟦{key}|⟧'))
    out = []
    for i, ln in enumerate(lines):
        for st, en, tok in sorted(spans.get(i, []), reverse=True):
            ln = ln[:st] + tok + ln[en:]
        out.append(ln)
    grow = {f'⟦{s.name}|⟧' for s in slots if s.policy == 'grow' and s.name}
    col = []  # collapse repeated continuation lines of grow blocks (grow may add lines)
    for ln in out:
        if col and ln == col[-1] and any(g in ln for g in grow): continue
        col.append(ln)
    return col

def verify(base, new, path='-', mode='auto', allow=None):
    bs, bi = scan_text(base, path, mode)
    ns, ni = scan_text(new, path, mode)
    v, changed = [], []
    for sev, l, c, m in ni:
        if sev == 'E': v.append(f'line {l+1}: {m}')
    sb, sn = _skeleton(base, bs), _skeleton(new, ns)
    if sb != sn:
        d = [x for x in difflib.unified_diff(sb, sn, 'base', 'new', lineterm='', n=0)][2:]
        v.append('text outside slots changed:\n    ' + '\n    '.join(d[:12]))
    if len(bs) != len(ns):
        v.append(f'slot count changed: {len(bs)} -> {len(ns)}')
    for a, b in zip(bs, ns):
        key = a.name or f'@{a.index}'
        if (a.name, a.policy) != (b.name, b.policy):
            v.append(f'{key}: header changed {a.header!r} -> {b.header!r}')
            continue
        if a.policy != 'grow':
            if a.width != b.width:
                v.append(f'{key}: width changed {a.width} -> {b.width} (closing > moved)')
            if len(a.conts) != len(b.conts):
                v.append(f'{key}: block height changed {1+len(a.conts)} -> {1+len(b.conts)}')
        va = a.block_value() if a.conts else (a.value or '')
        vb = b.block_value() if b.conts else (b.value or '')
        if va != vb:
            changed.append(dict(slot=key, line=b.line + 1, before=va, after=vb))
            if allow is not None and key not in allow:
                v.append(f'{key}: changed but not in the allowed list')
    return dict(ok=not v, changed=changed, violations=v, slots=len(ns))

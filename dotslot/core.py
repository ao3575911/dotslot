r"""dotslot v0.2 — fixed-width fill-in slots `<./________>`.

Interior (between `<./` and `>`), width W = its display cells in the file:
    empty      <./________>           padding only ('_' or ' ')
    named      <./status:____>        IDENT [policy] ':' padding
    filled     <./status:done__>      header + value + padding
               <./done_____>          unnamed value: no header, no cost
    policy     <./~:______>           unnamed slot with a policy
    cont       <./|more text___>      block continuation
    policy     !  error (default)   ~  ellipsis   +  grow
Escapes inside a value: \\  \<  \>  \_  \:  \|   (the tool writes them for you)
"""
from __future__ import annotations
import os, re
from dataclasses import dataclass, field
from .width import cells, cut, display_width

SLOT = re.compile(r'<\./((?:\\.|[^<>\\\n])*)>')
OPEN = re.compile(r'<\./')
IDENT = r'[A-Za-z_][\w-]*'
HEADER = re.compile(rf'(?:({IDENT})([!~+]?)|([!~+])):')
PAD = ' _'
POLICY = {'!': 'error', '~': 'ellipsis', '+': 'grow', '': None}
MARK = {v: k for k, v in POLICY.items() if v}
PROSE = {'.md', '.markdown', '.txt', '.text', '.rst', '.adoc', '.org', '.slot'}
COMMENT = {
    **{e: ('#',) for e in '.py .sh .bash .zsh .yaml .yml .toml .rb .pl .r .mk .cfg .conf .dockerfile'.split()},
    **{e: ('//', '/*') for e in '.js .mjs .cjs .ts .tsx .jsx .c .h .cc .cpp .go .rs .java .kt .swift .cs .css .scss .json5'.split()},
    **{e: ('--',) for e in '.sql .lua .hs .elm'.split()},
    **{e: (';',) for e in '.ini .el .lisp .clj .scm .asm'.split()},
    **{e: ('<!--',) for e in '.html .htm .xml .svg .vue'.split()},
}
ALL_MARKERS = ('#', '//', '/*', '--', ';', '<!--')
CLOSERS = ('-->', '*/')

class SlotError(Exception):
    pass

def unescape(s): return re.sub(r'\\(.)', r'\1', s)

def escape(v: str, unnamed: bool) -> str:
    v = v.replace('\\', '\\\\').replace('<', '\\<').replace('>', '\\>')
    if unnamed:
        if v[:1] == '|': v = '\\' + v
        m = HEADER.match(v)
        if m: v = v[:m.end() - 1] + '\\:' + v[m.end():]
    if v and v[-1] in PAD: v = v[:-1] + '\\' + v[-1]
    return v

def split_pad(s):
    """-> (body, padding) where padding is the trailing run of unescaped ' '/'_'."""
    i = len(s)
    while i > 0 and s[i - 1] in PAD:
        # stop if this pad char is escaped (odd number of backslashes before it)
        j, bs = i - 2, 0
        while j >= 0 and s[j] == '\\': bs += 1; j -= 1
        if bs % 2: break
        i -= 1
    return s[:i], s[i:]

@dataclass
class Slot:
    line: int; start: int; end: int; col: int; interior: str
    kind: str                       # empty | named | filled | cont
    name: str | None = None
    policy: str | None = None
    header: str = ''                # raw header incl ':' (or '|' for cont)
    raw_value: str = ''             # escaped form as in the file
    pad: str = '_'
    in_comment: bool = False
    role: str = 'inline'
    conts: list = field(default_factory=list)
    index: int = 0

    @property
    def width(self): return cells(self.interior)
    @property
    def capacity(self): return self.width - cells(self.header)
    @property
    def value(self): return unescape(self.raw_value) if self.raw_value else None
    @property
    def filled(self): return bool(self.raw_value)
    def block_value(self):
        return ' '.join(p for p in [self.value or ''] + [c.value or '' for c in self.conts] if p)

def parse_interior(s: str):
    if '\t' in s: return None
    body, padding = split_pad(s)
    pad = '_' if '_' in padding else (' ' if padding else '_')
    if body.startswith('|'):
        return dict(kind='cont', header='|', raw_value=body[1:], pad=pad)
    m = HEADER.match(body)
    if m:
        name, pol = m.group(1), POLICY[m.group(2) or m.group(3) or '']
        rest = body[m.end():]
        return dict(kind='filled' if rest else ('named' if name else 'empty'), name=name, policy=pol,
                    header=m.group(0), raw_value=rest, pad=pad)
    if not body:
        return dict(kind='empty', pad=pad) if padding else None
    return dict(kind='filled', raw_value=body, pad=pad)

def comment_start(line: str, markers) -> int:
    """Index of the first comment marker outside '…' "…" `…` strings, or -1."""
    q, i, n = None, 0, len(line)
    while i < n:
        c = line[i]
        if q:
            if c == '\\': i += 2; continue
            if c == q: q = None
        elif c in '"\'`':
            # treat ' as a quote only when it pairs later on the line (Rust lifetimes, prose)
            if c != "'" or line.find("'", i + 1) != -1: q = c
        else:
            for mk in markers:
                if line.startswith(mk, i): return i
        i += 1
    return -1

def markers_for(path, mode):
    ext = os.path.splitext(path or '')[1].lower()
    base = os.path.basename(path or '').lower()
    if mode == 'prose': return None
    if mode == 'auto' and (ext in PROSE or path in ('-', '/dev/stdin')): return None
    if base in ('dockerfile', 'makefile'): return ('#',)
    return COMMENT.get(ext, ALL_MARKERS)

def scan_text(text: str, path: str = '-', mode: str = 'auto'):
    lines = text.split('\n')
    markers = markers_for(path, mode)
    slots, issues = [], []
    for i, ln in enumerate(lines):
        taken = set()
        cpos = comment_start(ln, markers) if markers else -1
        for m in SLOT.finditer(ln):
            taken.add(m.start())
            col = display_width(ln[:m.start()])
            if m.group(1) == '':
                issues.append(('E', i, col, 'zero-width slot <./>')); continue
            p = parse_interior(m.group(1))
            if p is None:
                issues.append(('W', i, col, f'slot-like text {m.group(0)!r} is not a valid slot (ignored)')); continue
            if markers is not None and not (0 <= cpos < m.start()):
                issues.append(('W', i, col, f'{m.group(0)!r} is outside a comment (ignored; use --mode prose)')); continue
            s = Slot(i, m.start(), m.end(), col, m.group(1), in_comment=markers is not None, **p)
            if (os.path.splitext(path)[1].lower() in ('.md', '.markdown') and '_' in m.group(1)
                    and ln[:m.start()].count('`') % 2 == 0):
                issues.append(('W', i, col, f"{m.group(0)!r}: '_' outside a code span can render as emphasis in Markdown; wrap it in backticks"))
            if s.kind == 'cont': s.role = 'cont'
            slots.append(s)
        for m in OPEN.finditer(ln):
            if m.start() not in taken and (markers is None or 0 <= cpos < m.start()):
                issues.append(('E', i, display_width(ln[:m.start()]), "unterminated slot: '<./' without '>' on the same line"))
    by_line = {}
    for s in slots: by_line.setdefault(s.line, []).append(s)
    owned = set()
    for s in slots:
        if s.kind in ('named', 'filled') and s.name:
            j = s.line + 1
            while True:
                c = next((x for x in by_line.get(j, []) if x.kind == 'cont' and x.col == s.col), None)
                if not c: break
                if c.width != s.width:
                    issues.append(('E', j, c.col, f'block {s.name}: continuation width {c.width} != head width {s.width}')); break
                owned.add(id(c)); s.conts.append(c); j += 1
            if s.conts: s.role = 'head'
    for s in slots:
        if s.kind == 'cont' and id(s) not in owned:
            issues.append(('E', s.line, s.col, 'continuation <./|…> with no named slot directly above at the same column'))
    top = [s for s in slots if s.role != 'cont']
    widths = {}
    for k, s in enumerate(top):
        s.index = k + 1
        if s.name: widths.setdefault(s.name, set()).add(s.width)
        if s.capacity < 1 and s.policy != 'grow':
            issues.append(('E', s.line, s.col, f'{s.name or "slot"}: header leaves {s.capacity} cells for a value (width {s.width})'))
    for n, ws in widths.items():
        if len(ws) > 1: issues.append(('W', 0, 0, f'name {n!r} used with different widths {sorted(ws)}'))
    return top, issues

# ---------------------------------------------------------------- fill
def clean(v: str, block: bool):
    v = str(v)
    if block: v = re.sub(r'\s*\n\s*', ' ', v)
    if '\t' in v or '\n' in v:
        raise SlotError('value contains a tab or newline; inline slots hold one line')
    return v.rstrip(' ')

def render(header, raw, width, pad):
    body = header + raw
    return body + pad * max(width - cells(body), 0)

def cut_escaped(v, cap, unnamed, ellipsis):
    """Cut the *unescaped* value so its escaped form fits cap; prefer a word boundary for ellipsis."""
    lo, best = 0, ''
    for k in range(len(v), -1, -1):
        head = v[:k].rstrip(' ') if ellipsis else v[:k]
        e = escape(head, unnamed) + ('…' if ellipsis else '')
        if cells(e) <= cap:
            best = head; break
    if ellipsis and ' ' in best:
        wb = best[:best.rfind(' ')].rstrip(' ')
        if wb and cells(wb) >= (cap * 2) // 3: best = wb
    return escape(best, unnamed) + ('…' if ellipsis else '')

def fit_value(v, cap, policy, what, unnamed):
    e = escape(v, unnamed)
    if cells(e) <= cap: return e
    if policy == 'ellipsis':
        if cap < 2: raise SlotError(f'{what}: no room for an ellipsis')
        return cut_escaped(v, cap, unnamed, True)
    if policy == 'truncate': return cut_escaped(v, cap, unnamed, False)
    if policy == 'grow': return e
    raise SlotError(f'{what}: value is {cells(e)} cells, slot holds {cap} (overflow policy: error)')

def wrap_words(v, caps):
    words, lines, k = [w for w in v.split(' ') if w], [], 0
    for cap in caps:
        cur = ''
        while k < len(words):
            w = words[k]; cand = (cur + ' ' + w) if cur else w
            if cells(escape(cand, False)) <= cap: cur, k = cand, k + 1
            elif not cur and cells(escape(w, False)) > cap:
                head, _ = cut(w, max(cap - 1, 1))
                if not head: break
                cur, words[k] = head, w[len(head):]; break
            else: break
        lines.append(cur)
    return lines, ' '.join(words[k:])

def fill_text(text, values, path='-', mode='auto', default_policy='error', clear=(), allow=None):
    slots, issues = scan_text(text, path, mode)
    errs = [x for x in issues if x[0] == 'E']
    if errs: raise SlotError('; '.join(f'line {l+1}: {m}' for _, l, _, m in errs))
    lines = text.split('\n'); edits, inserts, used = [], [], set()
    for s in slots:
        key = f'@{s.index}'
        target = key if key in values or key in clear else s.name
        if target is None or (target not in values and target not in clear): continue
        if allow is not None and target not in allow:
            raise SlotError(f'{target}: not in the allowed slot list')
        if target in clear:
            used.add(target)
            for x in [s] + s.conts:
                h = x.header
                edits.append((x.line, x.start, x.end, '<./' + render(h, '', x.width, x.pad) + '>'))
            continue
        used.add(target)
        pol = s.policy or default_policy; what = s.name or key; unnamed = not s.header
        v = clean(values[target], bool(s.conts))
        if not s.conts:
            raw = fit_value(v, s.capacity, pol, what, unnamed)
            edits.append((s.line, s.start, s.end, '<./' + render(s.header, raw, s.width, s.pad) + '>'))
            continue
        rows = [s] + s.conts; caps = [r.capacity for r in rows]
        got, left = wrap_words(v, caps); extra = []
        if left:
            if pol == 'grow':
                while left:
                    more, left2 = wrap_words(left, [s.width - 1])
                    if left2 == left: raise SlotError(f'{what}: cannot wrap {left!r}')
                    extra.append(more[0]); left = left2
            elif pol == 'ellipsis':
                last = (got[-1] + ' ' + left).strip()
                got[-1] = None; edits_last = cut_escaped(last, caps[-1], False, True)
            elif pol == 'truncate': pass
            else:
                raise SlotError(f'{what}: block holds {sum(caps)} cells in {len(caps)} lines; '
                                f'{cells(left)} cells left over (overflow policy: error)')
        for r, g in zip(rows, got):
            raw = edits_last if g is None else escape(g, False)
            edits.append((r.line, r.start, r.end, '<./' + render(r.header, raw, r.width, r.pad) + '>'))
        if extra:
            last = rows[-1]; ln = lines[last.line]
            before, after = ln[:last.start], ln[last.end:]
            lead = before if not before.strip(' \t#/;*-!<') else ' ' * display_width(before)
            tail = after if after.strip() in CLOSERS or not after.strip() else ''
            inserts.append((last.line, [lead + '<./' + render('|', escape(e, False), s.width, last.pad) + '>' + tail for e in extra]))
    missing = [k for k in list(values) + list(clear) if k not in used]
    if missing: raise SlotError(f'no slot named {", ".join(missing)}')
    for li, st, en, new in sorted(edits, key=lambda e: (e[0], -e[1])):
        lines[li] = lines[li][:st] + new + lines[li][en:]
    for after, new in sorted(inserts, reverse=True):
        lines[after + 1:after + 1] = new
    return '\n'.join(lines)

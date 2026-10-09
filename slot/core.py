"""slot — fixed-width fill-in slots written as `<./    >`.

Grammar of the interior (the text between `<./` and `>`), width W = its display cells
(for an empty slot that is simply the number of characters, name included):

    empty     <./      >            spaces only
    named     <./name  >            identifier [policy] spaces
    filled    <./name=value  >      [identifier][policy] '=' value padding
              <./=value  >          unnamed, filled
    cont      <./|more text  >      continuation line of a block slot
    policy    !  error (default)   ~  ellipsis   +  grow
"""
from __future__ import annotations
import os, re
from dataclasses import dataclass, field
from .width import cells, cut, display_width

SLOT = re.compile(r'<\./([^<>\n]*)>')
OPEN = re.compile(r'<\./')
IDENT = r'[A-Za-z_][\w-]*'
R_EMPTY = re.compile(r'( +)$')
R_CONT = re.compile(r'\|(.*?)( *)$')
R_NAMED = re.compile(rf'({IDENT})([!~+]?)( *)$')
R_FILLED = re.compile(rf'({IDENT})?([!~+]?)=(.*?)( *)$')
POLICY = {'!': 'error', '~': 'ellipsis', '+': 'grow', '': None}
MARK = {v: k for k, v in POLICY.items() if v}

COMMENT = {  # extension -> line comment / block-comment openers
    **{e: ('#',) for e in '.py .sh .bash .zsh .yaml .yml .toml .rb .pl .r .mk .cfg .conf'.split()},
    **{e: ('//', '/*') for e in '.js .ts .tsx .jsx .c .h .cc .cpp .go .rs .java .kt .swift .cs .css'.split()},
    **{e: ('--',) for e in '.sql .lua .hs .elm'.split()},
    **{e: (';',) for e in '.ini .el .lisp .clj .scm .asm'.split()},
    **{e: ('<!--',) for e in '.html .htm .xml .svg .vue'.split()},
}
CLOSERS = ('-->', '*/')

class SlotError(Exception):
    pass

@dataclass
class Slot:
    line: int            # 0-based line index
    start: int           # char index of '<'
    end: int             # char index after '>'
    col: int             # display column of '<' (tabs expanded)
    interior: str
    kind: str            # empty | named | filled | cont
    name: str | None = None
    policy: str | None = None
    value: str | None = None
    in_comment: bool = False
    role: str = 'inline' # inline | head | cont
    conts: list = field(default_factory=list)
    index: int = 0       # 1-based scan order (for @N addressing)

    @property
    def width(self): return cells(self.interior)
    @property
    def prefix(self):
        return '|' if self.kind == 'cont' else (self.name or '') + MARK.get(self.policy, '')
    @property
    def capacity(self):  # cells available for a value
        return self.width - cells(self.prefix) - (0 if self.kind == 'cont' else 1)
    @property
    def filled(self): return self.kind == 'filled' or (self.kind == 'cont' and bool(self.value))
    def block_value(self):
        parts = [self.value or ''] + [c.value or '' for c in self.conts]
        return ' '.join(p for p in parts if p)

def parse_interior(s: str):
    if '\t' in s:
        return None
    if m := R_EMPTY.fullmatch(s):
        return dict(kind='empty')
    if m := R_CONT.fullmatch(s):
        return dict(kind='cont', value=m.group(1))
    if m := R_NAMED.fullmatch(s):
        return dict(kind='named', name=m.group(1), policy=POLICY[m.group(2)])
    if m := R_FILLED.fullmatch(s):
        return dict(kind='filled', name=m.group(1), policy=POLICY[m.group(2)], value=m.group(3))
    return None

def comment_markers(path, mode):
    if mode == 'prose': return None
    ext = os.path.splitext(path or '')[1].lower()
    if mode == 'code' and ext not in COMMENT: return ('#', '//', '/*', '--', ';', '<!--')
    return COMMENT.get(ext) if mode in ('auto', 'code') else None

def scan_text(text: str, path: str = '-', mode: str = 'auto'):
    """-> (slots, issues). issues: list of (severity, line0, col, msg)."""
    lines = text.split('\n')
    markers = comment_markers(path, mode)
    slots, issues = [], []
    for i, ln in enumerate(lines):
        taken = set()
        for m in SLOT.finditer(ln):
            p = parse_interior(m.group(1))
            col = display_width(ln[:m.start()])
            if m.group(1) == '':
                issues.append(('E', i, col, 'zero-width slot <./>'))
                taken.add(m.start()); continue
            if p is None:
                issues.append(('W', i, col, f'slot-like text {m.group(0)!r} is not a valid slot (ignored)'))
                taken.add(m.start()); continue
            in_c = False
            if markers is not None:
                pre = ln[:m.start()]
                in_c = any(k in pre for k in markers)
                if not in_c:
                    issues.append(('W', i, col, f'{m.group(0)!r} is outside a comment in a code file (ignored)'))
                    taken.add(m.start()); continue
            s = Slot(i, m.start(), m.end(), col, m.group(1), in_comment=in_c, **p)
            if s.kind == 'cont': s.role = 'cont'
            slots.append(s); taken.add(m.start())
        for m in OPEN.finditer(ln):
            if m.start() not in taken:
                issues.append(('E', i, display_width(ln[:m.start()]), "unterminated slot: '<./' without '>' on the same line"))
    # blocks: a named/filled head followed by `<./|…>` lines at the same column and width
    by_line = {}
    for s in slots: by_line.setdefault(s.line, []).append(s)
    for s in slots:
        if s.kind == 'cont' and s.role == 'cont' and not getattr(s, '_owned', False):
            pass
        if s.kind in ('named', 'filled') and s.name:
            j = s.line + 1
            while True:
                c = next((x for x in by_line.get(j, []) if x.kind == 'cont' and x.col == s.col), None)
                if not c: break
                if c.width != s.width:
                    issues.append(('E', j, c.col, f'block {s.name}: continuation width {c.width} != head width {s.width}'))
                    break
                c._owned = True; s.conts.append(c); j += 1
            if s.conts: s.role = 'head'
    for s in slots:
        if s.kind == 'cont' and not getattr(s, '_owned', False):
            issues.append(('E', s.line, s.col, 'continuation <./|…> with no named slot directly above at the same column'))
    widths = {}
    for k, s in enumerate(x for x in slots if x.role != 'cont'):
        s.index = k + 1
        if s.name: widths.setdefault(s.name, set()).add(s.width)
    for n, ws in widths.items():
        if len(ws) > 1: issues.append(('W', 0, 0, f'name {n!r} used with different widths {sorted(ws)}'))
    for s in slots:
        if s.role != 'cont' and s.capacity < 1:
            issues.append(('W', s.line, s.col, f'{s.name or "slot"}: name leaves {s.capacity} cells for a value (width {s.width})'))
    return [s for s in slots if s.role != 'cont'], issues

# ---------------------------------------------------------------- fill
def clean(v: str, escape: bool, block: bool):
    if block: v = re.sub(r'\s*\n\s*', ' ', v)
    if escape:
        v = v.replace('<', '‹').replace('>', '›').replace('\t', ' ').replace('\n', ' ')
    bad = [c for c in '<>\t\n' if c in v]
    if bad:
        raise SlotError(f'value contains {bad!r}, which cannot sit inside a slot (use --escape)')
    if v != v.rstrip(' '):
        v = v.rstrip(' ')  # trailing spaces are padding by definition
    return v

def render(prefix, v, width, sep='='):
    body = prefix + sep + v
    return body + ' ' * max(width - cells(body), 0)

def fit_one(v, cap, policy, what):
    w = cells(v)
    if w <= cap: return v
    if policy == 'ellipsis':
        if cap < 1: raise SlotError(f'{what}: no room for an ellipsis')
        return cut(v, cap - 1)[0] + '…'
    if policy == 'truncate': return cut(v, cap)[0]
    if policy == 'grow': return v
    raise SlotError(f'{what}: value is {w} cells, slot holds {cap} (overflow policy: error)')

def wrap_words(v, caps):
    """Greedy word wrap into successive capacities; returns (lines, leftover_text)."""
    words, lines, k = v.split(' '), [], 0
    words = [w for w in words if w]
    for cap in caps:
        cur = ''
        while k < len(words):
            w = words[k]
            cand = (cur + ' ' + w) if cur else w
            if cells(cand) <= cap:
                cur, k = cand, k + 1
            elif not cur and cells(w) > cap:      # word longer than a line: hard split
                head, _ = cut(w, cap)
                if not head: break
                cur, words[k] = head, w[len(head):]
                break
            else:
                break
        lines.append(cur)
    return lines, ' '.join(words[k:])

def fill_text(text, values, path='-', mode='auto', default_policy='error', escape=False, clear=()):
    """values: {name or '@N': value}. Returns new text. Raises SlotError."""
    slots, issues = scan_text(text, path, mode)
    errs = [x for x in issues if x[0] == 'E']
    if errs: raise SlotError('; '.join(f'line {l+1}: {m}' for _, l, _, m in errs))
    lines = text.split('\n')
    edits = []   # (line, start, end, new) ; inserts: (after_line, [new lines])
    inserts = []
    used = set()
    for s in slots:
        key = f'@{s.index}'
        if key in values: v = values[key]; used.add(key)
        elif s.name and s.name in values: v = values[s.name]; used.add(s.name)
        elif (s.name and s.name in clear) or key in clear:
            for x in [s] + s.conts:
                pre = x.prefix if x is not s else (s.name or '') + MARK.get(s.policy, '')
                edits.append((x.line, x.start, x.end, '<./' + pre + ' ' * (x.width - cells(pre)) + '>'))
            continue
        else: continue
        pol = s.policy or default_policy
        what = s.name or key
        v = clean(str(v), escape, bool(s.conts))
        pre = (s.name or '') + MARK.get(s.policy, '')
        if not s.conts:
            vv = fit_one(v, s.capacity, pol, what)
            edits.append((s.line, s.start, s.end, '<./' + render(pre, vv, s.width) + '>'))
            continue
        caps = [s.capacity] + [c.capacity for c in s.conts]
        got, left = wrap_words(v, caps)
        rows = [s] + s.conts
        extra = []
        if left:
            if pol == 'grow':
                while left:
                    more, left2 = wrap_words(left, [s.width - 1])
                    if left2 == left: raise SlotError(f'{what}: cannot wrap {left!r}')
                    extra.append(more[0]); left = left2
            elif pol in ('ellipsis', 'truncate'):
                if pol == 'ellipsis':
                    last = got[-1] + ' ' + left if got[-1] else left
                    got[-1] = fit_one(last, caps[-1], 'ellipsis', what)
            else:
                raise SlotError(f'{what}: block holds {sum(caps)} cells in {len(caps)} lines; '
                                f'{cells(left)} cells left over (overflow policy: error)')
        for r, g in zip(rows, got):
            if r is s: edits.append((r.line, r.start, r.end, '<./' + render(pre, g, r.width) + '>'))
            else: edits.append((r.line, r.start, r.end, '<./' + render('', g, r.width, sep='|') + '>'))
        if extra:
            last = rows[-1]; ln = lines[last.line]
            before, after = ln[:last.start], ln[last.end:]
            lead = before if not before.strip(' \t#/;*-!<') else ' ' * display_width(before)
            tail = after if after.strip() in CLOSERS or not after.strip() else ''
            inserts.append((last.line, [lead + '<./' + render('', e, s.width, sep='|') + '>' + tail for e in extra]))
    missing = [k for k in values if k not in used]
    if missing: raise SlotError(f'no slot named {", ".join(missing)}')
    for li, st, en, new in sorted(edits, key=lambda e: (e[0], -e[1])):
        lines[li] = lines[li][:st] + new + lines[li][en:]
    for after, new in sorted(inserts, reverse=True):
        lines[after + 1:after + 1] = new
    return '\n'.join(lines)

"""dotslot scan | fill | check | fit"""
from __future__ import annotations
import argparse, json, subprocess, sys
from .core import scan_text, fill_text, SlotError
from .verify import verify
from .width import layout, preview, legacy_ends, display_width

def read(p): return sys.stdin.read() if p == '-' else open(p, encoding='utf-8').read()

def parse_sets(items):
    out = {}
    for it in items or []:
        k, sep, v = it.partition('=')
        if not sep: raise SystemExit(f'--set needs name=value, got {it!r}')
        out[k] = v
    return out

def cmd_scan(a):
    rows = []
    for p in a.files:
        slots, issues = scan_text(read(p), p, a.mode)
        for s in slots:
            rows.append(dict(file=p, line=s.line + 1, col=s.col, index=s.index, name=s.name, role=s.role,
                             width=s.width, lines=1 + len(s.conts), capacity=s.capacity + sum(c.capacity for c in s.conts),
                             filled=s.filled, value=(s.block_value() if s.conts else s.value) if s.filled else None,
                             policy=s.policy, in_comment=s.in_comment))
        for sev, l, c, m in issues: print(f'{p}:{l+1}:{c}: {sev}: {m}', file=sys.stderr)
    if a.json: print(json.dumps(rows, ensure_ascii=False, indent=1)); return 0
    for r in rows:
        v = '' if r['value'] is None else repr(r['value'])
        print(f"{r['file']}:{r['line']}:{r['col']}  @{r['index']} {r['name'] or '-':12} {r['role']:6} "
              f"w={r['width']:<3} x{r['lines']} cap={r['capacity']:<3} {'filled' if r['filled'] else 'empty ':6} "
              f"{r['policy'] or '':8} {'#' if r['in_comment'] else ' '} {v}")
    return 0

def cmd_fill(a):
    vals = parse_sets(a.set)
    if a.json_values: vals.update(json.load(open(a.json_values)))
    rc = 0
    allow = set(a.allow.split(',')) if a.allow else None
    for p in a.files:
        try:
            out = fill_text(read(p), vals, p, a.mode, a.overflow, tuple(a.clear or ()), allow)
        except SlotError as e:
            print(f'{p}: error: {e}', file=sys.stderr); rc = 2; continue
        if a.in_place and p != '-':
            open(p, 'w', encoding='utf-8').write(out)
        else:
            sys.stdout.write(out)
    return rc

def fit_report(text, path, mode, targets, tab, show_preview):
    slots, _ = scan_text(text, path, mode)
    lines = text.split('\n'); out = []; bad = {t: 0 for t in targets}
    by_line = {}
    for s in slots:
        for x in [s] + s.conts: by_line.setdefault(x.line, []).append((s, x))
    for li in sorted(by_line):
        ln = lines[li]
        cl = layout([(ln, 'line')], tab)
        lw = cl[-1].col + cl[-1].width if cl else 0
        leg = legacy_ends([(ln, 'line')], tab)[-1]
        grows = any(h.policy == 'grow' for h, _ in by_line[li])
        for head, x in by_line[li]:
            end = display_width(ln[:x.end], 0, tab)
            st = {}
            for t in targets:
                s_ = 'over' if end > t else 'pushes' if lw > t else 'maybe' if leg > t else 'ok'
                st[t] = s_
                if s_ != 'ok': bad[t] += 1
            label = (head.name or f'@{head.index}') + ('' if x is head else f'[+{x.line - head.line}]')
            out.append(f"{path}:{li+1}: slot {label} col {x.col}..{end} (line {lw}{'' if leg == lw else f', per-codepoint {leg}'})"
                       f" {'grow' if grows else 'static'}  " + '  '.join(f'{t}:{v}' for t, v in st.items()))
            if show_preview:
                for t in targets:
                    if st[t] in ('over', 'pushes') and (p := preview(cl, t)):
                        out.append(f"    @{t}: {p['note']}" + (' (2-cell glyph straddles edge)' if p['straddle'] else ''))
                        out.append(f"      word │{p['word'][0]}\n           │{p['word'][1]}")
    return out, bad

def cmd_fit(a):
    targets = sorted(int(t) for t in a.targets.split(','))
    rc = 0
    for p in a.files:
        text = read(p)
        if a.set:
            try: text = fill_text(text, parse_sets(a.set), p, a.mode, a.overflow)
            except SlotError as e: print(f'{p}: error: {e}', file=sys.stderr); rc = 2; continue
        out, bad = fit_report(text, p, a.mode, targets, a.tab, a.preview)
        print('\n'.join(out)) if out else None
        if bad.get(a.fail_at or targets[0]): rc = max(rc, 1)
    return rc

def base_text(a, p):
    if a.base: return read(a.base)
    if a.git_base:
        r = subprocess.run(['git', 'show', f'{a.git_base}:./{p}'], capture_output=True, text=True,
                           cwd=None)
        return r.stdout if r.returncode == 0 else None   # new file: nothing to compare
    return None

def cmd_new(a):
    pol = a.policy or ''
    head = f'{a.name}{pol}:' if a.name else (f'{pol}:' if pol else '')
    if a.width < len(head) + 1: raise SystemExit(f'width {a.width} leaves no room after {head!r}')
    pre, post = a.comment, (' ' + CLOSE[a.comment.strip()] if a.comment.strip() in CLOSE else '')
    lines = [pre + '<./' + head + a.pad * (a.width - len(head)) + '>' + post]
    for _ in range(a.lines - 1):
        lines.append(pre + '<./|' + a.pad * (a.width - 1) + '>' + post)
    if a.md: lines = ['`' + l + '`' for l in lines]
    print('\n'.join(lines)); return 0

CLOSE = {'<!--': '-->', '/*': '*/'}

def cmd_repad(a):
    from .core import scan_text as sc, render
    base, text = read(a.base), read(a.files[0])
    bs, _ = sc(base, a.files[0], a.mode); ns, _ = sc(text, a.files[0], a.mode)
    if len(bs) != len(ns): print('slot count differs; cannot repad', file=sys.stderr); return 2
    lines = text.split('\n'); fixed = 0
    for b, n in sorted(zip(bs, ns), key=lambda p: (p[1].line, -p[1].start)):
        if b.width != n.width and not n.conts and b.policy != 'grow' and b.header == n.header:
            if len(n.raw_value) and __import__('dotslot.width', fromlist=['cells']).cells(n.header + n.raw_value) <= b.width:
                ln = lines[n.line]
                lines[n.line] = ln[:n.start] + '<./' + render(n.header, n.raw_value, b.width, b.pad) + '>' + ln[n.end:]
                fixed += 1
    out = '\n'.join(lines)
    if a.in_place: open(a.files[0], 'w', encoding='utf-8').write(out)
    else: sys.stdout.write(out)
    print(f'repadded {fixed} slot(s)', file=sys.stderr); return 0

def cmd_check(a):
    rc = 0
    req = set((a.require or '').split(',')) - {''}
    allow = set(a.allow.split(',')) if a.allow else None
    reports = []
    for p in a.files:
        text = read(p)
        b = base_text(a, p)
        if b is not None:
            r = verify(b, text, p, a.mode, allow); r['file'] = p; reports.append(r)
            if not a.json:
                for c in r['changed']: print(f"{p}:{c['line']}: filled {c['slot']}: {c['before']!r} -> {c['after']!r}")
                for x in r['violations']: print(f'{p}: VIOLATION: {x}')
                print(f"{p}: {'fill-safe' if r['ok'] else 'NOT fill-safe'} ({len(r['changed'])} slot(s) changed)")
            if not r['ok']: rc = 1
            continue
        slots, issues = scan_text(text, p, a.mode)
        probs = [(sev, l, c, m) for sev, l, c, m in issues]
        for s in slots:
            if (a.require_filled or (s.name in req)) and not s.filled:
                probs.append(('E', s.line, s.col, f'{s.name or "@%d" % s.index} is empty'))
        names = {s.name for s in slots}
        for n in req - names: probs.append(('E', 0, 0, f'required slot {n!r} not found'))
        if a.fit:
            out, bad = fit_report(text, p, a.mode, [a.fit], a.tab, False)
            for o in out:
                if f'{a.fit}:ok' not in o: probs.append(('E', 0, 0, 'fit: ' + o.split(': ', 1)[1]))
        for sev, l, c, m in probs:
            if not a.json: print(f'{p}:{l+1}:{c}: {sev}: {m}')
            if sev == 'E' or (a.strict and sev == 'W'): rc = 1
        if not probs and not a.json: print(f'{p}: ok ({len(slots)} slots)')
    if a.json: print(json.dumps(reports, ensure_ascii=False, indent=1))
    return rc

def main(argv=None):
    ap = argparse.ArgumentParser(prog='dotslot', description='fixed-width <./____> slots (v0.2)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    def common(sp):
        sp.add_argument('files', nargs='+')
        sp.add_argument('--mode', choices=['auto', 'prose', 'comments'], default='auto',
                        help='auto: bare slots only in prose files (.md .txt …); everything else comment-only')
    s = sub.add_parser('scan'); common(s); s.add_argument('--json', action='store_true')
    for name in ('fill', 'fit'):
        f = sub.add_parser(name); common(f)
        f.add_argument('--set', action='append', help='name=value or @N=value')
        f.add_argument('--overflow', choices=['error', 'ellipsis', 'truncate', 'grow'], default='error',
                       help='policy for slots without a !/~/+ marker')
        f.add_argument('--allow', help='comma list of slot names/@N that may be filled')
        if name == 'fill':
            f.add_argument('--json-values'); f.add_argument('-i', '--in-place', action='store_true')
            f.add_argument('--clear', action='append', help='empty a slot again (name or @N)')
        else:
            f.add_argument('--targets', default='80,100,120'); f.add_argument('--tab', type=int, default=8)
            f.add_argument('--preview', action='store_true'); f.add_argument('--fail-at', type=int)
    n = sub.add_parser('new', help='print a correctly sized slot or block')
    n.add_argument('name', nargs='?'); n.add_argument('--width', type=int, required=True)
    n.add_argument('--lines', type=int, default=1); n.add_argument('--policy', choices=['!', '~', '+'])
    n.add_argument('--comment', default='', help="prefix such as '# ' or '<!-- '"); n.add_argument('--pad', default='_')
    n.add_argument('--md', action='store_true', help='wrap in backticks (Markdown code span)')
    n.set_defaults(indent_only=False)
    r = sub.add_parser('repad', help='restore slot widths from a base file (fixes agents that drop padding)')
    r.add_argument('files', nargs=1); r.add_argument('--base', required=True); r.add_argument('-i', '--in-place', action='store_true')
    r.add_argument('--mode', choices=['auto', 'prose', 'comments'], default='auto')
    c = sub.add_parser('check'); common(c)
    c.add_argument('--require', help='comma list of names that must be filled')
    c.add_argument('--require-filled', action='store_true'); c.add_argument('--strict', action='store_true')
    c.add_argument('--fit', type=int, help='also fail lines wider than N cells'); c.add_argument('--tab', type=int, default=8)
    c.add_argument('--base', help='fill-safe check: compare against this earlier version of the file')
    c.add_argument('--git-base', help='fill-safe check against a git revision (e.g. HEAD, origin/main)')
    c.add_argument('--allow', help='with --base: only these slots may change')
    c.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    return dict(scan=cmd_scan, fill=cmd_fill, check=cmd_check, fit=cmd_fit, new=cmd_new, repad=cmd_repad)[a.cmd](a)

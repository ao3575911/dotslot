"""Conformance runner for the Python implementation.
Run: python conformance/run.py [fixtures-dir]   exits 1 on any mismatch."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotslot.core import scan_text, fill_text, SlotError  # noqa: E402
from dotslot.verify import verify  # noqa: E402

def evaluate(c):
    path, mode = c.get('path', '-'), c.get('mode', 'auto')
    if c['op'] == 'scan':
        slots, issues = scan_text(c['input'], path, mode)
        return dict(
            slots=[dict(index=s.index, name=s.name, kind=s.kind, policy=s.policy, line=s.line + 1, col=s.col,
                        width=s.width, capacity=s.capacity, lines=1 + len(s.conts),
                        value=(s.block_value() if s.conts else s.value)) for s in slots],
            issues=sorted([dict(severity=sev, line=l + 1) for sev, l, _, _ in issues], key=lambda x: (x['line'], x['severity'])))
    if c['op'] == 'fill':
        try:
            return dict(output=fill_text(c['input'], c['values'], path, mode, c.get('policy', 'error'), (),
                                         set(c['allow']) if 'allow' in c else None))
        except SlotError:
            return dict(error=True)
    if c['op'] == 'check':
        r = verify(c['base'], c['input'], path, mode, set(c['allow']) if 'allow' in c else None,
                   c.get('ignore_whitespace', False))
        return dict(ok=r['ok'], changed=[x['slot'] for x in r['changed']])
    raise ValueError(c['op'])

def main(argv):
    d = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
    bad = n = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith('.json'): continue
        c = json.load(open(os.path.join(d, f), encoding='utf-8')); n += 1
        got = evaluate(c)
        if got != c['expect']:
            bad += 1; print(f'FAIL {c["id"]}\n  expected {json.dumps(c["expect"], ensure_ascii=False)}\n  got      {json.dumps(got, ensure_ascii=False)}')
    print(f'{n - bad}/{n} conformance fixtures passed'); return 1 if bad or not n else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

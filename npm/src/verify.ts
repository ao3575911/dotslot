// Fill-safe verification: prove only slot interiors changed. A port of dotslot/verify.py.
import { scanText, Slot, Mode } from './core.js';

function skeleton(text: string, slots: Slot[]): string[] {
  const spans = new Map<number, [number, number, string][]>();
  const add = (l: number, x: [number, number, string]) => { if (!spans.has(l)) spans.set(l, []); spans.get(l)!.push(x); };
  for (const s of slots) {
    const key = s.name ?? `@${s.index}`;
    add(s.line, [s.start, s.end, `⟦${key}⟧`]);
    for (const c of s.conts) add(c.line, [c.start, c.end, `⟦${key}|⟧`]);
  }
  const out = text.split('\n').map((ln, i) => {
    for (const [st, en, tok] of (spans.get(i) ?? []).sort((a, b) => b[0] - a[0])) ln = ln.slice(0, st) + tok + ln.slice(en);
    return ln;
  });
  const grow = slots.filter((s) => s.policy === 'grow' && s.name).map((s) => `⟦${s.name}|⟧`);
  const col: string[] = [];
  for (const ln of out) {
    if (col.length && ln === col[col.length - 1] && grow.some((g) => ln.includes(g))) continue;
    col.push(ln);
  }
  return col;
}

export interface Change { slot: string; line: number; before: string; after: string }
export interface Result { ok: boolean; changed: Change[]; violations: string[]; slots: number }

export function verify(base: string, next: string, path = '-', mode: Mode = 'auto', allow: Set<string> | null = null,
                       ignoreWhitespace = false): Result {
  const [bs] = scanText(base, path, mode), [ns, ni] = scanText(next, path, mode);
  const v: string[] = [], changed: Change[] = [], nlines = next.split('\n');
  for (const [sev, l, , m] of ni) if (sev === 'E') v.push(`line ${l + 1}: ${m}`);
  let sb = skeleton(base, bs), sn = skeleton(next, ns);
  if (ignoreWhitespace) { sb = sb.map((x) => x.trimEnd()); sn = sn.map((x) => x.trimEnd()); }
  if (sb.length !== sn.length || sb.some((x, i) => x !== sn[i])) {
    const d: string[] = [];
    for (let i = 0; i < Math.max(sb.length, sn.length) && d.length < 12; i++)
      if (sb[i] !== sn[i]) { if (sb[i] !== undefined) d.push('-' + sb[i]); if (sn[i] !== undefined) d.push('+' + sn[i]); }
    v.push('text outside slots changed:\n    ' + d.slice(0, 12).join('\n    '));
  }
  if (bs.length !== ns.length) v.push(`slot count changed: ${bs.length} -> ${ns.length}`);
  for (let k = 0; k < Math.min(bs.length, ns.length); k++) {
    const a = bs[k], b = ns[k], key = a.name ?? `@${a.index}`;
    if (a.name !== b.name || a.policy !== b.policy) { v.push(`${key}: header changed '${a.header}' -> '${b.header}'`); continue; }
    if (a.policy !== 'grow') {
      if (a.width !== b.width) {
        v.push(`${key}: width changed ${a.width} -> ${b.width} (closing > moved)`);
        if (b.width < a.width && nlines[b.line].slice(b.end).includes('>'))
          v.push(`${key}: hint: a raw '>' in the value closed the slot early; escape it as '\\>' or fill with \`dotslot fill\`, which escapes for you`);
      }
      if (a.conts.length !== b.conts.length) v.push(`${key}: block height changed ${1 + a.conts.length} -> ${1 + b.conts.length}`);
    }
    const va = a.conts.length ? a.blockValue() : a.value ?? '', vb = b.conts.length ? b.blockValue() : b.value ?? '';
    if (va !== vb) {
      changed.push({ slot: key, line: b.line + 1, before: va, after: vb });
      if (allow && !allow.has(key)) v.push(`${key}: changed but not in the allowed list`);
    }
  }
  return { ok: !v.length, changed, violations: v, slots: ns.length };
}

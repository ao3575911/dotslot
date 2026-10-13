// Conformance runner: node dist/conformance.js [fixtures-dir]. Exits 1 on any mismatch.
import { readdirSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { scanText, fillText, SlotError, Mode } from './core.js';
import { verify } from './verify.js';
import { cells } from './width.js';

const CAPS = new Set<string>();   // no tree-sitter in the npm build
function evaluate(c: any): unknown {
  const path = c.path ?? '-', mode: Mode = c.mode ?? 'auto';
  const allow = c.allow ? new Set<string>(c.allow) : null;
  if (c.op === 'width') return (c.input as string[]).map(cells);
  if (c.op === 'scan') {
    const [slots, issues] = scanText(c.input, path, mode);
    return {
      slots: slots.map((s) => ({ index: s.index, name: s.name, kind: s.kind, policy: s.policy, line: s.line + 1, col: s.col,
        width: s.width, capacity: s.capacity, lines: 1 + s.conts.length, value: s.conts.length ? s.blockValue() : s.value })),
      issues: issues.map(([severity, l]) => ({ severity, line: l + 1 })).sort((a, b) => a.line - b.line || (a.severity < b.severity ? -1 : a.severity > b.severity ? 1 : 0)),
    };
  }
  if (c.op === 'fill') {
    try { return { output: fillText(c.input, c.values, path, mode, c.policy ?? 'error', [], allow) }; }
    catch (e) { if (e instanceof SlotError) return { error: true }; throw e; }
  }
  if (c.op === 'check') { const r = verify(c.base, c.input, path, mode, allow, c.ignore_whitespace ?? false); return { ok: r.ok, changed: r.changed.map((x) => x.slot) }; }
  throw new Error(c.op);
}
const canon = (v: unknown): string => JSON.stringify(v, (_, x) => (x && typeof x === 'object' && !Array.isArray(x) ? Object.fromEntries(Object.entries(x).sort()) : x));
const dir = process.argv[2] ?? join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'conformance', 'fixtures');
let n = 0, bad = 0, skip = 0;
for (const f of readdirSync(dir).filter((f) => f.endsWith('.json')).sort()) {
  const c = JSON.parse(readFileSync(join(dir, f), 'utf8'));
  if (!(c.requires ?? []).every((r: string) => CAPS.has(r))) { skip++; continue; }
  n++; const got = evaluate(c);
  if (canon(got) !== canon(c.expect)) { bad++; console.log(`FAIL ${c.id}\n  expected ${canon(c.expect)}\n  got      ${canon(got)}`); }
}
console.log(`${n - bad}/${n} conformance fixtures passed` + (skip ? `, ${skip} skipped (optional capability missing)` : ''));
process.exitCode = bad || !n ? 1 : 0;

#!/usr/bin/env node
// dotslot CLI (npm): scan, fill, check. Same flags and exit codes as the Python CLI for these commands.
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { scanText, fillText, SlotError, Mode } from './core.js';
import { verify, Result } from './verify.js';

const VERSION = '0.7.0';
const USAGE = `usage: dotslot {scan,fill,check} FILE... [options]
  scan  [--json] [--mode auto|prose|comments]
  fill  --set name=value ... [--json-values F] [--clear name] [--overflow error|ellipsis|truncate|grow] [--allow a,b] [-i]
  check [--base FILE | --git-base REV] [--allow a,b] [--ignore-whitespace] [--require-filled] [--strict] [--json]`;

interface Args { cmd: string; files: string[]; opts: Record<string, string[]>; flags: Set<string> }
const VALUED = new Set(['--set', '--json-values', '--clear', '--overflow', '--allow', '--mode', '--base', '--git-base', '--require']);
function parse(argv: string[]): Args {
  const [cmd, ...rest] = argv; const files: string[] = [], opts: Record<string, string[]> = {}, flags = new Set<string>();
  for (let i = 0; i < rest.length; i++) {
    let a = rest[i]; let val: string | undefined;
    if (a.startsWith('--') && a.includes('=')) { val = a.slice(a.indexOf('=') + 1); a = a.slice(0, a.indexOf('=')); }
    if (VALUED.has(a)) { if (val === undefined) val = rest[++i]; if (val === undefined) die(`${a} needs a value`); (opts[a] ??= []).push(val!); }
    else if (a.startsWith('-') && a !== '-') flags.add(a === '-i' ? '--in-place' : a);
    else files.push(a);
  }
  return { cmd, files, opts, flags };
}
function die(m: string): never { process.stderr.write(`dotslot: ${m}\n`); process.exit(2); }
const read = (p: string) => readFileSync(p === '-' ? 0 : p, 'utf8');
const one = (a: Args, k: string) => a.opts[k]?.[a.opts[k].length - 1];
const allowOf = (a: Args) => (one(a, '--allow') ? new Set(one(a, '--allow')!.split(',')) : null);

function scan(a: Args, mode: Mode): number {
  const rows: object[] = [];
  for (const p of a.files) {
    const [slots, issues] = scanText(read(p), p, mode);
    for (const s of slots) rows.push({ file: p, line: s.line + 1, col: s.col, index: s.index, name: s.name, role: s.role,
      width: s.width, lines: 1 + s.conts.length, capacity: s.capacity + s.conts.reduce((x, c) => x + c.capacity, 0),
      filled: !!s.rawValue, value: s.rawValue ? (s.conts.length ? s.blockValue() : s.value) : null, policy: s.policy, in_comment: s.inComment });
    for (const [sev, l, c, m] of issues) process.stderr.write(`${p}:${l + 1}:${c}: ${sev}: ${m}\n`);
  }
  if (a.flags.has('--json')) { console.log(JSON.stringify(rows, null, 1)); return 0; }
  for (const r of rows as any[]) {
    const parts = [
      `${r.file}:${r.line}:${r.col}  @${r.index}`,
      (r.name ?? '-').padEnd(12),
      r.role.padEnd(6),
      `w=${String(r.width).padEnd(3)}`,
      `x${r.lines}`,
      `cap=${String(r.capacity).padEnd(3)}`,
      r.filled ? 'filled' : 'empty ',
      (r.policy ?? '').padEnd(8),
      r.in_comment ? '#' : ' ',
      r.value === null ? '' : JSON.stringify(r.value),
    ];
    console.log(parts.join(' '));
  }
  return 0;
}
function fill(a: Args, mode: Mode): number {
  const vals: Record<string, string> = {};
  for (const it of a.opts['--set'] ?? []) { const k = it.indexOf('='); if (k < 0) die(`--set needs name=value, got '${it}'`); vals[it.slice(0, k)] = it.slice(k + 1); }
  if (one(a, '--json-values')) Object.assign(vals, JSON.parse(read(one(a, '--json-values')!)));
  let rc = 0;
  for (const p of a.files) {
    let out: string;
    try { out = fillText(read(p), vals, p, mode, one(a, '--overflow') ?? 'error', a.opts['--clear'] ?? [], allowOf(a)); }
    catch (e) { if (!(e instanceof SlotError)) throw e; process.stderr.write(`${p}: error: ${e.message}\n`); rc = 2; continue; }
    if (a.flags.has('--in-place') && p !== '-') writeFileSync(p, out); else process.stdout.write(out);
  }
  return rc;
}
function baseText(a: Args, p: string): string | null {
  if (one(a, '--base')) return read(one(a, '--base')!);
  const rev = one(a, '--git-base');
  if (rev) { try { return execFileSync('git', ['show', `${rev}:./${p}`], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }); } catch { return null; } }
  return null;
}
function check(a: Args, mode: Mode): number {
  let rc = 0; const json = a.flags.has('--json'); const reports: (Result & { file: string })[] = [];
  const req = new Set((one(a, '--require') ?? '').split(',').filter((x) => x));
  for (const p of a.files) {
    const text = read(p), b = baseText(a, p);
    if (b !== null) {
      const r = { ...verify(b, text, p, mode, allowOf(a), a.flags.has('--ignore-whitespace')), file: p }; reports.push(r);
      if (!json) {
        for (const c of r.changed) console.log(`${p}:${c.line}: filled ${c.slot}: ${JSON.stringify(c.before)} -> ${JSON.stringify(c.after)}`);
        for (const x of r.violations) console.log(`${p}: VIOLATION: ${x}`);
        console.log(`${p}: ${r.ok ? 'fill-safe' : 'NOT fill-safe'} (${r.changed.length} slot(s) changed)`);
      }
      if (!r.ok) rc = 1; continue;
    }
    const [slots, issues] = scanText(text, p, mode); const probs = [...issues];
    for (const s of slots) if ((a.flags.has('--require-filled') || (s.name && req.has(s.name))) && !s.rawValue) probs.push(['E', s.line, s.col, `${s.name ?? '@' + s.index} is empty`]);
    for (const n of req) if (!slots.some((s) => s.name === n)) probs.push(['E', 0, 0, `required slot '${n}' not found`]);
    for (const [sev, l, c, m] of probs) {
      if (!json) console.log(`${p}:${l + 1}:${c}: ${sev}: ${m}`);
      if (sev === 'E' || (a.flags.has('--strict') && sev === 'W')) rc = 1;
    }
    if (!probs.length && !json) console.log(`${p}: ok (${slots.length} slots)`);
  }
  if (json) console.log(JSON.stringify(reports, null, 1));
  return rc;
}

export function main(argv: string[]): number {
  if (!argv.length || argv[0] === '-h' || argv[0] === '--help') { console.log(USAGE); return 0; }
  if (argv[0] === '--version') { console.log(VERSION); return 0; }
  const a = parse(argv);
  const mode = (one(a, '--mode') ?? 'auto') as Mode;
  if (!['auto', 'prose', 'comments'].includes(mode)) die(`bad --mode ${mode}`);
  if (!a.files.length) die('no files given\n' + USAGE);
  const fn = ({ scan, fill, check } as Record<string, (a: Args, m: Mode) => number>)[a.cmd];
  if (!fn) die(`unknown command '${a.cmd}'\n` + USAGE);
  return fn(a, mode);
}
process.exitCode = main(process.argv.slice(2));

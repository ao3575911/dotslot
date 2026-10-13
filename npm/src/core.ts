// dotslot core: scan and fill `<./____>` slots. A port of dotslot/core.py; conformance/fixtures is the contract.
import { cells, cut, displayWidth } from './width.js';

export class SlotError extends Error {}
const SLOT = /<\.\/((?:\\.|[^<>\\\n])*)>/g;
const OPEN = /<\.\//g;
const HEADER = /^(?:([A-Za-z_][\p{L}\p{N}_-]*)([!~+]?)|([!~+])):/u;
const PAD = ' _';
const POLICY: Record<string, string | null> = { '!': 'error', '~': 'ellipsis', '+': 'grow', '': null };
const PROSE = new Set(['.md', '.markdown', '.txt', '.text', '.rst', '.adoc', '.org', '.slot']);
const COMMENT: Record<string, readonly string[]> = {};
for (const e of '.py .sh .bash .zsh .yaml .yml .toml .rb .pl .r .mk .cfg .conf .dockerfile'.split(' ')) COMMENT[e] = ['#'];
for (const e of '.js .mjs .cjs .ts .tsx .jsx .c .h .cc .cpp .go .rs .java .kt .swift .cs .css .scss .json5'.split(' ')) COMMENT[e] = ['//', '/*'];
for (const e of '.sql .lua .hs .elm'.split(' ')) COMMENT[e] = ['--'];
for (const e of '.ini .el .lisp .clj .scm .asm'.split(' ')) COMMENT[e] = [';'];
for (const e of '.html .htm .xml .svg .vue'.split(' ')) COMMENT[e] = ['<!--'];
const ALL_MARKERS = ['#', '//', '/*', '--', ';', '<!--'];
export const CLOSERS = ['-->', '*/'];

export type Mode = 'auto' | 'prose' | 'comments';
export type Issue = [sev: 'E' | 'W', line: number, col: number, msg: string];

export const unescape = (s: string) => s.replace(/\\(.)/gu, '$1');
export function escape(v: string, unnamed: boolean): string {
  v = v.replace(/\\/g, '\\\\').replace(/</g, '\\<').replace(/>/g, '\\>');
  if (unnamed) {
    if (v.startsWith('|')) v = '\\' + v;
    const m = HEADER.exec(v);
    if (m) v = v.slice(0, m[0].length - 1) + '\\:' + v.slice(m[0].length);
  }
  if (v && PAD.includes(v[v.length - 1])) v = v.slice(0, -1) + '\\' + v[v.length - 1];
  return v;
}
function splitPad(s: string): [string, string] {
  let i = s.length;
  while (i > 0 && PAD.includes(s[i - 1])) {
    let j = i - 2, bs = 0;
    while (j >= 0 && s[j] === '\\') { bs++; j--; }
    if (bs % 2) break;
    i--;
  }
  return [s.slice(0, i), s.slice(i)];
}

export class Slot {
  kind = 'empty'; name: string | null = null; policy: string | null = null; header = ''; rawValue = ''; pad = '_';
  inComment = false; role = 'inline'; conts: Slot[] = []; index = 0;
  constructor(public line: number, public start: number, public end: number, public col: number, public interior: string) {}
  get width() { return cells(this.interior); }
  get capacity() { return this.width - cells(this.header); }
  get value(): string | null { return this.rawValue ? unescape(this.rawValue) : null; }
  blockValue() { return [this.value ?? '', ...this.conts.map((c) => c.value ?? '')].filter((p) => p).join(' '); }
}

function parseInterior(s: string): Partial<Slot> | null {
  if (s.includes('\t')) return null;
  const [body, padding] = splitPad(s);
  const pad = padding.includes('_') ? '_' : padding ? ' ' : '_';
  if (body.startsWith('|')) return { kind: 'cont', header: '|', rawValue: body.slice(1), pad };
  const m = HEADER.exec(body);
  if (m) {
    const name = m[1] ?? null, rest = body.slice(m[0].length);
    return { kind: rest ? 'filled' : name ? 'named' : 'empty', name, policy: POLICY[m[2] || m[3] || ''],
             header: m[0], rawValue: rest, pad };
  }
  if (!body) return padding ? { kind: 'empty', pad } : null;
  return { kind: 'filled', rawValue: body, pad };
}

export function commentStart(line: string, markers: readonly string[]): number {
  let q: string | null = null, i = 0; const n = line.length;
  while (i < n) {
    const c = line[i];
    if (q) { if (c === '\\') { i += 2; continue; } if (c === q) q = null; }
    else if ('"\'`'.includes(c)) { if (c !== "'" || line.indexOf("'", i + 1) !== -1) q = c; }
    else for (const mk of markers) if (line.startsWith(mk, i)) return i;
    i++;
  }
  return -1;
}
function ext(path: string) { const b = path.split(/[\\/]/).pop() ?? ''; const k = b.lastIndexOf('.'); return k > 0 ? b.slice(k).toLowerCase() : ''; }
export function markersFor(path: string, mode: Mode): readonly string[] | null {
  const base = (path.split(/[\\/]/).pop() ?? '').toLowerCase();
  if (mode === 'prose') return null;
  if (mode === 'auto' && (PROSE.has(ext(path)) || path === '-' || path === '/dev/stdin')) return null;
  if (base === 'dockerfile' || base === 'makefile') return ['#'];
  return COMMENT[ext(path)] ?? ALL_MARKERS;
}

export function scanText(text: string, path = '-', mode: Mode = 'auto'): [Slot[], Issue[]] {
  const lines = text.split('\n'), markers = markersFor(path, mode);
  const slots: Slot[] = [], issues: Issue[] = [];
  const isMd = ['.md', '.markdown'].includes(ext(path));
  lines.forEach((ln, i) => {
    const taken = new Set<number>();
    const cpos = markers ? commentStart(ln, markers) : -1;
    const inC = (pos: number) => cpos >= 0 && cpos < pos;
    for (const m of ln.matchAll(SLOT)) {
      const st = m.index!; taken.add(st);
      const col = displayWidth(ln.slice(0, st));
      if (m[1] === '') { issues.push(['E', i, col, 'zero-width slot <./>']); continue; }
      const p = parseInterior(m[1]);
      if (!p) { issues.push(['W', i, col, `slot-like text ${m[0]} is not a valid slot (ignored)`]); continue; }
      if (markers && !inC(st)) { issues.push(['W', i, col, `${m[0]} is outside a comment (ignored; use --mode prose)`]); continue; }
      const s = Object.assign(new Slot(i, st, st + m[0].length, col, m[1]), p, { inComment: markers !== null });
      if (isMd && m[1].includes('_') && (ln.slice(0, st).split('`').length - 1) % 2 === 0)
        issues.push(['W', i, col, `${m[0]}: '_' outside a code span can render as emphasis in Markdown; wrap it in backticks`]);
      if (s.kind === 'cont') s.role = 'cont';
      slots.push(s);
    }
    for (const m of ln.matchAll(OPEN))
      if (!taken.has(m.index!) && (!markers || inC(m.index!)))
        issues.push(['E', i, displayWidth(ln.slice(0, m.index!)), "unterminated slot: '<./' without '>' on the same line"]);
  });
  const byLine = new Map<number, Slot[]>();
  for (const s of slots) { if (!byLine.has(s.line)) byLine.set(s.line, []); byLine.get(s.line)!.push(s); }
  const owned = new Set<Slot>();
  for (const s of slots) {
    if ((s.kind === 'named' || s.kind === 'filled') && s.name) {
      let j = s.line + 1;
      for (;;) {
        const c = (byLine.get(j) ?? []).find((x) => x.kind === 'cont' && x.col === s.col);
        if (!c) break;
        if (c.width !== s.width) { issues.push(['E', j, c.col, `block ${s.name}: continuation width ${c.width} != head width ${s.width}`]); break; }
        owned.add(c); s.conts.push(c); j++;
      }
      if (s.conts.length) s.role = 'head';
    }
  }
  for (const s of slots) if (s.kind === 'cont' && !owned.has(s))
    issues.push(['E', s.line, s.col, 'continuation <./|…> with no named slot directly above at the same column']);
  const top = slots.filter((s) => s.role !== 'cont');
  const widths = new Map<string, Set<number>>();
  top.forEach((s, k) => {
    s.index = k + 1;
    if (s.name) { if (!widths.has(s.name)) widths.set(s.name, new Set()); widths.get(s.name)!.add(s.width); }
    if (s.capacity < 1 && s.policy !== 'grow')
      issues.push(['E', s.line, s.col, `${s.name ?? 'slot'}: header leaves ${s.capacity} cells for a value (width ${s.width})`]);
  });
  for (const [n, ws] of widths) if (ws.size > 1) issues.push(['W', 0, 0, `name '${n}' used with different widths [${[...ws].sort((a, b) => a - b).join(', ')}]`]);
  return [top, issues];
}

// ------------------------------------------------------------------ fill
function clean(v: unknown, block: boolean): string {
  let s = String(v);
  if (block) s = s.replace(/\s*\n\s*/g, ' ');
  if (s.includes('\t') || s.includes('\n')) throw new SlotError('value contains a tab or newline; inline slots hold one line');
  return s.replace(/ +$/, '');
}
const render = (header: string, raw: string, width: number, pad: string) => {
  const body = header + raw; return body + pad.repeat(Math.max(width - cells(body), 0));
};
const rstripSp = (s: string) => s.replace(/ +$/, '');
function cutEscaped(v: string, cap: number, unnamed: boolean, ellipsis: boolean): string {
  const cp = Array.from(v); let best = '';
  for (let k = cp.length; k >= 0; k--) {
    const head = ellipsis ? rstripSp(cp.slice(0, k).join('')) : cp.slice(0, k).join('');
    if (cells(escape(head, unnamed) + (ellipsis ? '…' : '')) <= cap) { best = head; break; }
  }
  if (ellipsis && best.includes(' ')) {
    const wb = rstripSp(best.slice(0, best.lastIndexOf(' ')));
    if (wb && cells(wb) >= Math.floor((cap * 2) / 3)) best = wb;
  }
  return escape(best, unnamed) + (ellipsis ? '…' : '');
}
function fitValue(v: string, cap: number, policy: string, what: string, unnamed: boolean): string {
  const e = escape(v, unnamed);
  if (cells(e) <= cap) return e;
  if (policy === 'ellipsis') { if (cap < 2) throw new SlotError(`${what}: no room for an ellipsis`); return cutEscaped(v, cap, unnamed, true); }
  if (policy === 'truncate') return cutEscaped(v, cap, unnamed, false);
  if (policy === 'grow') return e;
  throw new SlotError(`${what}: value is ${cells(e)} cells, slot holds ${cap} (overflow policy: error)`);
}
function wrapWords(v: string, caps: number[]): [string[], string] {
  const words = v.split(' ').filter((w) => w); const lines: string[] = []; let k = 0;
  for (const cap of caps) {
    let cur = '';
    while (k < words.length) {
      const w = words[k], cand = cur ? cur + ' ' + w : w;
      if (cells(escape(cand, false)) <= cap) { cur = cand; k++; }
      else if (!cur && cells(escape(w, false)) > cap) {
        const [head] = cut(w, Math.max(cap - 1, 1));
        if (!head) break;
        cur = head; words[k] = w.slice(head.length); break;
      } else break;
    }
    lines.push(cur);
  }
  return [lines, words.slice(k).join(' ')];
}
const stripChars = (s: string, chars: string) => {
  let a = 0, b = s.length;
  while (a < b && chars.includes(s[a])) a++;
  while (b > a && chars.includes(s[b - 1])) b--;
  return s.slice(a, b);
};

export function fillText(text: string, values: Record<string, unknown>, path = '-', mode: Mode = 'auto',
                         defaultPolicy = 'error', clear: string[] = [], allow: Set<string> | null = null): string {
  const [slots, issues] = scanText(text, path, mode);
  const errs = issues.filter((x) => x[0] === 'E');
  if (errs.length) throw new SlotError(errs.map(([, l, , m]) => `line ${l + 1}: ${m}`).join('; '));
  const lines = text.split('\n');
  const edits: [number, number, number, string][] = [], inserts: [number, string[]][] = [], used = new Set<string>();
  const has = (k: string) => Object.prototype.hasOwnProperty.call(values, k);
  for (const s of slots) {
    const key = `@${s.index}`;
    const target = has(key) || clear.includes(key) ? key : s.name;
    if (target === null || (!has(target) && !clear.includes(target))) continue;
    if (allow && !allow.has(target)) throw new SlotError(`${target}: not in the allowed slot list`);
    used.add(target);
    if (clear.includes(target)) {
      for (const x of [s, ...s.conts]) edits.push([x.line, x.start, x.end, '<./' + render(x.header, '', x.width, x.pad) + '>']);
      continue;
    }
    const pol = s.policy ?? defaultPolicy, what = s.name ?? key, unnamed = !s.header;
    const v = clean(values[target], s.conts.length > 0);
    if (!s.conts.length) {
      edits.push([s.line, s.start, s.end, '<./' + render(s.header, fitValue(v, s.capacity, pol, what, unnamed), s.width, s.pad) + '>']);
      continue;
    }
    const rows = [s, ...s.conts], caps = rows.map((r) => r.capacity);
    const [got, left0] = wrapWords(v, caps); let left = left0;
    const extra: string[] = []; const raws: (string | null)[] = [...got]; let lastRaw = '';
    if (left) {
      if (pol === 'grow') {
        while (left) {
          const [more, left2] = wrapWords(left, [s.width - 1]);
          if (left2 === left) throw new SlotError(`${what}: cannot wrap '${left}'`);
          extra.push(more[0]); left = left2;
        }
      } else if (pol === 'ellipsis') {
        const last = (got[got.length - 1] + ' ' + left).trim();
        raws[raws.length - 1] = null; lastRaw = cutEscaped(last, caps[caps.length - 1], false, true);
      } else if (pol !== 'truncate') {
        throw new SlotError(`${what}: block holds ${caps.reduce((a, b) => a + b, 0)} cells in ${caps.length} lines; ${cells(left)} cells left over (overflow policy: error)`);
      }
    }
    rows.forEach((r, k) => {
      const g = raws[k]; const raw = g === null ? lastRaw : escape(g, false);
      edits.push([r.line, r.start, r.end, '<./' + render(r.header, raw, r.width, r.pad) + '>']);
    });
    if (extra.length) {
      const last = rows[rows.length - 1], ln = lines[last.line];
      const before = ln.slice(0, last.start), after = ln.slice(last.end);
      const lead = !stripChars(before, ' \t#/;*-!<') ? before : ' '.repeat(displayWidth(before));
      const tail = CLOSERS.includes(after.trim()) || !after.trim() ? after : '';
      inserts.push([last.line, extra.map((e) => lead + '<./' + render('|', escape(e, false), s.width, last.pad) + '>' + tail)]);
    }
  }
  const missing = [...Object.keys(values), ...clear].filter((k) => !used.has(k));
  if (missing.length) throw new SlotError(`no slot named ${missing.join(', ')}`);
  edits.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
  for (const [li, st, en, nw] of edits) lines[li] = lines[li].slice(0, st) + nw + lines[li].slice(en);
  inserts.sort((a, b) => b[0] - a[0]);
  for (const [after, nw] of inserts) lines.splice(after + 1, 0, ...nw);
  return lines.join('\n');
}

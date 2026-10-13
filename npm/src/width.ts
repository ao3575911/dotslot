// Display-width model: grapheme-ish clusters measured with wcwidth tables (see scripts/gen_tables.py).
import { WIDE, ZERO, CTRL, EXTEND, VS16, VS15 } from './tables.js';

function inT(t: readonly number[], c: number): boolean {
  let lo = 0, hi = t.length / 2 - 1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (c < t[2 * m]) hi = m - 1; else if (c > t[2 * m + 1]) lo = m + 1; else return true;
  }
  return false;
}
export function wcwidth(c: number): number {
  if (inT(CTRL, c)) return -1;
  if (inT(ZERO, c)) return 0;
  return inT(WIDE, c) ? 2 : 1;
}
const ANSI = /\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]/y;
const ZWJ = 0x200d;
const isRI = (c: number) => c >= 0x1f1e6 && c <= 0x1f1ff;
const isFitz = (c: number) => c >= 0x1f3fb && c <= 0x1f3ff;

export function* clusters(s: string): Generator<string> {
  const cp = Array.from(s); let i = 0; const n = cp.length;
  let off = 0;
  while (i < n) {
    ANSI.lastIndex = off; const m = ANSI.exec(s);
    if (m) { const len = Array.from(m[0]).length; yield m[0]; i += len; off += m[0].length; continue; }
    let j = i + 1;
    while (j < n && (inT(EXTEND, cp[j].codePointAt(0)!) || cp[j - 1].codePointAt(0) === ZWJ)) j++;
    if (isRI(cp[i].codePointAt(0)!) && j < n && isRI(cp[j].codePointAt(0)!)) j++;
    const u = cp.slice(i, j).join(''); yield u; i = j; off += u.length;
  }
}
function clusterWidth(u: string): number {
  const cp = Array.from(u, (x) => x.codePointAt(0)!);
  if (cp.some((c) => wcwidth(c) < 0)) return cp.reduce((a, c) => a + Math.max(wcwidth(c), 0), 0);
  if (cp.length === 2 && isRI(cp[0]) && isRI(cp[1])) return 2;
  const base = cp[0]; let w = wcwidth(base);
  for (let k = 1; k < cp.length; k++) {
    const c = cp[k];
    if (c === ZWJ) { k++; continue; }
    if (c === 0xfe0f) { if (inT(VS16, base)) w = 2; continue; }
    if (c === 0xfe0e) { if (inT(VS15, base) && w === 2) w = 1; continue; }
    if (isFitz(c)) continue;
    w += wcwidth(c);
  }
  return w;
}
export function unitWidth(u: string, col: number, tab: number): number {
  if (u === '\t') return tab - (col % tab);
  if (u.startsWith('\x1b')) return 0;
  return clusterWidth(u);
}
export function displayWidth(s: string, start = 0, tab = 8): number {
  let col = start;
  for (const u of clusters(s)) col += unitWidth(u, col, tab);
  return col - start;
}
export const cells = (s: string): number => displayWidth(s, 0);
export function cut(s: string, n: number): [string, number] {
  const out: string[] = []; let w = 0;
  for (const u of clusters(s)) { const uw = unitWidth(u, w, 8); if (w + uw > n) break; out.push(u); w += uw; }
  return [out.join(''), w];
}

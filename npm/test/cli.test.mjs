// CLI smoke tests: node test/cli.test.mjs (after npm run build)
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const cli = join(import.meta.dirname ?? new URL('.', import.meta.url).pathname, '..', 'dist', 'cli.js');
const run = (...a) => spawnSync(process.execPath, [cli, ...a], { encoding: 'utf8' });
const d = mkdtempSync(join(tmpdir(), 'dotslot-'));
const f = join(d, 'a.md'), base = join(d, 'base.md');
writeFileSync(f, 'Owner: `<./owner:____________>`\nkeep\n'); writeFileSync(base, readFileSync(f));

let r = run('fill', f, '--set', 'owner=alice', '-i'); assert.equal(r.status, 0, r.stderr);
assert.equal(readFileSync(f, 'utf8'), 'Owner: `<./owner:alice_______>`\nkeep\n');
r = run('check', f, '--base', base); assert.equal(r.status, 0); assert.match(r.stdout, /fill-safe/);
r = run('check', f, '--base', base, '--allow', 'other'); assert.equal(r.status, 1);
r = run('check', f, '--base', base, '--json'); assert.equal(JSON.parse(r.stdout)[0].changed[0].slot, 'owner');
r = run('fill', f, '--set', 'owner=' + 'x'.repeat(40)); assert.equal(r.status, 2); assert.match(r.stderr, /overflow/);
r = run('scan', f, '--json'); assert.equal(JSON.parse(r.stdout)[0].value, 'alice');
writeFileSync(f, 'Owner: `<./owner:alice_______>`\nchanged\n');
r = run('check', f, '--base', base); assert.equal(r.status, 1); assert.match(r.stdout, /VIOLATION/);
assert.equal(run('--version').stdout.trim(), JSON.parse(readFileSync(new URL('../package.json', import.meta.url))).version);
const g = join(d, 'u.py'); writeFileSync(g, '# <./n:______>\n');
for (const v of ['a\x1b[2J', 'a\u202eb', 'a\u2066b', 'a\u200bb']) { r = run('fill', g, '--set', 'n=' + v); assert.equal(r.status, 2); assert.match(r.stderr, /unsafe/); }
r = run('fill', g, '--set', 'n=a\u202eb', '--allow-unsafe-chars'); assert.equal(r.status, 0, r.stderr);
writeFileSync(g, '# <./:___>\n'); assert.equal(run('check', g).status, 1);
writeFileSync(g, '# <./a b:__>\n'); assert.equal(run('check', g).status, 1);
r = spawnSync(process.execPath, [cli, 'check', '--git-base', 'no-such-ref-xyz', g], { encoding: 'utf8', cwd: d }); assert.equal(r.status, 2);
console.log('cli tests passed');

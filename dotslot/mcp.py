"""Minimal MCP server (stdio, JSON-RPC 2.0, newline-delimited) exposing dotslot.
Run:  python -m dotslot.mcp --root /path/to/repo
The only write path is `dotslot_fill`, which changes slot interiors and re-verifies the result."""
from __future__ import annotations
import argparse, difflib, json, os, sys
from .core import scan_text, fill_text, SlotError
from .verify import verify
from . import __version__

TOOLS = [
    dict(name='dotslot_scan', description='List the fill-in slots in a file (name, width, capacity, current value).',
         inputSchema=dict(type='object', properties=dict(path=dict(type='string')), required=['path'])),
    dict(name='dotslot_fill', description='Fill named or @N slots in a file. Only slot interiors change; '
         'the result is verified fill-safe before it is written. Use dry_run to preview the diff.',
         inputSchema=dict(type='object', properties=dict(
             path=dict(type='string'), values=dict(type='object', additionalProperties=dict(type='string')),
             overflow=dict(type='string', enum=['error', 'ellipsis', 'truncate', 'grow']),
             dry_run=dict(type='boolean')), required=['path', 'values'])),
    dict(name='dotslot_check', description='Prove a file differs from a base version only inside slots.',
         inputSchema=dict(type='object', properties=dict(path=dict(type='string'), base_text=dict(type='string'),
             allow=dict(type='array', items=dict(type='string'))), required=['path', 'base_text'])),
]

class Server:
    def __init__(self, root): self.root = os.path.realpath(root)
    def _path(self, p):
        full = os.path.realpath(os.path.join(self.root, p))
        if os.path.commonpath([full, self.root]) != self.root: raise SlotError(f'{p}: outside the server root')
        return full
    def scan(self, path):
        slots, issues = scan_text(open(self._path(path), encoding='utf-8').read(), path)
        return dict(slots=[dict(index=s.index, name=s.name, line=s.line + 1, width=s.width, lines=1 + len(s.conts),
                                capacity=s.capacity + sum(c.capacity for c in s.conts), policy=s.policy,
                                value=(s.block_value() if s.conts else s.value)) for s in slots],
                    issues=[f'{sev} line {l+1}: {m}' for sev, l, _, m in issues])
    def fill(self, path, values, overflow='error', dry_run=False):
        full = self._path(path); old = open(full, encoding='utf-8').read()
        new = fill_text(old, values, path, 'auto', overflow or 'error')
        r = verify(old, new, path)
        if not r['ok']: raise SlotError('refusing to write: ' + '; '.join(r['violations']))
        diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), path, path))
        if not dry_run: open(full, 'w', encoding='utf-8').write(new)
        return dict(written=not dry_run, changed=r['changed'], diff=diff)
    def check(self, path, base_text, allow=None):
        new = open(self._path(path), encoding='utf-8').read()
        return verify(base_text, new, path, 'auto', set(allow) if allow else None)

    def handle(self, msg):
        m, mid, p = msg.get('method'), msg.get('id'), msg.get('params') or {}
        if m == 'initialize':
            res = dict(protocolVersion=p.get('protocolVersion', '2025-06-18'), capabilities=dict(tools={}),
                       serverInfo=dict(name='dotslot', version=__version__))
        elif m == 'tools/list': res = dict(tools=TOOLS)
        elif m == 'tools/call':
            name, args = p.get('name'), p.get('arguments') or {}
            fn = dict(dotslot_scan=self.scan, dotslot_fill=self.fill, dotslot_check=self.check).get(name)
            try:
                if not fn: raise SlotError(f'unknown tool {name}')
                out, err = fn(**args), False
            except (SlotError, OSError, TypeError) as e:
                out, err = dict(error=str(e)), True
            res = dict(content=[dict(type='text', text=json.dumps(out, ensure_ascii=False))], isError=err)
        elif mid is None: return None            # notification
        elif m == 'ping': res = {}
        else: return dict(jsonrpc='2.0', id=mid, error=dict(code=-32601, message=f'unknown method {m}'))
        return None if mid is None else dict(jsonrpc='2.0', id=mid, result=res)

def main(argv=None):
    ap = argparse.ArgumentParser(prog='dotslot-mcp'); ap.add_argument('--root', default='.')
    a = ap.parse_args(argv); srv = Server(a.root)
    for line in sys.stdin:
        if not line.strip(): continue
        out = srv.handle(json.loads(line))
        if out is not None: sys.stdout.write(json.dumps(out, ensure_ascii=False) + '\n'); sys.stdout.flush()

if __name__ == '__main__':
    main()

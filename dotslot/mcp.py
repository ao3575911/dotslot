"""Minimal MCP server (stdio, JSON-RPC 2.0, newline-delimited) exposing dotslot.
Run:  python -m dotslot.mcp --root /path/to/repo [--allow owner,status]
The only write path is `dotslot_fill`, which changes slot interiors and re-verifies the result.
Every tool call is validated against the tool's input schema before it runs."""
from __future__ import annotations
import argparse, difflib, json, os, sys
from .core import scan_text, fill_text, SlotError, atomic_write as _atomic_write
from .verify import verify
from . import __version__

_STR, _BOOL = dict(type='string'), dict(type='boolean')
_ALLOW = dict(type='array', items=_STR, description='Slot names or @N that may change. '
              'Intersected with the server --allow list, if any.')
TOOLS = [
    dict(name='dotslot_scan', description='List the fill-in slots in a file (name, width, capacity, current value).',
         inputSchema=dict(type='object', properties=dict(path=_STR), required=['path'], additionalProperties=False)),
    dict(name='dotslot_fill', description='Fill named or @N slots in a file. Only slot interiors change; '
         'the result is verified fill-safe before it is written. Use dry_run to preview the unified diff.',
         inputSchema=dict(type='object', properties=dict(
             path=_STR, values=dict(type='object', additionalProperties=_STR),
             overflow=dict(type='string', enum=['error', 'ellipsis', 'truncate', 'grow']),
             dry_run=_BOOL, allow=_ALLOW), required=['path', 'values'], additionalProperties=False)),
    dict(name='dotslot_check', description='Prove a file differs from a base version only inside slots.',
         inputSchema=dict(type='object', properties=dict(path=_STR, base_text=_STR, allow=_ALLOW,
             ignore_whitespace=_BOOL), required=['path', 'base_text'], additionalProperties=False)),
]
_SCHEMAS = {t['name']: t['inputSchema'] for t in TOOLS}
_TYPES = dict(string=str, boolean=bool, object=dict, array=list)

class InvalidParams(Exception):
    pass

def validate(schema, value, where='arguments'):
    """Check `value` against the small JSON-schema subset the tools use. Raises InvalidParams."""
    t = schema.get('type')
    if t and not (isinstance(value, _TYPES[t]) and not (t != 'boolean' and isinstance(value, bool))):
        raise InvalidParams(f'{where}: expected {t}, got {type(value).__name__}')
    if 'enum' in schema and value not in schema['enum']:
        raise InvalidParams(f'{where}: must be one of {schema["enum"]}, got {value!r}')
    if t == 'object':
        props = schema.get('properties', {})
        for k in schema.get('required', []):
            if k not in value: raise InvalidParams(f'{where}: missing required property {k!r}')
        extra = schema.get('additionalProperties', True)
        for k, v in value.items():
            if k in props: validate(props[k], v, f'{where}.{k}')
            elif extra is False: raise InvalidParams(f'{where}: unexpected property {k!r}')
            elif isinstance(extra, dict): validate(extra, v, f'{where}.{k}')
    if t == 'array' and 'items' in schema:
        for i, v in enumerate(value): validate(schema['items'], v, f'{where}[{i}]')

PROTOCOL_VERSIONS = ('2025-06-18', '2025-03-26', '2024-11-05')   # newest first
MAX_BYTES = 16 * 1024 * 1024   # refuse to load larger files (memory/CPU bound for an agent-driven server)

class Server:
    def __init__(self, root, allow=None):
        self.root = os.path.realpath(root)
        self.allow = set(allow) if allow else None
    def _path(self, p):
        if not p or '\0' in p: raise SlotError(f'{p!r}: invalid path')
        try:
            full = os.path.realpath(os.path.join(self.root, p))
            inside = os.path.commonpath([full, self.root]) == self.root
        except ValueError:   # e.g. a different drive on Windows
            inside = False
        if not inside: raise SlotError(f'{p}: outside the server root')
        if '.git' in os.path.relpath(full, self.root).split(os.sep):
            raise SlotError(f'{p}: inside a .git directory')
        if not os.path.isfile(full): raise SlotError(f'{p}: not a regular file')
        if os.path.getsize(full) > MAX_BYTES: raise SlotError(f'{p}: larger than {MAX_BYTES} bytes')
        return full
    def _read(self, p):
        with open(self._path(p), encoding='utf-8', newline='') as f: return f.read()
    def _allow(self, allow):
        if allow is None: return self.allow
        return set(allow) & self.allow if self.allow is not None else set(allow)
    def scan(self, path):
        slots, issues = scan_text(self._read(path), path)
        return dict(slots=[dict(index=s.index, name=s.name, line=s.line + 1, width=s.width, lines=1 + len(s.conts),
                                capacity=s.capacity + sum(c.capacity for c in s.conts), policy=s.policy,
                                value=(s.block_value() if s.conts else s.value)) for s in slots],
                    issues=[f'{sev} line {l+1}: {m}' for sev, l, _, m in issues])
    def fill(self, path, values, overflow='error', dry_run=False, allow=None):
        full = self._path(path); old = self._read(path)
        allow = self._allow(allow)
        new = fill_text(old, values, path, 'auto', overflow or 'error', (), allow)
        r = verify(old, new, path, 'auto', allow)
        if not r['ok']: raise SlotError('refusing to write: ' + '; '.join(r['violations']))
        diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f'a/{path}', f'b/{path}'))
        if not dry_run and new != old: _atomic_write(full, new)
        return dict(written=not dry_run and new != old, dry_run=bool(dry_run), changed=r['changed'], diff=diff)
    def check(self, path, base_text, allow=None, ignore_whitespace=False):
        new = self._read(path)
        return verify(base_text, new, path, 'auto', self._allow(allow), ignore_whitespace)

    def handle(self, msg):
        if not isinstance(msg, dict):
            return dict(jsonrpc='2.0', id=None, error=dict(code=-32600, message='invalid request'))
        m, mid, p = msg.get('method'), msg.get('id'), msg.get('params')
        if p is None: p = {}
        if not isinstance(p, dict):
            if mid is None: return None
            return dict(jsonrpc='2.0', id=mid, error=dict(code=-32602, message='params must be an object'))
        if m == 'initialize':
            want = p.get('protocolVersion')
            ver = want if want in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            res = dict(protocolVersion=ver, capabilities=dict(tools={}),
                       serverInfo=dict(name='dotslot', version=__version__))
        elif m == 'tools/list': res = dict(tools=TOOLS)
        elif m == 'tools/call':
            name, args = p.get('name'), p.get('arguments', {})
            fn = dict(dotslot_scan=self.scan, dotslot_fill=self.fill, dotslot_check=self.check).get(name)
            if not fn:
                return dict(jsonrpc='2.0', id=mid, error=dict(code=-32602, message=f'unknown tool {name!r}'))
            try:
                validate(_SCHEMAS[name], args)
            except InvalidParams as e:
                return dict(jsonrpc='2.0', id=mid, error=dict(code=-32602, message=f'{name}: {e}'))
            try:
                out, err = fn(**args), False
            except (SlotError, OSError, UnicodeDecodeError) as e:
                out, err = dict(error=str(e)), True
            except Exception as e:   # never let one bad call take the server down
                out, err = dict(error=f'internal error: {type(e).__name__}'), True
            res = dict(content=[dict(type='text', text=json.dumps(out, ensure_ascii=False))], isError=err)
        elif mid is None: return None            # notification
        elif m == 'ping': res = {}
        else: return dict(jsonrpc='2.0', id=mid, error=dict(code=-32601, message=f'unknown method {m}'))
        return None if mid is None else dict(jsonrpc='2.0', id=mid, result=res)

def main(argv=None):
    ap = argparse.ArgumentParser(prog='dotslot-mcp'); ap.add_argument('--root', default='.')
    ap.add_argument('--allow', help='comma list of slots that fill/check may change (per-call allow narrows it)')
    a = ap.parse_args(argv); srv = Server(a.root, a.allow.split(',') if a.allow else None)
    import signal; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        for line in sys.stdin:
            if not line.strip(): continue
            try: msg = json.loads(line)
            except (ValueError, RecursionError):
                out = dict(jsonrpc='2.0', id=None, error=dict(code=-32700, message='parse error'))
            else:
                try: out = srv.handle(msg)
                except Exception:
                    out = dict(jsonrpc='2.0', id=msg.get('id') if isinstance(msg, dict) else None,
                               error=dict(code=-32603, message='internal error'))
            if out is not None: sys.stdout.write(json.dumps(out, ensure_ascii=False) + '\n'); sys.stdout.flush()
    except (KeyboardInterrupt, BrokenPipeError):   # client went away: exit quietly
        pass
    return 0

if __name__ == '__main__':
    sys.exit(main())

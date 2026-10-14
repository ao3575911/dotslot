import json, subprocess, sys
from dotslot.cli import main
from dotslot.mcp import Server

def test_fill_rejects_unsafe_chars(tmp_path):
    f = tmp_path / 'a.py'; f.write_text('# <./n:______>\n')
    for v in ('a\x1b[2J', 'a\u202eb', 'a\u2066b', 'a\u200bb'):
        assert main(['fill', str(f), '--set', f'n={v}']) == 2
    assert main(['fill', str(f), '--set', 'n=a\u202eb', '--allow-unsafe-chars']) == 0

def test_fit_fail_at_exits_nonzero(tmp_path):
    f = tmp_path / 'a.py'; f.write_text('# <./n:____>\n' + 'x' * 19 + '\n')
    assert main(['fit', str(f), '--fail-at', '10']) == 1
    assert main(['fit', str(f), '--fail-at', '40']) == 0

def test_malformed_headers_flagged(tmp_path):
    f = tmp_path / 'a.txt'
    for s in ('<./:___>\n', '<./a b:__>\n'):
        f.write_text(s); assert main(['check', str(f)]) == 1

def _mcp(lines, root):
    p = subprocess.run([sys.executable, '-m', 'dotslot.mcp', '--root', str(root)], input='\n'.join(lines) + '\n',
                       capture_output=True, text=True, timeout=20)
    return [json.loads(l) for l in p.stdout.splitlines()]

def test_mcp_schema_rejected_before_write(tmp_path):
    f = tmp_path / 'a.py'; f.write_text('# <./n:____>\n')
    call = lambda i, a: json.dumps(dict(jsonrpc='2.0', id=i, method='tools/call', params=dict(name='dotslot_fill', arguments=a)))
    out = _mcp([call(1, dict(path='a.py', values=dict(n=5))),
                call(2, dict(path='a.py', values=dict(n='x'), overflow='bogus'))], tmp_path)
    assert [o['error']['code'] for o in out] == [-32602, -32602]
    assert f.read_text() == '# <./n:____>\n'

def test_mcp_parse_error_keeps_serving(tmp_path):
    out = _mcp(['not json', json.dumps(dict(jsonrpc='2.0', id=7, method='ping'))], tmp_path)
    assert out[0]['error']['code'] == -32700 and out[0]['id'] is None
    assert out[1] == dict(jsonrpc='2.0', id=7, result={})

def test_mcp_fill_rejects_unsafe(tmp_path):
    (tmp_path / 'a.py').write_text('# <./n:____>\n')
    r = Server(str(tmp_path)).handle(dict(jsonrpc='2.0', id=1, method='tools/call',
        params=dict(name='dotslot_fill', arguments=dict(path='a.py', values=dict(n='a\u202e')))))
    assert r['result']['isError'] and (tmp_path / 'a.py').read_text() == '# <./n:____>\n'

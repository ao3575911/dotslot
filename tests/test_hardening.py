import json, os, subprocess, sys
import pytest
from dotslot.cli import main
from dotslot.mcp import Server

HOOK = os.path.join(os.path.dirname(__file__), '..', 'integrations', 'claude-code', 'dotslot-hook.sh')

def _repo(tmp_path, monkeypatch, name, data):
    monkeypatch.chdir(tmp_path)
    git = ['git', '-c', 'user.email=a@b', '-c', 'user.name=a']
    subprocess.run(['git', 'init', '-q'], check=True)
    (tmp_path / name).write_bytes(data)
    subprocess.run(git + ['add', '--', name], check=True)
    subprocess.run(git + ['commit', '-qm', 'i'], check=True)

def test_git_base_keeps_crlf(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch, 'a.md', b'Owner: `<./owner:____>`\r\nkeep\r\n')
    assert main(['check', '--git-base', 'HEAD', 'a.md']) == 0

def test_git_base_rejects_option_like_revision(tmp_path, monkeypatch, capsys):
    _repo(tmp_path, monkeypatch, 'a.md', b'`<./owner:____>`\n')
    assert main(['check', '--git-base=--output=pwn', 'a.md']) == 2
    assert not (tmp_path / 'pwn').exists()

def test_json_values_must_be_object_of_strings(tmp_path):
    f = tmp_path / 'a.md'; f.write_text('`<./n:____>`\n')
    for bad in ('[1]', '{"n": 1}'):
        v = tmp_path / 'v.json'; v.write_text(bad)
        with pytest.raises(SystemExit): main(['fill', str(f), '--json-values', str(v)])
    v.write_text('{bad')
    assert main(['fill', str(f), '--json-values', str(v)]) == 2

def test_fill_in_place_follows_symlink(tmp_path):
    f = tmp_path / 'a.md'; f.write_text('`<./n:____>`\n')
    link = tmp_path / 'l.md'; link.symlink_to(f)
    assert main(['fill', '-i', str(link), '--set', 'n=ab']) == 0
    assert link.is_symlink() and f.read_text() == '`<./n:ab__>`\n'

def test_bad_numeric_and_pad_args():
    with pytest.raises(SystemExit): main(['fit', '-', '--targets', 'x'])
    with pytest.raises(SystemExit): main(['new', 'o', '--width', '10', '--pad', 'ab'])
    with pytest.raises(SystemExit): main(['new', 'o', '--width', '10', '--lines', '0'])
    with pytest.raises(SystemExit): main(['new', 'o', '--width', '0'])

def test_mcp_rejects_bad_paths(tmp_path):
    (tmp_path / '.git').mkdir(); (tmp_path / '.git' / 'config').write_text('x')
    srv = Server(str(tmp_path))
    for p in ('a\0b', '.git/config', '../x', '.', ''):
        r = srv.handle(dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(name='dotslot_scan', arguments=dict(path=p))))
        assert r['result']['isError'], p

def test_mcp_survives_hostile_input(tmp_path):
    lines = ['[' * 100000 + ']' * 100000, '{"jsonrpc":"2.0","id":2,"method":"ping"}']
    r = subprocess.run([sys.executable, '-m', 'dotslot.mcp', '--root', str(tmp_path)],
                       input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=30)
    out = [json.loads(x) for x in r.stdout.splitlines()]
    assert out[0]['error']['code'] == -32700 and out[1] == dict(jsonrpc='2.0', id=2, result={})

def test_claude_hook_checks_absolute_paths(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch, 'b.md', b'`<./owner:____>`\nkeep\n')
    (tmp_path / 'b.md').write_text('`<./owner:____>`\nkept\n')
    env = dict(os.environ, PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ['PATH'])
    payload = json.dumps(dict(tool_input=dict(file_path=str(tmp_path / 'b.md'))))
    r = subprocess.run(['bash', HOOK], input=payload, capture_output=True, text=True, env=env)
    if 'command not found' in r.stderr: pytest.skip('dotslot entry point not installed')
    assert r.returncode == 2, r.stderr

"""v0.3: MCP schema validation and --allow, check --ignore-whitespace, and the h1–h9 exit gate."""
import json, os, subprocess, sys, pathlib, pytest
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from dotslot.core import fill_text
from dotslot.cli import main
from dotslot.mcp import Server, validate, InvalidParams, TOOLS

T = 'Title: <./title:______________>\nOwner: <./owner:_______>\nBody text stays.\n'

def rpc(srv, name, **args):
    return srv.handle(dict(jsonrpc='2.0', id=7, method='tools/call', params=dict(name=name, arguments=args)))

def text(r): return json.loads(r['result']['content'][0]['text'])

@pytest.fixture
def srv(tmp_path):
    (tmp_path / 'doc.md').write_text(T); return Server(str(tmp_path))

@pytest.mark.parametrize('name,args,msg', [
    ('dotslot_scan', {}, "missing required property 'path'"),
    ('dotslot_scan', {'path': 3}, 'arguments.path: expected string'),
    ('dotslot_fill', {'path': 'doc.md', 'values': {'owner': 1}}, 'arguments.values.owner: expected string'),
    ('dotslot_fill', {'path': 'doc.md', 'values': []}, 'arguments.values: expected object'),
    ('dotslot_fill', {'path': 'doc.md', 'values': {}, 'overflow': 'wrap'}, 'must be one of'),
    ('dotslot_fill', {'path': 'doc.md', 'values': {}, 'dry_run': 'yes'}, 'expected boolean'),
    ('dotslot_fill', {'path': 'doc.md', 'values': {}, 'evil': 1}, "unexpected property 'evil'"),
    ('dotslot_check', {'path': 'doc.md', 'base_text': T, 'allow': ['a', 2]}, 'arguments.allow[1]: expected string'),
    ('dotslot_check', {'path': 'doc.md'}, "missing required property 'base_text'"),
])
def test_mcp_rejects_bad_arguments(srv, name, args, msg):
    r = rpc(srv, name, **args)
    assert r['error']['code'] == -32602 and msg in r['error']['message']

def test_mcp_non_object_arguments_and_unknown_tool(srv):
    r = srv.handle(dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(name='dotslot_scan', arguments=[1])))
    assert r['error']['code'] == -32602
    assert rpc(srv, 'nope')['error']['code'] == -32602

def test_schemas_are_closed_and_validate_themselves():
    for t in TOOLS:
        assert t['inputSchema']['additionalProperties'] is False
    validate(TOOLS[1]['inputSchema'], {'path': 'a', 'values': {'x': 'y'}, 'allow': ['x'], 'dry_run': True})
    with pytest.raises(InvalidParams): validate({'type': 'string'}, True)

def test_mcp_dry_run_diff_does_not_write(srv, tmp_path):
    r = text(rpc(srv, 'dotslot_fill', path='doc.md', values={'owner': 'Adam'}, dry_run=True))
    assert r['dry_run'] and not r['written'] and (tmp_path / 'doc.md').read_text() == T
    assert '-Owner: <./owner:_______>' in r['diff'] and '+Owner: <./owner:Adam___>' in r['diff']
    assert r['diff'].startswith('--- a/doc.md') and r['changed'][0]['slot'] == 'owner'
    r = text(rpc(srv, 'dotslot_fill', path='doc.md', values={'owner': 'Adam'}))
    assert r['written'] and 'Adam' in (tmp_path / 'doc.md').read_text()

def test_mcp_allow_per_call_and_server_wide(tmp_path):
    (tmp_path / 'doc.md').write_text(T)
    srv = Server(str(tmp_path))
    r = rpc(srv, 'dotslot_fill', path='doc.md', values={'owner': 'x'}, allow=['title'])
    assert r['result']['isError'] and 'not in the allowed' in text(r)['error']
    assert text(rpc(srv, 'dotslot_fill', path='doc.md', values={'title': 'x'}, allow=['title']))['written']
    (tmp_path / 'doc.md').write_text(fill_text(T, {'title': 'a', 'owner': 'b'}))
    c = text(rpc(srv, 'dotslot_check', path='doc.md', base_text=T, allow=['title']))
    assert not c['ok'] and any('owner' in v for v in c['violations'])
    narrow = Server(str(tmp_path), allow=['title'])     # server-wide list; per-call can only narrow it
    c = text(rpc(narrow, 'dotslot_check', path='doc.md', base_text=T, allow=['title', 'owner']))
    assert not c['ok']
    assert not text(rpc(narrow, 'dotslot_check', path='doc.md', base_text=T))['ok']
    assert text(rpc(Server(str(tmp_path), allow=['title', 'owner']), 'dotslot_check', path='doc.md', base_text=T))['ok']

def test_mcp_paths_confined_to_root(srv, tmp_path):
    (tmp_path.parent / 'outside.md').write_text(T)
    for p in ('../outside.md', str(tmp_path.parent / 'outside.md')):
        r = rpc(srv, 'dotslot_fill', path=p, values={'owner': 'x'})
        assert r['result']['isError'] and 'outside the server root' in text(r)['error']
    os.symlink(tmp_path.parent / 'outside.md', tmp_path / 'link.md')
    assert 'outside the server root' in text(rpc(srv, 'dotslot_scan', path='link.md'))['error']

def test_mcp_stdio_parse_error_and_allow_flag(tmp_path):     # h9: real stdio
    (tmp_path / 'doc.md').write_text(T)
    msgs = ['not json', json.dumps(dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(
        name='dotslot_fill', arguments=dict(path='doc.md', values={'owner': 'x'}))))]
    p = subprocess.run([sys.executable, '-m', 'dotslot.mcp', '--root', str(tmp_path), '--allow', 'title'],
                       input='\n'.join(msgs) + '\n', capture_output=True, text=True, cwd=ROOT, check=True)
    a, b = [json.loads(x) for x in p.stdout.splitlines()]
    assert a['error']['code'] == -32700 and b['result']['isError']

def test_check_ignore_whitespace(tmp_path, capsys):
    b = tmp_path / 'base.md'; b.write_text(T)
    f = tmp_path / 'a.md'; f.write_text(fill_text(T, {'owner': 'Adam'}).replace('stays.', 'stays.   '))
    assert main(['check', str(f), '--base', str(b)]) == 1                         # off: h7 caught
    assert main(['check', str(f), '--base', str(b), '--ignore-whitespace']) == 0  # on: trailing ws ignored
    f.write_text(f.read_text().replace('Body text', 'Body  text'))
    assert main(['check', str(f), '--base', str(b), '--ignore-whitespace']) == 1  # inner whitespace still counts
    capsys.readouterr()

# ---- exit gate: h1–h8 in a git repo, the way the Action and hooks run them ----
REL = ('# Release\nOwner: <./owner:____________>   Date: <./date:__________>\n'
       'Status: <./status~:__________________>\nDo not edit below this line: legal text, version 3.1.\n')

@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); (tmp_path / 'release.md').write_text(REL)
    for c in (['init', '-q'], ['add', '.'], ['-c', 'user.email=a@b', '-c', 'user.name=a', 'commit', '-qm', 'base']):
        subprocess.run(['git', *c], check=True)
    return tmp_path

@pytest.mark.parametrize('case,mut,args,rc,msg', [
    ('h1', lambda t: fill_text(t, {'owner': 'Adam', 'date': '2026-10-17'}), [], 0, 'fill-safe (2'),
    ('h2', lambda t: t.replace('version 3.1', 'version 3.2'), [], 1, 'outside slots'),
    ('h3', lambda t: t.replace('<./owner:____________>', '<./owner:Adam>'), [], 1, 'width changed'),
    ('h4', lambda t: t.replace('<./owner:', '<./owners'), [], 1, 'header changed'),
    ('h5', lambda t: t.replace('<./date:__________>', '<./date:a>b_______>'), [], 1, "raw '>'"),
    ('h6', lambda t: fill_text(t, {'date': '2026-10-17'}), ['--allow', 'owner'], 1, 'not in the allowed'),
    ('h7', lambda t: t.replace('# Release', '# Release  '), [], 1, 'outside slots'),
    ('h7w', lambda t: t.replace('# Release', '# Release  '), ['--ignore-whitespace'], 0, 'fill-safe'),
])
def test_exit_gate_h_cases(repo, capsys, case, mut, args, rc, msg):
    (repo / 'release.md').write_text(mut(REL))
    assert main(['check', 'release.md', '--git-base', 'HEAD', *args]) == rc
    assert msg in capsys.readouterr().out

def test_exit_gate_h8_claude_code_hook(repo):
    hook = ROOT / 'integrations' / 'claude-code' / 'dotslot-hook.sh'
    env = dict(os.environ, PATH=f"{pathlib.Path(sys.executable).parent}:{os.environ['PATH']}")
    ev = json.dumps(dict(tool_input=dict(file_path='release.md')))
    (repo / 'release.md').write_text(fill_text(REL, {'owner': 'Adam'}))
    assert subprocess.run(['bash', str(hook)], input=ev, text=True, env=env).returncode == 0
    (repo / 'release.md').write_text(REL.replace('3.1', '3.2'))
    p = subprocess.run(['bash', str(hook)], input=ev, text=True, env=env, capture_output=True)
    assert p.returncode == 2 and 'fill-only' in p.stderr

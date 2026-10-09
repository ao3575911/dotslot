import json, subprocess, sys, pathlib, pytest
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from dotslot.core import scan_text, fill_text, SlotError, escape, parse_interior
from dotslot.verify import verify
from dotslot.cli import main
from dotslot.mcp import Server
from dotslot.width import display_width

def one(t, path='x.md'):
    s, iss = scan_text(t, path); assert len(s) == 1, iss; return s[0]

def test_underscore_and_space_padding():
    a, b = one('<./status:______>'), one('<./status:      >')
    assert (a.width, a.capacity, a.pad, a.kind) == (13, 6, '_', 'named')
    assert (b.capacity, b.pad) == (6, ' ')
    assert fill_text('<./s:_____>', {'s': 'ok'}) == '<./s:ok___>'
    assert fill_text('<./s:     >', {'s': 'ok'}) == '<./s:ok   >'   # keeps the slot's own pad char

def test_unnamed_has_no_cost_and_typed_word_is_a_value():
    s = one('<./__________>'); assert s.capacity == 10
    assert fill_text('<./__________>', {'@1': '2026-10-10'}) == '<./2026-10-10>'
    y = one('<./yes___>'); assert (y.kind, y.name, y.value) == ('filled', None, 'yes')

@pytest.mark.parametrize('v', ['a > b', '<tag>', 'back\\slash', 'foo_', 'note: x', '|pipe', 'x  y', '中文_'])
def test_escape_roundtrip(v):
    out = fill_text('<./' + '_' * 20 + '>', {'@1': v})
    s = one(out); assert s.value == v and s.name is None and s.width == 20

def test_named_escape_and_header_policy():
    out = fill_text('<./t~:__________>', {'t': 'a>b'}); assert out == '<./t~:a\\>b______>'
    assert one(out).value == 'a>b' and one(out).policy == 'ellipsis'
    assert one('<./+:______>').policy == 'grow' and one('<./+:______>').name is None

def test_header_too_long_is_error():
    _, iss = scan_text('<./longername:>', 'x.md'); assert any(e[0] == 'E' and 'header leaves' in e[3] for e in iss)

def test_comment_only_default_outside_prose():
    s, iss = scan_text('echo <./x____>\n# <./owner:____>\n', 'run.sh'); assert [x.name for x in s] == ['owner']
    s, _ = scan_text('val <./a:___> # <./b:___>', 'notes.unknownext'); assert [x.name for x in s] == ['b']
    s, _ = scan_text('val <./a:___>', 'readme.md'); assert [x.name for x in s] == ['a']
    s, _ = scan_text('val <./a:___>', 'readme.md', mode='comments'); assert s == []

def test_hash_in_string_is_not_a_comment():
    s, _ = scan_text('url = "http://x/#a" <./v:____>\n', 'c.py'); assert s == []
    s, _ = scan_text('url = "http://x/#a"  # <./v:____>\n', 'c.py'); assert [x.name for x in s] == ['v']

def test_unexpand_safe():
    t = 'Status: <./status:________________> ok\n'
    r = subprocess.run(['unexpand', '-a'], input=t, capture_output=True, text=True).stdout
    assert r == t

def test_ellipsis_prefers_word_boundary_and_cjk_cells():
    assert fill_text('<./s~:________________>', {'s': 'shipped to production today'}) == '<./s~:shipped to…_____>'
    out = fill_text('<./n:______>|', {'n': '中文'})
    assert display_width(out) == display_width('<./n:______>|')

def test_block_v02():
    t = '<./notes:______________>\n<./|' + '_' * 19 + '>'
    out = fill_text(t, {'notes': 'one two three four five'})
    s = one(out); assert s.block_value() == 'one two three four five' and len(s.conts) == 1

T = 'Title: <./title:______________>\nOwner: <./owner:_______>\nBody text stays.\n'

def test_verify_ok_and_audit():
    new = fill_text(T, {'title': 'Ship v0.2', 'owner': 'Adam'})
    r = verify(T, new, 'x.md'); assert r['ok'] and [c['slot'] for c in r['changed']] == ['title', 'owner']

@pytest.mark.parametrize('mut,why', [
    (lambda t: t.replace('Body text stays.', 'Body text changed.'), 'outside slots'),
    (lambda t: t.replace('<./owner:_______>', '<./owner:Adam_____>'), 'width changed'),
    (lambda t: t.replace('<./owner:_______>', '<./boss:________>'), 'header changed'),
    (lambda t: t.replace('<./owner:_______>', 'Adam'), 'slot count'),
    (lambda t: t + 'extra <./x:___>\n', 'slot count'),
])
def test_verify_violations(mut, why):
    r = verify(T, mut(T), 'x.md'); assert not r['ok'] and any(why in v for v in r['violations'])

def test_verify_allow_list():
    new = fill_text(T, {'title': 'x', 'owner': 'y'})
    r = verify(T, new, 'x.md', allow={'title'}); assert not r['ok'] and 'owner' in r['violations'][0]
    assert fill_text(T, {'title': 'x'}, allow={'title'})
    with pytest.raises(SlotError, match='not in the allowed'): fill_text(T, {'owner': 'x'}, allow={'title'})

def test_verify_grow_block_may_add_lines():
    t = '# <./n+:______>\n# <./|' + '_' * 8 + '>\nprint(1)\n'
    new = fill_text(t, {'n': 'aa bb cc dd ee ff gg hh ii'}, path='a.py')
    assert new.count('\n') > t.count('\n') and verify(t, new, 'a.py')['ok']

def test_cli_check_base_and_git_base(tmp_path, capsys, monkeypatch):
    f = tmp_path / 'a.md'; f.write_text(T); b = tmp_path / 'base.md'; b.write_text(T)
    assert main(['fill', str(f), '--set', 'owner=Adam', '-i']) == 0
    assert main(['check', str(f), '--base', str(b)]) == 0
    f.write_text(f.read_text().replace('stays', 'moved'))
    assert main(['check', str(f), '--base', str(b)]) == 1
    assert 'NOT fill-safe' in capsys.readouterr().out
    monkeypatch.chdir(tmp_path)
    for c in (['init', '-q'], ['add', 'base.md'], ['-c', 'user.email=a@b', '-c', 'user.name=a', 'commit', '-qm', 'x']):
        subprocess.run(['git', *c], check=True)
    (tmp_path / 'base.md').write_text(fill_text(T, {'title': 'Hi'}))
    assert main(['check', 'base.md', '--git-base', 'HEAD']) == 0

def test_mcp_server_roundtrip(tmp_path):
    (tmp_path / 'doc.md').write_text(T)
    srv = Server(str(tmp_path))
    init = srv.handle(dict(jsonrpc='2.0', id=1, method='initialize', params={}))
    assert init['result']['serverInfo']['name'] == 'dotslot'
    names = [t['name'] for t in srv.handle(dict(jsonrpc='2.0', id=2, method='tools/list'))['result']['tools']]
    assert names == ['dotslot_scan', 'dotslot_fill', 'dotslot_check']
    call = lambda n, **a: json.loads(srv.handle(dict(jsonrpc='2.0', id=3, method='tools/call',
                                     params=dict(name=n, arguments=a)))['result']['content'][0]['text'])
    assert [s['name'] for s in call('dotslot_scan', path='doc.md')['slots']] == ['title', 'owner']
    r = call('dotslot_fill', path='doc.md', values={'owner': 'Adam'}); assert r['written']
    assert call('dotslot_check', path='doc.md', base_text=T)['ok']
    assert 'outside the server root' in call('dotslot_scan', path='../x')['error']
    assert 'slot holds' in call('dotslot_fill', path='doc.md', values={'owner': 'x' * 40})['error']

def test_new_block_is_well_formed(capsys):
    assert main(['new', 'notes', '--width', '20', '--lines', '3', '--comment', '# ']) == 0
    out = capsys.readouterr().out
    s, iss = scan_text(out, 'a.py'); assert not iss and len(s[0].conts) == 2 and s[0].width == 20

def test_repad_fixes_dropped_padding(tmp_path, capsys):
    b = tmp_path / 'b.md'; b.write_text(T); f = tmp_path / 'f.md'
    f.write_text(T.replace('<./owner:_______>', '<./owner:Adam>'))
    assert not verify(T, f.read_text(), 'x.md')['ok']
    assert main(['repad', str(f), '--base', str(b), '-i']) == 0
    assert verify(T, f.read_text(), 'x.md')['ok']

def test_markdown_emphasis_warning_and_code_span():
    _, iss = scan_text('Fill <./_____> and <./_____> here', 'a.md'); assert sum('emphasis' in i[3] for i in iss) == 2
    _, iss = scan_text('Fill `<./_____>` and `<./_____>` here', 'a.md'); assert not iss
    _, iss = scan_text('Fill <./     > here', 'a.md'); assert not iss

import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from slot.core import scan_text, fill_text, SlotError
from slot.cli import main

def one(t, path='x.md'):
    s, _ = scan_text(t, path); assert len(s) == 1; return s[0]

def test_width_counts_name_and_spaces():
    s = one('a <./status    > b')
    assert (s.width, s.name, s.kind, s.capacity) == (10, 'status', 'named', 3)
    assert one('<./     >').width == 5 and one('<./     >').capacity == 4

def test_fill_keeps_closing_column():
    t = 'x <./owner      > | y'
    out = fill_text(t, {'owner': 'Adam'})
    assert out == 'x <./owner=Adam > | y' and out.index('>') == t.index('>')

def test_cjk_and_emoji_padding_by_cells():
    out = fill_text('<./n      >|', {'n': '中文'})          # cap 4
    assert out == '<./n=中文 >|'
    from slot.width import display_width
    assert display_width(out) == display_width('<./n      >|')
    with pytest.raises(SlotError): fill_text('<./n     >', {'n': '中文🚀'})

def test_refill_and_clear_roundtrip():
    t = '<./a        >'
    f1 = fill_text(t, {'a': 'one'}); f2 = fill_text(f1, {'a': 'two'})
    assert f2 == '<./a=two    >'
    assert fill_text(f2, {}, clear=('a',)) == t
    assert fill_text(fill_text(t, {'a': 'x'}), {'a': 'x'}) == fill_text(t, {'a': 'x'})  # idempotent

def test_unnamed_by_index():
    assert fill_text('<./   > <./    >', {'@2': 'ok'}) == '<./   > <./=ok >'

def test_policies():
    assert fill_text('<./s~      >', {'s': 'shipped today'}) == '<./s~=ship…>'
    assert fill_text('<./s+   >', {'s': 'longer'}) == '<./s+=longer>'
    assert fill_text('<./s     >', {'s': 'abcdefg'}, default_policy='truncate') == '<./s=abcd>'
    with pytest.raises(SlotError, match='overflow policy: error'): fill_text('<./s!  >', {'s': 'abc'})

def test_forbidden_chars_and_escape():
    with pytest.raises(SlotError, match='--escape'): fill_text('<./v        >', {'v': 'a > b'})
    assert fill_text('<./v        >', {'v': 'a > b'}, escape=True) == '<./v=a › b  >'

def test_block_wrap_and_overflow():
    t = '<./notes        >\n<./|            >'
    out = fill_text(t, {'notes': 'one two three four'})
    assert out.split('\n') == ['<./notes=one two>', '<./|three four  >']
    with pytest.raises(SlotError, match='left over'): fill_text(t, {'notes': 'w ' * 40})
    g = fill_text('# <./n+       >\n# <./|        >', {'n': 'aa bb cc dd ee ff gg hh'})
    assert all(l.startswith('# <./') and l.endswith('>') for l in g.split('\n')) and len(g.split('\n')) > 2

def test_block_mismatch_and_orphan():
    _, iss = scan_text('<./n     >\n<./|  >', 'x.md'); assert any('width' in m for *_, m in iss)
    _, iss = scan_text('<./|   >', 'x.md'); assert any('no named slot' in m for *_, m in iss)

def test_comment_mode_for_code():
    t = 'cat <./in >out\n# owner: <./owner     >\nx = "<./s   >"\n'
    s, iss = scan_text(t, 'run.sh')
    assert [x.name for x in s] == ['owner'] and sum('outside a comment' in m for *_, m in iss) == 2
    s, _ = scan_text('/* <./a   > */ int x; // <./b   >', 'a.c'); assert [x.name for x in s] == ['a', 'b']
    s, _ = scan_text('<!-- <./a    > -->', 'p.html'); assert s[0].name == 'a'

def test_malformed_ignored():
    s, iss = scan_text('cat <./input.txt >out <./ok    >\n<./x\n<./>', 'x.md')
    assert [x.name for x in s] == ['ok']
    sev = sorted(i[0] for i in iss); assert sev.count('E') == 2 and sev.count('W') == 1

def test_cli_check_and_fit(tmp_path, capsys):
    f = tmp_path / 'a.md'; f.write_text('x' * 70 + ' <./status      >\n')
    assert main(['check', str(f)]) == 0
    assert main(['check', str(f), '--require-filled']) == 1
    assert main(['fit', str(f), '--targets', '80,100']) == 1      # 70+1+16 = 87 > 80
    out = capsys.readouterr().out; assert '80:over' in out and '100:ok' in out and 'static' in out
    assert main(['fill', str(f), '--set', 'status=ok', '-i']) == 0
    assert 'status=ok' in f.read_text()

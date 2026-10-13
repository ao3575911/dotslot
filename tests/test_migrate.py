import pytest
from dotslot.migrate import convert, migrate_text
from dotslot.core import scan_text
from dotslot.cli import main

@pytest.mark.parametrize('old,new', [
    ('status   ', 'status:__'),
    ('status=done ', 'status:done_'),
    ('~=42  ', '~:42__'),
    ('=42  ', '42___'),
    ('~    ', '~:___'),
    ('s+=x', 's+:x'),
    ('|more text ', '|more text_'),
    ('      ', '______'),
    ('=key: v ', 'key\\: v_'),
])
def test_convert(old, new):
    assert convert(old) == new
    assert len(new) == len(old)

@pytest.mark.parametrize('cur', ['status:____', 'done_____', 'a:x=y_', '______', 'v:a\\>b__'])
def test_current_syntax_untouched(cur):
    assert convert(cur) is None

def test_trailing_underscore_is_current_syntax():
    assert migrate_text('x <./=a_>\n', 'a.txt')[1] == []

def test_migrate_file_roundtrip(tmp_path, capsys):
    f = tmp_path / 'a.txt'
    f.write_text('Owner: <./owner=alice   >\nNotes: <./notes          >\n       <./|              >\n')
    assert main(['migrate', '--check', str(f)]) == 1
    assert main(['migrate', '-i', str(f)]) == 0
    t = f.read_text()
    assert t == 'Owner: <./owner:alice___>\nNotes: <./notes:_________>\n       <./|______________>\n'
    slots, issues = scan_text(t, 'a.txt')
    assert [s.name for s in slots] == ['owner', 'notes'] and slots[0].value == 'alice' and slots[1].conts
    assert [i for i in issues if i[0] == 'E'] == []
    assert main(['migrate', '--check', str(f)]) == 0               # idempotent

def test_code_only_in_comments():
    t, ch, _ = migrate_text('x = "<./a=1 >"  # <./b=2 >\n', 'a.py')
    assert t == 'x = "<./a=1 >"  # <./b:2_>\n' and len(ch) == 1

def test_space_pad():
    assert convert('status=done  ', ' ') == 'status:done  '

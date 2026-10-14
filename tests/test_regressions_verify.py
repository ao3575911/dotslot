import subprocess, sys
from dotslot.cli import main

def test_fill_in_place_keeps_crlf(tmp_path):
    f = tmp_path / 'a.py'; f.write_bytes(b'# <./n:____>\r\nx=1\r\n')
    assert main(['fill', '-i', str(f), '--set', 'n=ab']) == 0
    assert f.read_bytes() == b'# <./n:ab__>\r\nx=1\r\n'

def test_git_base_unknown_ref_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subprocess.run(['git', 'init', '-q'], check=True)
    (tmp_path / 'a.py').write_text('# <./n:____>\n')
    subprocess.run(['git', '-c', 'user.email=a@b', '-c', 'user.name=a', 'add', '.'], check=True)
    subprocess.run(['git', '-c', 'user.email=a@b', '-c', 'user.name=a', 'commit', '-qm', 'i'], check=True)
    assert main(['check', '--git-base', 'no-such-ref', 'a.py']) == 2
    assert main(['check', '--git-base', 'HEAD', 'a.py']) == 0

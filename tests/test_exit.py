import signal, subprocess, sys, time
from dotslot import __version__
from dotslot.cli import main

def test_missing_file_is_clean_error(capsys):
    assert main(['check', 'does-not-exist.md']) == 2
    assert 'Traceback' not in capsys.readouterr().err

def test_version(capsys):
    try: main(['--version'])
    except SystemExit as e: assert e.code == 0
    assert __version__ in capsys.readouterr().out

def test_mcp_exits_cleanly_on_eof_and_signals():
    r = subprocess.run([sys.executable, '-m', 'dotslot.mcp'], input=b'', capture_output=True)
    assert (r.returncode, r.stderr) == (0, b'')
    for sig in (signal.SIGINT, signal.SIGTERM):
        p = subprocess.Popen([sys.executable, '-m', 'dotslot.mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.5); p.send_signal(sig); _, err = p.communicate(timeout=10)
        assert p.returncode == 0 and b'Traceback' not in err

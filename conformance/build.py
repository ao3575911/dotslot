"""Regenerate conformance/fixtures/*.json from CASES using the Python reference implementation.
Run: python conformance/build.py   (review the diff before committing: fixtures are the contract)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from run import evaluate  # noqa: E402

def _corpus():
    import unicodedata
    out = []
    for c in list(range(0x20, 0x3000, 37)) + list(range(0x3000, 0x10000, 211)) + list(range(0x1F000, 0x1FB00, 13)) + list(range(0x20000, 0x30000, 4099)):
        ch = chr(c)
        if unicodedata.category(ch) in ('Cs', 'Co', 'Cn', 'Cc'): continue
        out.append(ch)
    out += ['e\u0301', '👍🏽', '👨\u200d👩\u200d👧', '❤️', '☺\ufe0f', '⌚\ufe0e', '🇦🇺', '🇦', 'a\u200bb', 'ｆｕｌｌ', '\x1b[31mred\x1b[0m', 'नमस्ते', 'กำ']
    return out
WIDTH_CORPUS = _corpus()
G = '# <./notes+:__________>\n# <./|________________>\nx = 1\n'
M = 'Owner: `<./owner:____________>`\n'
CASES = [
 # --- scan: grammar
 ('scan-empty-unnamed', 'Unnamed empty slot: capacity equals width.', dict(op='scan', path='a.txt', input='x <./__________> y\n')),
 ('scan-named', 'Named slot: header counts against capacity.', dict(op='scan', path='a.txt', input='<./status:____>\n')),
 ('scan-filled-named', 'Filled named slot.', dict(op='scan', path='a.txt', input='<./status:done__>\n')),
 ('scan-filled-unnamed', 'Filled unnamed slot.', dict(op='scan', path='a.txt', input='<./done_____>\n')),
 ('scan-space-pad', 'Space padding is read.', dict(op='scan', path='a.txt', input='<./name:    >\n')),
 ('scan-policies', 'Policies ! ~ + before the colon or alone.', dict(op='scan', path='a.txt', input='<./a!:____> <./b~:____> <./c+:_> <./~:______>\n')),
 ('scan-escapes', 'Escaped value characters; width counts the escaped form.', dict(op='scan', path='a.txt', input='<./v:a\\>b\\_\\\\__>\n')),
 ('scan-zero-width', 'Zero-width slot is an error.', dict(op='scan', path='a.txt', input='x <./> y\n')),
 ('scan-unterminated', 'Unterminated slot is an error.', dict(op='scan', path='a.txt', input='x <./abc\n')),
 ('scan-tab-invalid', 'A tab inside a slot makes it invalid (warning, ignored).', dict(op='scan', path='a.txt', input='<./a\t__>\n')),
 ('scan-no-capacity', 'Header that leaves no cell is an error.', dict(op='scan', path='a.txt', input='<./status:>\n')),
 ('scan-no-capacity-grow', 'Grow slot may start with zero capacity.', dict(op='scan', path='a.txt', input='<./s+:>\n')),
 ('scan-block', 'Named head plus continuations at the same column form a block.', dict(op='scan', path='a.txt', input='<./notes:__________>\n<./|_______________>\n<./|_______________>\n')),
 ('scan-block-width-mismatch', 'Continuation width must equal head width.', dict(op='scan', path='a.txt', input='<./notes:__________>\n<./|____>\n')),
 ('scan-orphan-cont', 'Continuation without a head is an error.', dict(op='scan', path='a.txt', input='<./|______>\n')),
 ('scan-name-widths', 'Same name with different widths warns.', dict(op='scan', path='a.txt', input='<./a:____> <./a:______>\n')),
 ('scan-wide-chars', 'East Asian wide characters count 2 cells.', dict(op='scan', path='a.txt', input='<./n:日本__>\n')),
 ('scan-emoji', 'Emoji grapheme cluster counts 2 cells.', dict(op='scan', path='a.txt', input='<./n:👍🏽___>\n')),
 # --- scan: modes
 ('mode-code-outside-comment', 'In code files slots outside comments are ignored (warning).', dict(op='scan', path='a.py', input='x = "<./____>"\n')),
 ('mode-code-in-comment', 'Slot inside a # comment counts.', dict(op='scan', path='a.py', input='x = 1  # <./owner:______>\n')),
 ('mode-marker-in-string', 'Comment markers inside strings are skipped.', dict(op='scan', path='a.py', input='s = "# <./a:____>"  # <./b:____>\n')),
 ('mode-js-comment', '// marks a comment in .js.', dict(op='scan', path='a.js', input='f(); // <./todo:______>\n')),
 ('mode-unknown-ext', 'Unknown extensions accept every marker.', dict(op='scan', path='a.zzz', input='-- <./a:____>\n; <./b:____>\n')),
 ('mode-prose-override', 'mode=prose counts bare slots in code files.', dict(op='scan', path='a.py', mode='prose', input='x = "<./____>"\n')),
 ('mode-markdown-warning', "Markdown: '_' outside a code span warns.", dict(op='scan', path='a.md', input='Owner: <./owner:____>\n')),
 ('mode-markdown-codespan', 'Markdown: inside backticks no warning.', dict(op='scan', path='a.md', input=M)),
 # --- fill
 ('fill-named', 'Fill pads to the original width with the slot pad.', dict(op='fill', path='a.md', input=M, values={'owner': 'alice'})),
 ('fill-by-index', 'Fill by @N index.', dict(op='fill', path='a.txt', input='<./______> <./______>\n', values={'@2': 'b'})),
 ('fill-space-pad', 'A space-padded slot keeps space padding.', dict(op='fill', path='a.txt', input='<./name:      >\n', values={'name': 'bo'})),
 ('fill-overflow-error', 'Default policy: overflow is an error.', dict(op='fill', path='a.txt', input='<./s:____>\n', values={'s': 'too long'})),
 ('fill-ellipsis', 'Ellipsis policy cuts and appends an ellipsis.', dict(op='fill', path='a.txt', input='<./s~:__________>\n', values={'s': 'hello wonderful world'})),
 ('fill-grow', 'Grow policy widens the slot.', dict(op='fill', path='a.txt', input='<./s+:__>\n', values={'s': 'longer'})),
 ('fill-escape', 'Fill escapes > < \\ and a trailing _.', dict(op='fill', path='a.txt', input='<./v:____________>\n', values={'v': 'a>b<c\\d_'})),
 ('fill-unnamed-colon', 'Unnamed value that looks like a header is escaped.', dict(op='fill', path='a.txt', input='<./____________>\n', values={'@1': 'key: v'})),
 ('fill-tab-rejected', 'Inline values cannot contain tabs or newlines.', dict(op='fill', path='a.txt', input='<./s:______>\n', values={'s': 'a\tb'})),
 ('fill-unknown-name', 'Filling a missing name is an error.', dict(op='fill', path='a.txt', input='<./s:______>\n', values={'x': 'a'})),
 ('fill-allow', 'Allow list refuses other slots.', dict(op='fill', path='a.txt', input='<./s:______>\n', values={'s': 'a'}, allow=['t'])),
 ('fill-block-wrap', 'Block value wraps at word boundaries across lines.', dict(op='fill', path='a.txt', input='<./notes:__________>\n<./|_______________>\n<./|_______________>\n', values={'notes': 'the quick brown fox jumps over'})),
 ('fill-block-overflow', 'Block overflow is an error by default.', dict(op='fill', path='a.txt', input='<./notes:____>\n<./|__________>\n', values={'notes': 'the quick brown fox jumps over the lazy dog'})),
 ('fill-block-grow', 'Grow block inserts continuation lines.', dict(op='fill', path='a.py', input=G, values={'notes': 'the quick brown fox jumps over the lazy dog'})),
 ('fill-refuses-errors', 'Fill refuses a file with scan errors.', dict(op='fill', path='a.txt', input='<./s:____> <./>\n', values={'s': 'a'})),
 ('fill-wide', 'Wide characters are measured in cells.', dict(op='fill', path='a.txt', input='<./n:______>\n', values={'n': '日本'})),
 ('fill-crlf-free', 'Text outside the slot is untouched.', dict(op='fill', path='a.py', input='a = 1  # <./o:____> tail\nb = 2\n', values={'o': 'x'})),
 # --- check
 ('check-pass', 'Only slot interiors changed.', dict(op='check', path='a.md', base=M, input='Owner: `<./owner:alice_______>`\n')),
 ('check-outside-changed', 'Text outside a slot changed.', dict(op='check', path='a.md', base=M, input='Owner:  `<./owner:alice_______>`\n')),
 ('check-width-changed', 'Width change is a violation.', dict(op='check', path='a.md', base=M, input='Owner: `<./owner:alice>`\n')),
 ('check-raw-gt', 'A raw > closes the slot early.', dict(op='check', path='a.md', base=M, input='Owner: `<./owner:a>b_________>`\n')),
 ('check-header-changed', 'Header change is a violation.', dict(op='check', path='a.txt', base='<./a:____>\n', input='<./b:____>\n')),
 ('check-count-changed', 'Slot count change is a violation.', dict(op='check', path='a.txt', base='<./a:____>\n', input='<./a:____> <./b:____>\n')),
 ('check-allow-pass', 'Changed slot in allow list passes.', dict(op='check', path='a.txt', base='<./a:____> <./b:____>\n', input='<./a:x___> <./b:____>\n', allow=['a'])),
 ('check-allow-fail', 'Changed slot not in allow list fails.', dict(op='check', path='a.txt', base='<./a:____> <./b:____>\n', input='<./a:____> <./b:x___>\n', allow=['a'])),
 ('check-allow-index', 'Unnamed slot allowed by @N.', dict(op='check', path='a.txt', base='<./____>\n', input='<./x___>\n', allow=['@1'])),
 ('check-grow-lines', 'Lines added by a + block are tolerated.', dict(op='check', path='a.py', base=G, input='# <./notes+:the quick_>\n# <./|brown fox jumps_>\n# <./|over the lazy___>\n# <./|dog_____________>\nx = 1\n')),
 ('check-trailing-ws', 'Trailing whitespace counts by default.', dict(op='check', path='a.txt', base='a\n<./s:____>\n', input='a  \n<./s:____>\n')),
 ('check-ignore-ws', 'ignore_whitespace tolerates trailing whitespace.', dict(op='check', path='a.txt', base='a\n<./s:____>\n', input='a  \n<./s:____>\n', ignore_whitespace=True)),
 ('check-block-height', 'Block height change is a violation.', dict(op='check', path='a.txt', base='<./n:____>\n<./|______>\n', input='<./n:____>\n')),
 ('width-corpus', 'Cell widths of single code points and clusters (wcwidth model).', dict(op='width', input=WIDTH_CORPUS)),
 # --- parser-based comment detection (fixtures marked requires: treesitter)
 ('ts-py-multiline-string', 'A # inside a triple-quoted string is not a comment.', dict(op='scan', path='a.py', requires=['treesitter'], input='s = """\n# <./a:____>\n"""  # <./b:____>\n')),
 ('ts-js-template-literal', 'A // inside a multi-line template literal is not a comment.', dict(op='scan', path='a.js', requires=['treesitter'], input='const s = `\n// <./a:____>\n`; // <./b:____>\n')),
 ('ts-c-block-comment', 'A slot on an inner line of a /* */ block comment counts.', dict(op='scan', path='a.c', requires=['treesitter'], input='/*\n * owner: <./owner:______>\n */\nint x;\n')),
 ('ts-py-fill-multiline-string', 'Fill ignores the slot inside a string.', dict(op='fill', path='a.py', requires=['treesitter'], input='s = """\n# <./a:____>\n"""  # <./a:____>\n', values={'a': 'x'})),
]

if __name__ == '__main__':
    d = os.path.join(os.path.dirname(__file__), 'fixtures')
    for f in os.listdir(d):
        if f.endswith('.json'): os.remove(os.path.join(d, f))
    for cid, desc, case in CASES:
        case = dict(id=cid, description=desc, **case); case['expect'] = evaluate(case, strict=True)
        with open(os.path.join(d, cid + '.json'), 'w', encoding='utf-8') as f:
            json.dump(case, f, ensure_ascii=False, indent=1); f.write('\n')
    print(len(CASES), 'fixtures')

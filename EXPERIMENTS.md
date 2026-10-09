# EXPERIMENTS — `<./    >` slot syntax

All outputs below are copied from `experiments/out/{a..g}.txt`, which `experiments/run.sh` regenerates. Environment: Python 3.13.5, wcwidth 0.9.2, markdown-it-py, black 26.10.0, bash, node 20.19.2, gcc, gofmt, GNU coreutils `fmt`/`unexpand`. Unit tests: `.venv/bin/python -m pytest -q tests` → **12 passed**. Nothing was published.

Ratings: **works** (does what the spec promises, no surprises) · **awkward** (works but costs the user something) · **fails** (breaks, or needs a workaround outside the syntax).

## Summary
| exp | question | rating |
|---|---|---|
| a | inline fill / refill / clear keeps the `>` column | works: column held for ASCII, CJK, emoji, ZWJ · awkward: the `=` and the name eat capacity |
| b | is the raw syntax safe in host formats? | works: Markdown/HTML/strings show it as literal text · **fails** in code position (bash, Python, JS, C syntax errors) · awkward: renderers collapse the padding |
| c | comment-embedded form in 7 languages | works: py/sh/js/c/go/html/sql still compile after fill; black leaves it alone · awkward: gofmt moves the `>` column · fails: `#` inside a string counts as a comment |
| d | editor and text-tool hygiene | works: trailing-whitespace strip, `git diff --check` · **fails**: `unexpand -a` (tabs make slots invalid), `fmt` reflow splits slots |
| e | named slots: ambiguity and forbidden characters | works: `=` and `\|` in values · awkward: a typed word reads as a *name*, `>` needs `--escape`, same name with two widths · fails: a name longer than the slot |
| f | block slots and overflow policies | works: policy matrix, grow in comment blocks (still compiles), CJK, hard split · awkward: word wrap wastes cells, hand-aligning blocks is error-prone, ellipsis cuts mid-word |
| g | `slot fit` wrap probe | works: static width known before filling, the threshold is exact · awkward: padding spaces are soft-wrap points, `+` makes width depend on the value, emoji = `maybe` |

## (a) Inline round-trip and capacity
```
work/a.md:1:7  @1 owner   inline w=10 x1 cap=4  empty
work/a.md:1:29 @2 date    inline w=10 x1 cap=5  empty
work/a.md:1:51 @3 -       inline w=10 x1 cap=9  empty
'Owner: <./owner=Adam>  Date: …' cells 65
'Owner: <./owner=中文>  Date: …' cells 65
'Owner: <./owner=🚀ok>  Date: …' cells 65
'Owner: <./owner=👨‍👩‍👧  >  Date: …' cells 65      original cells: 65
$ slot fill a.md --set @3=2026-10-10
error: @3: value is 10 cells, slot holds 9 (overflow policy: error)
clear restores original: yes · fill twice == fill once: yes
```
- **Works:** the `>` column holds in every case, and clear plus idempotent re-fill hold too.
- **Awkward:** the width counts the name, so a 10-character slot named `owner` holds only 4 cells. The `=` marker costs 1 cell even on an unnamed slot, so a 10-character date does not fit a 10-wide slot.

## (b) Host formats, raw syntax outside comments
```
Markdown: <p>Status: &lt;./status      &gt; done</p>          (literal text; spaces kept in HTML source)
html.parser: DATA 'Owner: ' / DATA '<' / DATA './owner      > end'   (not a tag)
bash -n b.sh: syntax error near unexpected token `newline'  (`<./name` is a redirection)
python: SyntaxError: invalid syntax · node: SyntaxError: Unexpected token '.' · gcc: expected expression before '.' token
JSON/YAML/Python strings: {"k": "<./owner     >"}  (just text)
slot scan (auto mode): '<./name    >' is outside a comment in a code file (ignored)
```
- **Works:** prose formats and strings treat the slot as plain text. `<.` cannot start a CommonMark or HTML tag.
- **Fails:** in a code position, all four languages reject it. In shell, `cmd <./x >out` is a valid redirection, and it would run. That is why the spec ignores code-position slots in code files.
- **Awkward:** rendered HTML collapses the padding (see d4), so the width can only be seen in monospace source.

## (c) Comment-embedded form
```
# owner: <./owner=Adam     >
def f():  # status: <./status~=shipp…>
// owner: <./owner=Adam     >          const x = 1; /* status: <./status~=shipp…> */
<!-- owner: <./owner=Adam     > -->    SELECT 1; -- status: <./status~=shipp…>
py_compile / bash -n / node --check / gcc -fsyntax-only: [exit 0] ×4
black: unchanged
gofmt:  var x = 1 // status: …   →   var x = 1          // status: <./status~=shipp…>
url = "http://x/#a" <./v    >   → scanned as a slot (# in a string)
```
- **Works:** every language still compiles after the fill, and black leaves the comments alone.
- **Awkward:** gofmt realigns trailing comments. The interior survives, but the `>` column moves, so `fit` results computed before gofmt go stale.
- **Fails:** the comment test is a line-local heuristic, so `#` inside a string gives a false positive. Fixing it needs a real tokenizer per language.

## (d) Editor and text-tool hygiene
```
sed 's/[ \t]*$//': unchanged (interiors end at '>' so nothing is trailing) · git diff --check: clean
unexpand -a:  Status: <./status^I    > ok   → W: '<./status\t    >' is not a valid slot (ignored)
fmt -w 30:    ok Notes: <./notes / >        → E: unterminated slot: '<./' without '>' on the same line
markdown-it:  <p>Status: &lt;./status           &gt; ok   (browser collapses the run of spaces)
counter-test with '_' padding (not in the tool): unexpand -a unchanged; fmt moves whole slot, cannot split it
```
- **Works:** stripping trailing whitespace and `git diff --check` leave slots alone. This is the main advantage of the closing `>`.
- **Fails:** space padding is fragile under tab conversion and paragraph reflow. Padding with `_` survived both in the counter-test (d5). That makes it the strongest candidate change for v0.2, at the cost of a less blank look.

## (e) Named slots: ambiguity and forbidden characters
```
width 10:  a cap=8 · ab cap=7 · status cap=3 · deadline cap=1 · longername cap=-1 (W: name leaves -1 cells)
'Done? <./yes   >'  → @1 yes  empty   (a typed answer is parsed as a slot *name*)
--set v='> done'            → error: value contains ['>'] … (use --escape)
--set v='> done' --escape   → <./v=› done           >
--set v='a=b|c'             → <./v=a=b|c            >   (re-scans as value 'a=b|c')
'<./who    > and <./who         >' → W: name 'who' used with different widths [7, 12]; fill who=Adam → error at the narrower one
```
- **Awkward:**
  - Adam's `> quote` style cannot go into a slot without being rewritten to `›`.
  - Hand-typing a value without the `=` silently turns it into an empty slot with that name.
- **Fails:** a name longer than its slot cannot hold any value.

## (f) Block slots and overflow policies
```
value 'shipped to production today' into 14-wide slots (fill is atomic per file):
error     -  error: value is 27 cells, slot holds 12      ellipsis  -  <./s=shipped to …>|
truncate  -  <./s=shipped to p>|                          grow      -  <./s=shipped to production today>|
any       !  error · any ~  <./s~=shipped to…>| · any +  <./s+=shipped to production today>|   (marker wins)
block 49 cells, 48-char value → error: 6 cells left over   (word wrap wastes line ends)
--overflow ellipsis → <./notes=First line of notes   > / <./|that wraps across the bloc…>
f0 hand-typed block, continuation 1 cell too wide → E: continuation width 17 != head width 16
grow in a Python comment block:
    # notes: <./notes+=a long   >
    #        <./|explanation    >   … (+3 lines, '# ' prefix copied) → py_compile [exit 0]
<!-- <./notes+=a long   > -->  … (' -->' suffix copied)
CJK: <./notes=价格 和 交割 日期 需要> / <./|再次 确认 一下 好的        >
long word: <./notes=supercalifragilisticex> / <./|pialidocious-and-more      >
```
- **Works:** the policies and marker precedence behave as specified, and grow keeps code compiling.
- **Awkward:**
  - Lining up blocks by hand is error-prone. I mistyped one while writing this experiment, and `check` caught it.
  - Word wrap means a value can fail to fit even when it is shorter than the block's total capacity.
  - Ellipsis cuts mid-word.

## (g) `slot fit` wrap probe (slotfit logic reused)
```
x*60 + ' <./status         >'   → col 61..80 (line 80) static  80:ok 100:ok 120:ok   (known before filling)
sweep, 18-cell slot, value 'ship today':
 col 60..78 ok · 62..80 ok · 64..82 over: word ">" moves · 66..84 over: "today" moves · 68..86 over: "today" moves
grow slot after 66 'y's:  ok →77 ok · 'ship it' →81 over, "it>" moves · 'ship it today' →87 "today>" moves · +🚀 →90
tabs (--tab 8): 'a\t' and 'abcdefg\t' both start the slot at col 8; 'abcdefgh\t' at col 16
emoji: 69 z + <./s=👨‍👩‍👧 ok…>  → line 81, per-codepoint 85
check --fit 80 on the 80-cell line: ok
```
- **Works:**
  - A fixed-width slot makes the wrap decision static: `start_col + 3 + W + 1 > target`, whatever the value is. This answers Adam's observation that the last word wraps depending on length and column.
  - It also flags the problem before anyone types a value.
- **Awkward:**
  - Padding spaces inside a slot are soft-wrap points, so an editor can split a slot visually and leave `>` alone on the next line (col 64 case).
  - Under `+`, typing pushes `>` right, and the line wraps exactly as it did before slots existed.
  - Emoji sequences remain `maybe` across terminals (see /workspace/artifacts/slotfit/EXPERIMENTS.md).

## Prior art (URLs fetched 2026-10-10 from the box, HTTP 200)
| system | URL | overlap | difference |
|---|---|---|---|
| Perl formats (`perlform`) | https://perldoc.perl.org/perlform | **closest match.** Field width = length of the picture field (`@<<<<`). Truncation, `...` ellipsis, `^<<<` multi-line block fill, `~~` repeat-until-done (≈ grow) | pictures are output templates, separate from the data. Not filled in place, not re-fillable, not comment-embedded |
| POSIX `printf` field width | https://pubs.opengroup.org/onlinepubs/9699919799/utilities/printf.html | fixed-width fields | width is a number in the format, not visible as space |
| Python format spec | https://docs.python.org/3/library/string.html | `{name:<10}` named, padded fields | template is consumed; byte/char-based, not cells |
| COBOL PICTURE clause | https://en.wikipedia.org/wiki/COBOL | width given by repeated picture chars, e.g. `X(10)` | record layout, not text |
| VS Code snippet placeholders | https://code.visualstudio.com/docs/editor/userdefinedsnippets | named, tab-stop fill-ins `${1:name}` | editor-only, vanish after fill, no width |
| Mustache | https://mustache.github.io/mustache.5.html | named holes | no width, template consumed |
| Cog | https://nedbatchelder.com/code/cog/ | generator code embedded in comments, output rewritten in place, re-runnable | regenerates whole regions; no fixed width |
| Org-mode tables | https://orgmode.org/manual/Tables.html | fixed-width cells kept aligned in plain text | the tool realigns and the width grows; table-only |
| GitHub issue forms | https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms | named fill-in fields with required ones (≈ `check --require`) | YAML/UI, not inline text |
| CommonMark raw HTML / GFM | https://spec.commonmark.org/0.31.2/ · https://github.github.com/gfm/ | why `<./` renders as literal text (a tag name must start with a letter) | — |
| UAX #11 East Asian Width · wcwidth · terminal-unicode-core (mode 2027) | https://www.unicode.org/reports/tr11/ · https://github.com/jquast/wcwidth · https://github.com/contour-terminal/terminal-unicode-core | the cell-width model `fit` relies on | — |
| EditorConfig | https://editorconfig.org/ | `trim_trailing_whitespace` is why the closing `>` matters | — |
| pyte | https://github.com/selectel/pyte | VT emulator used to cross-check widths (exp. g in slotfit) | — |

## Verdict
- **Keep, narrowly.** `<./    >` works as a fixed-width, re-fillable field in monospace prose and in code comments. Its one real advantage over prior art is that **the slot is the layout**: width, wrap and alignment are known before filling and survive re-filling (a, g). Perl formats have had width-by-picture, ellipsis and block fill since the 1980s, so the novel part is that the field is filled in place, re-fillable and comment-embedded, not the field idea itself.
- **Don't** use it raw in code (b), or rely on it in rendered Markdown (b, d4).
- **Changes for v0.2:**
  1. Pad with `_` or `·` instead of spaces, which survived `unexpand` and `fmt` (d5), or have `check` re-validate after formatters.
  2. Drop the `=` tax for unnamed slots, e.g. by treating any non-space interior of an unnamed slot as a value with a leading-space rule.
  3. Write names as a suffix (`<./    >status`?) or allow `W` to exclude the name, because "width includes the name" costs most of the capacity (e1).
  4. Make `grow` opt-in per slot only (it is), and have `fit` warn on `+` slots near a target.
  5. Use a per-language tokenizer for comment detection.
- **Name ideas**, all checked free on PyPI and npm on 2026-10-10 (HTTP 404): **dotslot** (from `./`), **slotfmt**, **fillslot**, **inslot**, **fixslot**, **widthslot**, **gapline**. `ruled` is taken on npm.

---
# v0.2 (`dotslot/`, `bin/dotslot`): re-tests and experiment (h)
Outputs come from `experiments/out/v02.txt` and `experiments/out/h.txt`, which `experiments/run_v02.sh` regenerates. Tests: 42 passing (12 v0.1 + 30 v0.2). v0.1 stays in `slot/` and `bin/slot`, so the (a)–(g) outputs above can still be reproduced.

## Re-tests of the v0.1 awkward/fails list
| v0.1 finding | v0.2 change | result |
|---|---|---|
| a3: 10-char date fails a 10-wide slot | unnamed slots have no header and no `=` | `Date: <./2026-10-10>`: **works** |
| e2: a typed word reads as a name | names need `name:` | `<./yes___>` is value `'yes'`: **works** |
| e3: `>` refused or rewritten to `›` | backslash escapes, written by the tool | `<./v:\> done, a\<b___>` scans back to `'> done, a<b'`: **works** |
| e1: name longer than its slot (warning) | now an error | `E: longername: header leaves 0 cells`: **works** |
| b: slots in code positions | comment-only everywhere except prose extensions (.md .txt .rst .adoc .org) | `.sh` code slot and unknown-extension code slot ignored: **works** |
| c: `#` in a string counted as a comment | quote-aware comment finder | `"http://x/#a" <./v:____>` ignored; `# <./w:____>` found: **works** (heuristic: no multi-line strings) |
| d2/d3: `unexpand`, `fmt` break space-padded slots | `_` padding (spaces still read) | `unexpand -a` unchanged; `fmt -w 30` moves whole slots, check ok: **works** |
| f0: hand-aligned blocks miss by 1 | `dotslot new NAME --width W --lines H --comment '# '` | generated blocks always line up: **works** (and the v0.2 test fixtures I typed by hand were off by 1 twice) |
| f: ellipsis cut mid-word | prefers the last word boundary if it keeps ≥ ⅔ of capacity | `<./s~:shipped to…_____>`: **works** |

## (h) Fill-safe AI edits: simulated LLM patches checked by `dotslot check --git-base HEAD`
Each patch was made in a scratch git repo, recorded with `git diff`, reset, and re-applied with `git apply`.

| case | what the "agent" did | check result | rating |
|---|---|---|---|
| h1 | filled 3 slots by hand-editing the diff | **NOT fill-safe**: `status: width changed 34 -> 36`. My hand-written "good" patch miscounted the padding | works (caught a real slip) |
| h1b | `dotslot repad --base` | fill-safe, 3 slots changed | works |
| h2 | filled a slot and also "fixed" `version 3.1` → `3.2` in the legal line | VIOLATION, text outside slots changed (shows the line) | works |
| h3 | `<./owner:Adam>` with the padding dropped | VIOLATION width 18 → 10; `repad` then fill-safe | works |
| h4 | renamed `date:` to `when:` | VIOLATION header changed | works |
| h5 | raw `>` in a value | VIOLATION: the slot closes early and the tail lands outside | works (caught); awkward (the message is indirect) |
| h6 | `--allow status`, agent also filled `owner` | VIOLATION, owner not in the allowed list | works |
| h7 | YAML comment slot fill plus 2 trailing spaces elsewhere | VIOLATION, outside text changed | works, but strict: may need `--ignore-whitespace` |
| h8 | Claude Code PostToolUse hook, legal-line edit | hook exit 2 with the violation on stderr (fed back to the agent); a clean fill gives exit 0 | works |
| h9 | MCP server over real stdio | `initialize` → `tools/list` = scan/fill/check → `dotslot_fill` wrote 2 slots (block wrapped) → check fill-safe; `../../etc/passwd` → `outside the server root` | works |

**Finding:** check is a reliable gate, but the agent should not hand-edit slots. In h1 and h3, two of the plain-diff fills got the padding wrong. Filling through the tool (MCP `dotslot_fill` or the CLI) gives correct widths by construction, and `repad` rescues hand edits.

## (i) Does `_` padding break Markdown? (new risk created by v0.2)
```
'Fill <./_____> and <./_____> here'   -> <p>Fill &lt;./<em><strong><strong>&gt; and &lt;./</strong></strong></em>&gt; here</p>
'A <./a:_x_> and <./b:_y_>'           -> <p>A &lt;./a:<em>x</em>&gt; and &lt;./b:<em>y</em>&gt;</p>
'Owner: <./owner:Adam________>  Date: <./__________>'  -> literal (no pairing)
'Fill `<./_____>` and `<./_____>` here' -> <p>Fill <code>&lt;./_____&gt;</code> and <code>&lt;./_____&gt;</code> here</p>
dotslot check i.md → W: '_' outside a code span can render as emphasis in Markdown; wrap it in backticks (×2)
dotslot new owner --width 12 --md → `<./owner:______>`
```
- **Fails:** two bare `_` slots on one Markdown line can turn into emphasis when rendered.
- **Works:** backtick code spans render the slot literally, in monospace, with its width visible. That also fixes the d4 problem, where padding collapsed on render.
- v0.2 now warns about bare `_` slots in `.md` files, and `dotslot new --md` emits the code-span form.

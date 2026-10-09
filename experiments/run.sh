#!/usr/bin/env bash
# Runs experiments (a)-(g); every output file under experiments/out/ is produced by this script.
set -u
cd "$(dirname "$0")"; W=work; O=out; S=../bin/slot; PY=python3; [ -x ../.venv/bin/python ] && PY=../.venv/bin/python
rm -rf $W/*; mkdir -p $W
sec(){ echo; echo "### $*"; }
run(){ echo "\$ $*"; "$@" 2>&1; echo "[exit $?]"; }

{ ### (a) inline round-trip + width/capacity
sec "a1 capacity: width counts every char between <./ and >, name included"
printf 'Owner: <./owner     >  Date: <./date      >  Free: <./          >\n' > $W/a.md
run $S scan $W/a.md
sec "a2 fill keeps the closing > column (ASCII, CJK, emoji)"
for v in Adam 中文 🚀ok 👨‍👩‍👧; do $S fill $W/a.md --set owner="$v" | $PY -c "
import sys; sys.path.insert(0,'..'); from slot.width import display_width as d
l=sys.stdin.read().rstrip('\n'); print(repr(l), 'cells', d(l))"; done
echo "original cells: $($PY -c "import sys;sys.path.insert(0,'..');from slot.width import display_width as d;print(d(open('$W/a.md').read().rstrip()))")"
sec "a3 10-char date into a 10-wide unnamed slot (the '=' costs one cell)"
run $S fill $W/a.md --set @3=2026-10-10
sec "a4 refill / clear / idempotency"
$S fill $W/a.md --set owner=Adam > $W/a1.md; $S fill $W/a1.md --set owner=Bo > $W/a2.md; $S fill $W/a2.md --clear owner > $W/a3.md
cat $W/a1.md $W/a2.md $W/a3.md; cmp -s $W/a.md $W/a3.md && echo "clear restores original: yes" || echo "clear restores original: NO"
$S fill $W/a1.md --set owner=Adam | cmp -s - $W/a1.md && echo "fill twice == fill once: yes"
} > $O/a.txt

{ ### (b) host formats: is the raw syntax safe outside comments?
sec "b1 Markdown (markdown-it-py, CommonMark)"
printf 'Status: <./status      > done\n\n`<./code   >` in code\n' > $W/b.md
$PY -c "from markdown_it import MarkdownIt; print(MarkdownIt().render(open('$W/b.md').read()))"
sec "b2 HTML: html.parser sees text, then whitespace collapses on render"
$PY -c "
from html.parser import HTMLParser
class P(HTMLParser):
    def handle_starttag(s,t,a): print('TAG',t)
    def handle_data(s,d): print('DATA',repr(d))
P().feed('<p>Owner: <./owner      > end</p>')"
sec "b3 shell: a slot in code is an input redirection"
printf 'echo hello <./name    >\n' > $W/b.sh; run bash -n $W/b.sh; (cd $W && run bash b.sh)
sec "b4 python / JS / C with a slot in code (not comment)"
printf 'x = 1 <./v   > 2\n' > $W/b.py; run $PY -m py_compile $W/b.py
printf 'let x = 1 <./v   > 2;\n' > $W/b.js; run node --check $W/b.js
printf 'int x = 1 <./v   > 2;\n' > $W/b.c; run gcc -fsyntax-only $W/b.c
sec "b5 in strings (YAML/JSON/Python) the slot is just text"
printf 'owner: "<./owner     >"\n' > $W/b.yaml; run $PY -c "import json;print(json.dumps({'k':'<./owner     >'}))"
sec "b6 slot tool in auto mode refuses code-position slots"
run $S scan $W/b.sh $W/b.py $W/b.yaml
} > $O/b.txt

{ ### (c) comment-embedded form across languages, filled, then compiled/formatted
cat > $W/c.py <<'P'
# owner: <./owner          >
def f():  # status: <./status~       >
    return 1
P
cat > $W/c.sh <<'P'
#!/bin/sh
# owner: <./owner          >
echo hi # status: <./status~       >
P
cat > $W/c.js <<'P'
// owner: <./owner          >
const x = 1; /* status: <./status~       > */
P
cat > $W/c.c <<'P'
// owner: <./owner          >
int x = 1; /* status: <./status~       > */
P
cat > $W/c.go <<'P'
package main

// owner: <./owner          >
var x = 1 // status: <./status~       >
var longername = 2 // other
P
cat > $W/c.html <<'P'
<!-- owner: <./owner          > -->
<p>hi</p> <!-- status: <./status~       > -->
P
cat > $W/c.sql <<'P'
-- owner: <./owner          >
SELECT 1; -- status: <./status~       >
P
for f in c.py c.sh c.js c.c c.go c.html c.sql; do
  sec "c $f"; $S fill $W/$f --set owner=Adam --set status='shipped and tagged' -i; cat $W/$f
done
sec "c compile/syntax checks after fill"
run $PY -m py_compile $W/c.py; run bash -n $W/c.sh; run node --check $W/c.js; run gcc -fsyntax-only $W/c.c
sec "c formatters: black, gofmt (does padding survive? does the > column move?)"
cp $W/c.py $W/c_black.py; black -q $W/c_black.py; diff $W/c.py $W/c_black.py && echo "black: unchanged"
gofmt $W/c.go > $W/c_fmt.go; diff $W/c.go $W/c_fmt.go; echo "[gofmt diff exit $?]"
run $S scan $W/c_fmt.go
sec "c false positive: '#' inside a string counts as a comment marker"
printf 'url = "http://x/#a" <./v    >\n' > $W/c_fp.py; run $S scan $W/c_fp.py
} > $O/c.txt

{ ### (d) editor & text-tool hygiene
printf 'Status: <./status           > ok\nNotes: <./notes                >\n       <./|                    >\n' > $W/d.md
sec "d1 strip trailing whitespace (sed 's/[ \\t]*$//') + git diff --check"
sed 's/[ \t]*$//' $W/d.md | cmp -s - $W/d.md && echo "unchanged: interiors end at '>' so nothing is trailing"
(cd $W && git init -q dd && cp d.md dd/ && cd dd && git add d.md && git -c user.email=x@x -c user.name=x commit -qm x && git diff --check HEAD~0 && echo "git diff --check: clean")
sec "d2 unexpand -a (spaces->tabs) then scan"
unexpand -a $W/d.md > $W/d_tab.md; cat -A $W/d_tab.md | head -3; run $S scan $W/d_tab.md
sec "d3 paragraph reflow: fmt -w 30 splits a slot across lines"
fmt -w 30 $W/d.md > $W/d_fmt.md; cat $W/d_fmt.md; run $S check $W/d_fmt.md
sec "d4 Markdown renderers collapse the padding (width invisible when rendered)"
$PY -c "from markdown_it import MarkdownIt; print(MarkdownIt().render(open('$W/d.md').read()))"
sec "d5 counter-test (not supported by the tool): the same slots padded with '_' instead of spaces"
printf 'Status: <./status___________> ok\nNotes: <./notes________________>\n' > $W/d_us.md
unexpand -a $W/d_us.md | cmp -s - $W/d_us.md && echo "unexpand -a: unchanged"
fmt -w 30 $W/d_us.md; echo "(fmt can still move a whole slot to another line, but cannot split it)"
} > $O/d.txt

{ ### (e) named slots: ambiguity and forbidden characters
sec "e1 capacity left after the name (width 10)"
for n in a ab status deadline longername; do
  pad=$(( 10 - ${#n} )); [ $pad -lt 0 ] && pad=0
  printf '<./%s%*s>\n' "$n" $pad '' ; done > $W/e.md
run $S scan $W/e.md
sec "e2 a word typed into an empty slot reads as a *name*, not a value"
printf 'Done? <./yes   >\n' > $W/e2.md; run $S scan $W/e2.md
sec "e3 values containing > < (Adam's '> quote' case), = and |"
printf '<./v                  >\n' > $W/e3.md
run $S fill $W/e3.md --set v='> done'
run $S fill $W/e3.md --set v='> done' --escape
run $S fill $W/e3.md --set v='a=b|c'
$S fill $W/e3.md --set v='a=b|c' | ../bin/slot scan /dev/stdin --mode prose
sec "e4 same name, two widths"
printf '<./who    > and <./who         >\n' > $W/e4.md; run $S check $W/e4.md; run $S fill $W/e4.md --set who=Adam
} > $O/e.txt

{ ### (f) block slots & overflow policies
sec "f1 policy matrix: value 'shipped to production today' (27 cells) into width-14 slots"
for m in '' '!' '~' '+'; do printf '<./s%s%*s>|\n' "$m" $(( 13 - ${#m} )) '' > $W/f_$m.md; done
echo "fill is atomic: one overflowing slot aborts the whole file, so each slot is its own file here"
for p in error ellipsis truncate grow; do for m in '' '!' '~' '+'; do
  printf '%-9s marker=%-2s ' "$p" "${m:--}"; $S fill $W/f_$m.md --set s='shipped to production today' --overflow $p 2>&1 | head -1; done; done
sec "f2 block wraps by words; error when it does not fit (a 48-char value fails a 49-cell block: word wrap wastes line ends)"
printf 'Notes: <./notes                       >\n       <./|                           >\n' > $W/f2.md
run $S fill $W/f2.md --set notes='First line of notes that wraps across the block.'
run $S fill $W/f2.md --set notes='First line of notes that wraps across.'
run $S fill $W/f2.md --set notes='First line of notes that wraps across the block and then keeps on going well past the end.'
run $S fill $W/f2.md --set notes='First line of notes that wraps across the block and then keeps on going well past the end.' --overflow ellipsis
sec "f0 hand-typed block whose continuation is 1 cell too wide (happened while writing f3)"
printf '# <./notes+          >\n# <./|                >\n' > $W/f0.py; run $S check $W/f0.py
sec "f3 grow on a comment-embedded block adds lines with the comment prefix (python + html)"
printf 'def f():\n    # notes: <./notes+          >\n    #        <./|               >\n    return 1\n' > $W/f3.py
$S fill $W/f3.py --set notes='a long explanation that needs several more lines than the block has' -i; cat $W/f3.py; run $PY -m py_compile $W/f3.py
printf '<!-- <./notes+          > -->\n<!-- <./|               > -->\n' > $W/f3.html
$S fill $W/f3.html --set notes='a long explanation that needs several more lines than the block has'
sec "f4 CJK into a block: odd cell left as padding"
$S fill $W/f2.md --set notes='价格 和 交割 日期 需要 再次 确认 一下 好的'
sec "f5 a single word longer than a line is hard-split"
$S fill $W/f2.md --set notes='supercalifragilisticexpialidocious-and-more'
} > $O/f.txt

{ ### (g) slot fit: wrap probe with the new syntax
sec "g1 an empty slot reserves its width, so the wrap is known before filling"
printf '%s <./status         >\n' "$(printf 'x%.0s' $(seq 1 60))" > $W/g.md
run $S fit $W/g.md --preview
sec "g2 sweep: slot start column vs 80 (18-cell slot: <./ + 14 interior + >; value 'ship today')"
for c in 60 62 64 66 68; do printf '%*s<./s             >\n' $c '' > $W/g2.md; $S fit $W/g2.md --set s='ship today' --preview | head -3; done
sec "g3 grow (+) and typing that pushes '>' : the line width now depends on the value"
printf '%s <./s+    >\n' "$(printf 'y%.0s' $(seq 1 66))" > $W/g3.md
for v in ok 'ship it' 'ship it today' 'ship it today 🚀'; do $S fit $W/g3.md --set s="$v" --preview | head -4; done
sec "g4 tab before the slot: column depends on tab stop"
printf 'a\t<./s     >\nabcdefg\t<./s     >\nabcdefgh\t<./s     >\n' > $W/g4.md; run $S fit $W/g4.md --targets 16,20 --tab 8
sec "g5 emoji sequence inside a slot: wcwidth vs per-codepoint terminals"
printf '%s<./s       >\n' "$(printf 'z%.0s' $(seq 1 69))" > $W/g5.md; run $S fit $W/g5.md --set s='👨‍👩‍👧 ok'
sec "g6 check --fit gate"
run $S check $W/g.md --fit 80
} > $O/g.txt
echo done

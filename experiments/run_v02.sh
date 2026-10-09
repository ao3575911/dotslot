#!/usr/bin/env bash
# v0.2 re-tests of the v0.1 awkward/fails list, and experiment (h) fill-safe AI edits.
set -u
cd "$(dirname "$0")"; ROOT=$(cd .. && pwd); export PATH="$ROOT/bin:$PATH"
W=$ROOT/experiments/work2; O=$ROOT/experiments/out; rm -rf $W; mkdir -p $W
sec(){ echo; echo "### $*"; }
run(){ echo "\$ $*"; "$@" 2>&1; echo "[exit $?]"; }

{ sec "v1 (a3) a 10-char date now fits a 10-wide unnamed slot"
printf 'Date: <./__________>\n' > $W/v1.md; run dotslot fill $W/v1.md --set @1=2026-10-10
sec "v2 (e2) a typed word is a value; names need a ':' header"
printf 'Done? <./yes___>  Owner: <./owner:____>\n' > $W/v2.md; run dotslot scan $W/v2.md
sec "v3 (e3) '>' and friends are escaped, not rewritten"
printf '<./v:________________>\n' > $W/v3.md
run dotslot fill $W/v3.md --set v='> done, a<b'; dotslot fill $W/v3.md --set v='> done, a<b' | dotslot scan - 
sec "v4 (e1) a header longer than the slot is now an error"
printf '<./longername:>\n' > $W/v4.md; run dotslot check $W/v4.md
sec "v5 (b) code-position slots are ignored by default; unknown extensions are comment-only"
printf 'echo hello <./name____>\n# owner <./owner:______>\n' > $W/v5.sh; printf 'x <./a:___> ; <./b:___>\n' > $W/v5.weird
run dotslot scan $W/v5.sh $W/v5.weird
sec "v6 (c) '#' inside a string no longer counts as a comment"
printf 'url = "http://x/#a" <./v:____>\nurl = "http://x/#a"  # <./w:____>\n' > $W/v6.py; run dotslot scan $W/v6.py
sec "v7 (d2,d3) '_' padding survives unexpand -a and fmt cannot split a slot"
printf 'Status: <./status:_____________> ok\nNotes: <./notes:____________________>\n' > $W/v7.md
unexpand -a $W/v7.md | cmp -s - $W/v7.md && echo "unexpand -a: unchanged"
fmt -w 30 $W/v7.md > $W/v7f.md; cat $W/v7f.md; run dotslot check $W/v7f.md
sec "v8 (f0) blocks generated, not hand-aligned"
run dotslot new notes --width 26 --lines 3 --comment '# '
sec "v9 (f) ellipsis prefers a word boundary"
printf '<./s~:________________>\n' > $W/v9.md; run dotslot fill $W/v9.md --set s='shipped to production today'
} > $O/v02.txt

{ ### (h) fill-safe AI edits: simulated LLM patches validated by `dotslot check`
R=$W/repo; mkdir -p $R && cd $R && git init -q && git config user.email a@b && git config user.name a
cat > release.md <<'P'
# Release v0.2
Owner:   <./owner:____________>   Date: <./date:__________>
Status:  <./status~:__________________________>
Notes:   <./notes:____________________________>
         <./|_________________________________>
Do not edit below this line: legal text, version 3.1.
P
cat > deploy.yaml <<'P'
service: api
replicas: 3            # <./replicas_note:______________________>
image: api:1.4.2       # owner <./owner:____________>
P
git add . && git commit -qm base
patch_from(){ git diff > "$1"; git checkout -q -- .; }   # record the simulated LLM patch, then reset

sec "h1 good agent: fills slots only (patch applied with git apply)"
python3 - <<'P'
t=open('release.md').read()
t=t.replace('<./owner:____________>','<./owner:Adam________>').replace('<./date:__________>','<./date:2026-10-17>')
t=t.replace('<./status~:__________________________>','<./status~:ready for tag_______________>')
open('release.md','w').write(t)
P
patch_from h1.diff; cat h1.diff | sed -n '5,12p'; git apply h1.diff; run dotslot check release.md --git-base HEAD
sec "h1b the hand-written 'good' patch miscounted padding by 2 cells; repad, then check"
git show HEAD:release.md > /tmp/base_release.md; run dotslot repad release.md --base /tmp/base_release.md -i
run dotslot check release.md --git-base HEAD; git checkout -q -- .

sec "h2 helpful agent: fills a slot and also 'fixes' the legal line"
sed -i 's/<.\/owner:____________>/<.\/owner:Adam________>/; s/version 3.1/version 3.2/' release.md
patch_from h2.diff; git apply h2.diff; run dotslot check release.md --git-base HEAD; git checkout -q -- .

sec "h3 sloppy agent: drops the padding (most common LLM slip), then repad"
sed -i 's/<.\/owner:____________>/<.\/owner:Adam>/' release.md
patch_from h3.diff; git apply h3.diff; run dotslot check release.md --git-base HEAD
git show HEAD:release.md > /tmp/base_release.md; run dotslot repad release.md --base /tmp/base_release.md -i
run dotslot check release.md --git-base HEAD; git checkout -q -- .

sec "h4 agent renames a slot header"
sed -i 's/<.\/date:__________>/<.\/when:__________>/' release.md
patch_from h4.diff; git apply h4.diff; run dotslot check release.md --git-base HEAD; git checkout -q -- .

sec "h5 agent writes a raw '>' inside a value"
sed -i 's/<.\/status~:__________________________>/<.\/status~:a > b ready_________________>/' release.md
patch_from h5.diff; git apply h5.diff; run dotslot check release.md --git-base HEAD; git checkout -q -- .

sec "h6 permission scope: only 'status' may change, agent also fills owner"
dotslot fill release.md --set status=green --set owner=Adam -i
run dotslot check release.md --git-base HEAD --allow status; git checkout -q -- .

sec "h7 YAML comment slot + trailing whitespace added elsewhere"
dotslot fill deploy.yaml --set replicas_note='scaled for launch' -i; sed -i 's/^service: api$/service: api  /' deploy.yaml
run dotslot check deploy.yaml --git-base HEAD; git checkout -q -- .

sec "h8 Claude Code PostToolUse hook on an outside-slot edit (exit 2 feeds stderr back to the agent)"
sed -i 's/version 3.1/version 9/' release.md
echo '{"tool_name":"Edit","tool_input":{"file_path":"release.md"}}' | run "$ROOT/integrations/claude-code/dotslot-hook.sh"
git checkout -q -- .
echo '{"tool_name":"Edit","tool_input":{"file_path":"release.md"}}' > /tmp/hookin.json
dotslot fill release.md --set owner=Adam -i; run bash -c "$ROOT/integrations/claude-code/dotslot-hook.sh < /tmp/hookin.json"; git checkout -q -- .

sec "h9 MCP server over real stdio (initialize, tools/list, dotslot_fill, out-of-root path)"
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"dotslot_fill","arguments":{"path":"release.md","values":{"owner":"Adam","notes":"Tag after CI is green; announce on Monday."}}}}' \
 '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"dotslot_scan","arguments":{"path":"../../etc/passwd"}}}' \
 | PYTHONPATH=$ROOT $ROOT/.venv/bin/python -m dotslot.mcp --root . | python3 -c "
import json,sys
for l in sys.stdin:
    m=json.loads(l); r=m.get('result',{})
    if 'tools' in r: print(m['id'], 'tools:', [t['name'] for t in r['tools']])
    elif 'content' in r: print(m['id'], 'isError' if r['isError'] else 'ok', r['content'][0]['text'][:300])
    else: print(m['id'], json.dumps(r)[:120])"
cat release.md | sed -n 2,5p; run dotslot check release.md --git-base HEAD; git checkout -q -- .
} > $O/h.txt
echo done
{ sec "i1 '_' padding in Markdown: two bare slots on a line render as emphasis (markdown-it-py, CommonMark)"
cd "$ROOT/experiments"
$ROOT/.venv/bin/python -c "
from markdown_it import MarkdownIt
md=MarkdownIt()
for t in ['Fill <./_____> and <./_____> here', 'A <./a:_x_> and <./b:_y_>', 'Owner: <./owner:Adam________>  Date: <./__________>', 'Fill \`<./_____>\` and \`<./_____>\` here']:
    print(repr(t)); print('   ->', md.render(t).strip())"
printf 'Fill <./_____> and <./_____> here\n' > $W/i.md; run dotslot check $W/i.md
run dotslot new owner --width 12 --md
} > $O/i.txt

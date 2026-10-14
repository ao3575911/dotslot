#!/usr/bin/env bash
# Claude Code PostToolUse hook: after Edit/Write, prove the file changed only inside slots.
# Exit 2 sends stderr back to Claude (https://docs.anthropic.com/en/docs/claude-code/hooks).
set -u
f=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))') || exit 0
[ -n "$f" ] && [ -f "$f" ] || exit 0
top=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0   # not in a git work tree
# Claude Code passes absolute paths: make the path relative to the work tree root, then run from there.
rel=$(python3 -c 'import os,sys; print(os.path.relpath(os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])))' "$f" "$top") || exit 0
case "$rel" in ../*|..) exit 0 ;; esac                        # outside this repository
cd "$top" || exit 0
git cat-file -e "HEAD:./$rel" 2>/dev/null || exit 0          # new file: nothing to compare
git show "HEAD:./$rel" | grep -q '<\./' || exit 0            # file had no slots: not our business
out=$(dotslot check --git-base HEAD -- "$rel" 2>&1) && exit 0
echo "dotslot: this file is fill-only. Revert edits outside <./…> slots or use the dotslot_fill tool." >&2
echo "$out" >&2
exit 2

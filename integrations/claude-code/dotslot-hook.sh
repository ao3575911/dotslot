#!/usr/bin/env bash
# Claude Code PostToolUse hook: after Edit/Write, prove the file changed only inside slots.
# Exit 2 sends stderr back to Claude (https://docs.anthropic.com/en/docs/claude-code/hooks).
f=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
[ -n "$f" ] && [ -f "$f" ] || exit 0
git cat-file -e "HEAD:./$f" 2>/dev/null || exit 0            # new file: nothing to compare
git show "HEAD:./$f" | grep -q '<\./' || exit 0              # file had no slots: not our business
out=$(dotslot check "$f" --git-base HEAD 2>&1) && exit 0
echo "dotslot: this file is fill-only. Revert edits outside <./…> slots or use the dotslot_fill tool." >&2
echo "$out" >&2
exit 2

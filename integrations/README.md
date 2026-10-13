# Agent kits

Copy-paste setups for Claude Code, Cursor and aider. Each one does the same three things: give the agent the
`dotslot_fill` tool (or command), tell it the file is fill-only, and run `dotslot check` after every edit.

Prerequisite for all three: `pip install dotslot` (provides `dotslot` and `dotslot-mcp`).

## Claude Code

```bash
cp integrations/claude-code/.mcp.json .                         # MCP server: dotslot_scan, dotslot_fill, dotslot_check
mkdir -p .claude/skills && cp -r integrations/claude-code/skills/dotslot .claude/skills/
cp integrations/claude-code/settings.json .claude/settings.json # or merge the "hooks" key into your existing file
chmod +x integrations/claude-code/dotslot-hook.sh
```

The `PostToolUse` hook runs `dotslot check --git-base HEAD` after `Edit`, `MultiEdit` and `Write`. On a violation
it exits 2, so Claude sees the reason and reverts. Files without slots at `HEAD` are skipped.

## Cursor

```bash
mkdir -p .cursor/rules
cp integrations/cursor/.cursor/mcp.json .cursor/mcp.json
cp integrations/cursor/.cursor/rules/dotslot.mdc .cursor/rules/
```

Enable the `dotslot` server under *Settings → MCP*. The rule tells the agent to fill through `dotslot_fill` and to run
`dotslot check FILE --git-base HEAD` before finishing.

## aider

```bash
cp integrations/aider/.aider.conf.yml .
cp integrations/aider/CONVENTIONS.md .   # then set read: [CONVENTIONS.md] in .aider.conf.yml
```

`lint-cmd` with `auto-lint: true` makes aider run `dotslot check --git-base HEAD` after each edit and send failures
back to the model.

## Any other agent

Paste [`AGENTS.md`](AGENTS.md) into your repo's `AGENTS.md`, and add the pre-commit hook or GitHub Action from the
main [README](../README.md) as the gate.

## MCP options

`dotslot-mcp --root . [--allow owner,status]`

- `--root`: every path is resolved inside it; `..`, absolute paths and symlinks that leave it are refused.
- `--allow`: server-wide list of slots that `dotslot_fill` and `dotslot_check` may change. A per-call `allow`
  argument can narrow it, never widen it.
- Arguments are validated against each tool's input schema; bad types, missing or unknown properties return
  JSON-RPC error `-32602`.
- `dotslot_fill` with `dry_run: true` returns the unified diff without writing.

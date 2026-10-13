# Changelog

All notable changes are listed here. Versions follow [SemVer](https://semver.org).

## [Unreleased]

## [0.3.0] - 2026-10-14

### Added
- `check --ignore-whitespace`: trailing whitespace changes outside slots are not a violation (h7). Off by default.
- MCP: every tool call is validated against its input schema; bad types, missing required and unknown properties return JSON-RPC `-32602` with the failing path (e.g. `arguments.values.owner: expected string`).
- MCP: `allow` argument on `dotslot_fill` and `dotslot_check`, and a server-wide `dotslot-mcp --allow`. A per-call list can only narrow the server list.
- MCP: `ignore_whitespace` on `dotslot_check`; malformed JSON lines return `-32700` instead of stopping the server.
- Action: `ignore-whitespace` and `report` inputs, a `report` output, and a readable step summary (verdict, violations, JSON report).
- `integrations/README.md`: copy-paste setup for Claude Code, Cursor and aider.
- Tests for the h1–h9 exit gate (git repo, Claude Code hook, MCP over stdio). CI runs the Action on a 100-file change and checks it catches the violation in under 10 s.

### Changed
- MCP `dotslot_fill` `dry_run` returns `dry_run: true` and an `a/`/`b/` unified diff; a no-op fill does not rewrite the file.
- Action writes one JSON array for all files (was concatenated arrays), passes on no matched files, and fails with a clear message when the base revision is missing.
- pre-commit hooks are published: use `rev: v0.3.0` with `dotslot-check` and `dotslot-lint`.
- CI requires at least 70 passing tests and validates the pre-commit manifest.

## [0.2.1] - 2026-10-13

### Added
- Published to PyPI: `pip install dotslot`. The release workflow uploads the sdist and wheel through PyPI trusted publishing (`pypi` environment, no API token).
- `check` now prints a hint when a raw `>` in a value closes a slot early (h5), pointing to `\>` or `dotslot fill`.
- Offline regression tests for `parse_sets` (#5, thanks @1nfernet).

### Changed
- CI requires at least 42 passing tests instead of exactly 42 (#6).
- README: M8ven badge (#7); install from PyPI; test count updated.

## [0.2.0] - 2026-10-10

First public release.

### Added
- `dotslot` CLI: `scan`, `fill`, `check`, `fit`, `new`, `repad`.
- Fill-safe check: `check --base / --git-base / --allow` proves a diff changed only slot interiors, with each slot's width kept.
- MCP server (`dotslot-mcp`, or `python -m dotslot.mcp --root .`): `dotslot_scan`, `dotslot_fill`, `dotslot_check` over stdio, with paths confined to the root.
- Integrations: Claude Code (MCP, `PostToolUse` hook, skill), Cursor (MCP, rule), aider (lint-cmd), `AGENTS.md` snippet, pre-commit hooks (`dotslot-check`, `dotslot-lint`) and a composite GitHub Action.
- `SPEC.md` (v0.2) and `EXPERIMENTS.md` with reproducible runs (a–i, v02, h).

### Changed (from the v0.1 prototype)
- Padding uses `_` (spaces still read); unnamed slots cost no cells; names are written `name:`.
- Backslash escapes `\< \> \\ \_ \: \|`, written by the tool.
- Comment-only by default outside prose files; quote-aware comment detection.
- A header too long for its slot is an error.
- Ellipsis cuts at a word boundary.
- Markdown: `check` warns on bare `_` slots outside code spans.

### Known gaps
- Formatters such as gofmt can move the `>` column; run dotslot after them.
- Multi-line strings can fool the comment finder (tree-sitter planned for v1.0).
- Trailing whitespace counts as a violation (`--ignore-whitespace` planned for v0.3).
- Not yet on PyPI or npm (PyPI added in 0.2.1).

[Unreleased]: https://github.com/ao3575911/dotslot/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ao3575911/dotslot/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/ao3575911/dotslot/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ao3575911/dotslot/releases/tag/v0.2.0

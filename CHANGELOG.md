# Changelog

All notable changes are listed here. Versions follow [SemVer](https://semver.org).

## [Unreleased]

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
- Not yet on PyPI or npm.

[Unreleased]: https://github.com/ao3575911/dotslot/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ao3575911/dotslot/releases/tag/v0.2.0

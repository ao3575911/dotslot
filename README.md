[![M8ven Score](https://m8ven.ai/badge/mcp/ao3575911-dotslot-ia87ds?v=c3035f8aeacd04053e6285ac74d5eccb)](https://m8ven.ai/mcp/ao3575911-dotslot-ia87ds?s=readme)

# dotslot

Let agents fill the blanks in a file, and prove they touched nothing else.

[![ci](https://github.com/ao3575911/dotslot/actions/workflows/ci.yml/badge.svg)](https://github.com/ao3575911/dotslot/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dotslot)](https://pypi.org/project/dotslot/)
[![npm](https://img.shields.io/npm/v/dotslot)](https://www.npmjs.com/package/dotslot)
· MIT · [Spec](SPEC.md) · [Changelog](CHANGELOG.md)

Mark the editable parts of a file with fixed-width slots. An agent or script fills them; `dotslot check`
proves the diff changed only the slots and that each slot kept its width, so columns and wraps stay put.
Works in Markdown, config files and code comments.

```text
Owner: `<./owner:____________>`   Status: `<./status~:____________>`

$ dotslot fill release.md --set owner=Adam --set status="ready for tag" -i
$ dotslot check release.md --git-base HEAD
release.md: fill-safe (2 slot(s) changed)
```

## Install

| Surface | Install |
|---|---|
| CLI (Python 3.10+) | `pip install dotslot` (optional: `pip install "dotslot[treesitter]"`) |
| CLI (Node 18+) | `npx dotslot` or `npm i -g dotslot` (`scan`, `fill`, `check`) |
| GitHub Action | `uses: ao3575911/dotslot@v0.8.1` ([Marketplace](https://github.com/marketplace/actions/dotslot-check)) |
| pre-commit | `repo: https://github.com/ao3575911/dotslot`, `rev: v0.8.1` |
| MCP server | `dotslot-mcp --root .` (installed with the Python package) |
| Editor extension | [Open VSX](https://open-vsx.org/extension/ao3575911/dotslot) `ao3575911.dotslot` (VS Code, Cursor, VSCodium) |

## Use

```bash
dotslot new owner --width 12                  # print a correctly sized slot
dotslot scan FILE                             # list slots, widths, capacity
dotslot fill FILE --set owner=Adam -i         # fill in place; width kept
dotslot check FILE --git-base HEAD            # prove only slots changed (--allow a,b to narrow)
dotslot check FILE --base OLD --ignore-whitespace
dotslot repad FILE --base OLD -i              # restore padding an editor dropped
dotslot migrate FILE -i                       # convert v0.1 `=` slots
dotslot fit FILE --targets 80,100,120         # where lines will wrap
dotslot fit FILE --fail-at 100                # exit 1 if any line is wider
```

Slot forms: `<./______>` unnamed, `<./owner:____>` named, `<./status~:____>` ellipsis on overflow
(`!` error, `+` grow). In Markdown, keep slots in backticks. Grammar: [SPEC.md](SPEC.md).
Values with control, bidi or zero-width characters are rejected; pass `--allow-unsafe-chars` to permit them.
Headers like `<./:___>` or `<./a b:__>` are errors.
Exit codes: `0` ok, `1` violation, `2` usage or input error.

## GitHub Action

```yaml
- uses: actions/checkout@v5
  with: { fetch-depth: 0 }
- uses: ao3575911/dotslot@v0.8.1
  with: { files: "docs/**/*.md config/*.yaml", allow: "status,owner" }
```

Inputs: `files` (required), `allow`, `base` (default: PR base SHA), `ignore-whitespace`, `report`
(default `dotslot-report.json`). Violations and the JSON report go to the step summary. No matched files
passes; a missing base revision fails.

## pre-commit

Run after formatters.

```yaml
- repo: https://github.com/ao3575911/dotslot
  rev: v0.8.1
  hooks: [{ id: dotslot-check }, { id: dotslot-lint }]
```

## Agents (MCP)

`dotslot-mcp` serves `dotslot_scan`, `dotslot_fill` and `dotslot_check` over stdio. Arguments are
schema-validated before any write, bad JSON gets a `-32700` reply, `dry_run` returns a diff, `allow` limits which slots may change, writes are atomic and
confined to `--root`. Ready-made setups: [Claude Code](integrations/claude-code), [Cursor](integrations/cursor/.cursor),
[aider](integrations/aider), and an [AGENTS.md snippet](integrations/AGENTS.md). See [integrations/README.md](integrations/README.md).

## Limits

dotslot is a check, not a sandbox. Without `dotslot[treesitter]`, comment detection is a line heuristic.
Formatters such as gofmt can move columns, so run dotslot after them. Trailing whitespace counts as a change
unless you pass `--ignore-whitespace`. Roadmap: [PLAN.md](PLAN.md).

## Development

`pip install -e ".[test]" && pytest -q` runs the Python tests and the shared [conformance](conformance/)
fixtures; `npm test` in `npm/` and `vscode/` runs the others. `slot/` and `bin/slot` are the v0.1 reference,
kept for [EXPERIMENTS.md](EXPERIMENTS.md); not installed.

## Licence

MIT. Releases are GPG-signed in CI with SHA256SUMS and build provenance; see [RELEASING.md](RELEASING.md)
and [SECURITY.md](SECURITY.md).

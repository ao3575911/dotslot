```
dotslot: let agents fill the blanks, and prove they touched nothing else.

Owner: `<./owner:____________>`   Status: `<./status~:____________>`

$ dotslot fill release.md --set owner=Adam --set status="ready for tag" -i
$ dotslot check release.md --git-base HEAD
release.md: fill-safe (2 slot(s) changed)

CLI · pre-commit · GitHub Action · MCP server (Claude Code, Cursor, aider)
```

[![ci](https://github.com/ao3575911/dotslot/actions/workflows/ci.yml/badge.svg)](https://github.com/ao3575911/dotslot/actions/workflows/ci.yml) · MIT · v0.2.0 · [Spec](SPEC.md) · [Experiments](EXPERIMENTS.md) · [Changelog](CHANGELOG.md)

## What it is

Mark the parts of a file that may change with `<./________>`. An agent or script fills those blanks and nothing else. `dotslot check` proves the diff touched only the blanks, and that each blank kept its width, so columns and line wraps stay put. It works in docs, configs and code comments.

A file with slots is **fill-only**. That turns "don't touch the rest" into a rule a machine can check.

## Install

Not on PyPI yet. Install from GitHub:

```bash
pip install "git+https://github.com/ao3575911/dotslot@v0.2.0"
dotslot --help
```

Requires Python 3.10+ and `wcwidth`.

## Use

```bash
dotslot new notes --width 26 --lines 3 --comment '# '   # generate a slot or block
dotslot scan FILE                                         # list slots, widths, capacity
dotslot fill FILE --set name=value -i                     # fill in place, width kept
dotslot check FILE --git-base HEAD [--allow a,b]          # prove only slots changed
dotslot repad FILE --base OLD -i                          # restore padding after a hand edit
dotslot fit FILE --targets 80,100,120                     # where will lines wrap?
```

Slot forms: `<./______>` (unnamed), `<./owner:____>` (named), `<./status~:____>` (ellipsis on overflow). In Markdown, put slots in backticks. Full grammar: [SPEC.md](SPEC.md).

## Integrations

| tool | files | what it does |
|---|---|---|
| MCP server | `dotslot-mcp --root .` | `dotslot_scan`, `dotslot_fill`, `dotslot_check` over stdio; fill verifies before writing; paths confined to root |
| Claude Code | [`integrations/claude-code/`](integrations/claude-code) | `.mcp.json`, a `PostToolUse` hook that exits 2 on a violation, and a skill |
| Cursor | [`integrations/cursor/.cursor/`](integrations/cursor/.cursor) | `mcp.json` and a fill-only rule |
| aider | [`integrations/aider/`](integrations/aider) | `lint-cmd: dotslot check --git-base HEAD` with auto-lint |
| any agent | [`integrations/AGENTS.md`](integrations/AGENTS.md) | snippet to paste into your `AGENTS.md` |
| pre-commit | [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) | `dotslot-check`, `dotslot-lint` |
| GitHub Action | [`action.yml`](action.yml) | checks PR files against the base SHA, writes a JSON report to the step summary |

pre-commit:

```yaml
- repo: https://github.com/ao3575911/dotslot
  rev: v0.2.0
  hooks: [{ id: dotslot-check }]
```

GitHub Action:

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: ao3575911/dotslot@v0.2.0
  with: { files: "docs/**/*.md config/*.yaml", allow: "status,owner" }
```

## Limits

dotslot is a check, not a sandbox. The comment finder is a heuristic until tree-sitter lands; formatters such as gofmt can move columns, so run dotslot after them; trailing whitespace counts as a change. See [CHANGELOG.md](CHANGELOG.md) for open items and [PLAN.md](PLAN.md) for the roadmap.

## Repository layout

- `dotslot/`: the v0.2 package (CLI, MCP server).
- `slot/`, `bin/slot`: the v0.1 reference, kept only so `experiments/run.sh` reproduces findings (a)–(g). Not installed.
- `tests/`: 42 tests (12 v0.1, 30 v0.2). Run `pip install -e ".[test]" && pytest -q`.
- `experiments/`: `run.sh` (a–g) and `run_v02.sh` (v02, h, i), with recorded output in `out/`.

## Licence

MIT. See [LICENSE](LICENSE). Releases are GPG-signed in CI and carry SHA256SUMS and build provenance; see [RELEASING.md](RELEASING.md).

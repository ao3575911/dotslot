# dotslot: plan (v0.2 → v1.0)

*Adam, 10 Oct 2026. Every decision cites the experiment behind it, by ID in `EXPERIMENTS.md` (a–i). Nothing is published yet.*

## 1. Thesis and pitch
**Thesis:** mark the parts of a file that may change, and get proof that nothing else did.

**10-second pitch:** dotslot marks the blanks in a file with `<./________>`. An AI agent or a script can fill those blanks and nothing else. `dotslot check` then proves the diff touched only the blanks, with each blank's width kept, so columns and line wraps stay put. It works in docs, configs and code comments, from the CLI, a pre-commit hook, a GitHub Action or an MCP server.

## 2. v0.2 spec changes (implemented in the prototype)
| change | why (finding) |
|---|---|
| Pad with `_` (spaces still read) | `unexpand -a` broke space padding, and `fmt` split slots in two (d2, d3). With `_`, both pass (v7). |
| Unnamed slots cost nothing; names are `name:` | `=` cost a cell, so a 10-char date failed a 10-wide slot (a3). A typed answer was read as a name (e2). Both fixed (v1, v2). |
| Backslash escapes `\< \> \\ \_ \: \|`, written by the tool | Values with `>`, such as my `> quote` style, were refused or rewritten (e3). They now round-trip exactly (v3). |
| Comment-only by default, except prose files | Raw slots are syntax errors in bash, Python, JS and C, and `cmd <./x >out` is a live shell redirect (b). |
| Quote-aware comment detection | `#` inside a string was mistaken for a comment (c). Fixed (v6). |
| A header too long for its slot is an error, not a warning | `<./longername:>` can never hold a value (e1, v4). |
| `dotslot new` generates slots and blocks | I hand-aligned blocks wrong three times while writing the tests (f0). |
| Ellipsis cuts at a word boundary | `shipp…` read badly (f). It now gives `shipped to…` (v9). |
| In Markdown, slots go in backticks; `check` warns on bare `_` slots | `_` padding renders as bold/italic when two slots share a line (i). A code span also shows the width when rendered, which fixes d4. |
| `check --base / --git-base / --allow`, plus `repad` | This is the flagship (§3). It is backed by h1–h9. |

**Still open:**
- gofmt moves the `>` column, so `fit` results computed before it go stale. Fix: run dotslot after formatters in pre-commit.
- Multi-line strings can fool the comment finder. v1.0 will use tree-sitter.
- Trailing whitespace counts as a violation (h7). v0.3 adds `--ignore-whitespace`.
- When a raw `>` closes a slot early, the diagnostic is indirect (h5). v0.3 adds a dedicated hint.

## 3. Flagship: fill-safe AI edits
Agents are good at filling templates and bad at leaving the rest alone. dotslot turns that into a rule a machine can check: **a fill-only file may change only inside its slots.**

**Experiment (h): simulated LLM patches, recorded with `git diff`, applied with `git apply`, then `dotslot check --git-base HEAD`.**

| case | result |
|---|---|
| Clean fill | fill-safe, with an audit line for each slot (h1b) |
| "Helpful" fix to a legal line | caught; the changed line is shown (h2) |
| Padding dropped | caught; `repad` fixes it (h3) |
| Slot renamed | caught (h4) |
| Raw `>` in a value | caught (h5) |
| Slot outside `--allow` filled | caught (h6) |
| Trailing whitespace added elsewhere | caught (h7) |

- **Hand-edited fills slip.** My own hand-written "good" patch miscounted the padding by 2 cells (h1), so the main path is tool-mediated filling, with `check` as the gate.
- **MCP server (built, v0.3 hardening):** `python -m dotslot.mcp --root .` exposes `dotslot_scan`, `dotslot_fill` and `dotslot_check`.
  - `dotslot_fill` verifies its own result before writing.
  - Paths are confined to the root.
  - Tested over real stdio (h9).
- **Claude Code** (`integrations/claude-code/`):
  - `.mcp.json` registers the MCP server.
  - A `PostToolUse` hook on `Edit|MultiEdit|Write` runs check and exits 2 on a violation, which sends the reason back to the agent (h8).
  - `skills/dotslot/SKILL.md` tells the agent to scan, fill through the tool, then check.
- **Cursor:** `.cursor/mcp.json`, plus `.cursor/rules/dotslot.mdc` (fill-only rule, check before finishing).
- **aider:** `.aider.conf.yml` sets `lint-cmd: dotslot check --git-base HEAD` with `auto-lint`, so aider re-prompts the model on failure. `CONVENTIONS.md` is passed as `read:`.
- **Everyone else:** `AGENTS.md` snippet, pre-commit (`.pre-commit-hooks.yaml`: `dotslot-check`, `dotslot-lint`) and a composite GitHub Action (`action.yml`). The Action checks PR files against the base SHA, takes an `--allow` list, and writes a JSON report to the step summary.

## 4. Secondary uses
- **Fixed-width records and reports:** `>` holds its column for ASCII, CJK and emoji (a2), and fills are idempotent (a4).
- **Aligned config and docs tables:** YAML and TOML comment slots keep alignment (h7, c). In Markdown tables, put slots in code spans (i).
- **Terminal UIs and CLI output templates:** widths are counted in wcwidth cells, so emoji widths that differ between terminals show up as `maybe` (g5).
- **Teaching worksheets and forms:** `` `<./______>` `` blanks in Markdown. `check --require-filled` marks incomplete work (CLI test).
- **Wrap lint for chat and terminal output:** `dotslot fit` knows where a line will wrap before anything is filled. It warns when start column + width crosses 80/100/120 (g1, g2).

## 5. Offering, in layers
1. **Open spec** (`SPEC.md`, CC-BY), with conformance tests taken from the pytest suite.
2. **CLI:** `pip install dotslot` (reference implementation), then `npx dotslot`. The npm port must pass the same conformance fixtures.
3. **VS Code extension** (Open VSX too):
   - highlight slots and show `w=18 cap=12` inlay hints
   - warn when a value overflows or the line crosses 80/100/120
   - "Fill slot" command
   - mark text outside slots as read-only in fill-only files (stretch)
4. **pre-commit hook and GitHub Action** (files exist now).
5. **MCP server** (exists now): shipped inside the Python package as `dotslot-mcp`.
6. **Paid layer: none at launch.** I'll revisit once more than 50 repos use the Action. The candidate is a hosted *AI edit audit*: a GitHub App that stores each check's JSON report (who or which agent, slot, before and after), with per-path allow-list policies across repos. It builds on what `check --json --allow` already emits (h6). I won't build it on spec.

## 6. Differentiators vs prior art
- **Perl formats (perlform)** already have width-by-picture, ellipsis and block fill. But the picture is a separate template. dotslot fields live in the document, stay re-fillable and survive inside comments (a4, c).
- **Cog** rewrites whole generated regions. dotslot fills bounded fields and **proves** nothing else changed (h). None of the prior art I checked has that check.
- **Snippets, Mustache and Python format strings** are consumed at expansion. dotslot slots persist, so the next agent can re-fill them.
- **GitHub issue forms** are YAML and web UI. dotslot is plain text that works in any file and any editor.
- **Width is a contract:** columns and wraps are known before filling (g1). Agents can't push the layout around unless a slot opts in with `+`.

## 7. Roadmap
| version | scope | exit criteria |
|---|---|---|
| **v0.2** (1 week) | Done in the prototype: `_` padding, free unnamed slots, escapes, comment-only default, `new`, `repad`, fill-safe `check`, the Markdown warning. Remaining: package as `dotslot` on PyPI (not yet uploaded), README, `--ignore-whitespace`, a clearer hint for h5 | 42 tests green; `experiments/run_v02.sh` reproduces v02, h and i; every v0.1 "fails" row is either fixed or listed as open in §2 |
| **v0.3** (MCP + Action) | Harden the MCP server (schema validation, dry-run diffs, `--allow` per call); Action released with a JSON summary; pre-commit published; Claude Code, Cursor and aider kits documented | All of h1–h9 pass in CI on a sample repo; one real agent session each in Claude Code, Cursor and aider fills a template with zero violations, or the violation is caught and fixed by the agent; the Action runs in under 10 s on a 100-file PR |
| **v1.0** | Frozen spec with a conformance suite; npm CLI; VS Code extension; tree-sitter comment detection; migration tool from v0.1 `=` syntax | Python and npm pass the same fixtures; no open "fails" items; 3 external repos using the Action; the spec has had one outside review |

## 8. Launch
- **Where to post:**
  - Show HN ("dotslot: let AI fill the blanks and prove it touched nothing else")
  - r/programming and r/LocalLLaMA
  - the MCP servers list (modelcontextprotocol GitHub)
  - Claude Code and Cursor community forums
  - the aider Discord
  - a short X thread with the GIF
- **Demo GIF script (25 s):**
  1. `release.md` with `` `<./owner:____>` ``, a notes block and a legal footer.
  2. The agent fills it through MCP, then `dotslot check` prints `fill-safe (3 slot(s) changed)`.
  3. The agent "helpfully" edits the footer; the hook prints `VIOLATION: text outside slots changed`, and the agent reverts.
  4. End card: `pip install dotslot`.
- **README first screen:**
  ```
  dotslot: let agents fill the blanks, and prove they touched nothing else.

  Owner: `<./owner:____________>`   Status: `<./status~:____________>`

  $ dotslot fill release.md --set owner=Adam --set status="ready for tag" -i
  $ dotslot check release.md --git-base HEAD
  release.md: fill-safe (2 slot(s) changed)

  CLI · pre-commit · GitHub Action · MCP server (Claude Code, Cursor, aider)
  ```

## 9. Risks and out of scope
- **Risks:**
  - The syntax looks odd at first. Mitigation: `dotslot new` and the VS Code highlighting.
  - Agents hand-edit slots anyway (h1, h3). Mitigation: MCP fill first, then the hook, then `repad`.
  - Formatters move columns (c). Mitigation: run dotslot last in pre-commit.
  - The comment finder is a heuristic until tree-sitter lands.
  - Rendered Markdown needs backticks (i).
  - Someone may ship a similar "fill-only" mode inside an agent product. Mitigation: dotslot stays a portable, editor-neutral spec.
- **Out of scope:**
  - general templating (loops, conditionals)
  - proportional-font layout
  - signing or attestation of edits (the audit layer, if any, is v1.x)
  - binary formats
  - enforcing anything at the OS level

  dotslot is a check, not a sandbox.

## 10. Names to reserve (checked live 10 Oct 2026, 03:25 AWST)
| where | `dotslot` |
|---|---|
| npm `dotslot` / scope `@dotslot` | **free** (404; npm search returns nothing) |
| PyPI `dotslot` | **free** (404) |
| GitHub `ao3575911/dotslot` | **free** (404; `ao3575911` exists) |
| GitHub user `dotslot` | **taken**: user `Dotslot`, created 2022-11-01, 0 public repos |
| crates.io / Open VSX `dotslot` | free (404) |
| domains | **dotslot.dev available** (GoDaddy check); dotslot.com and dotslot.io taken |

Reserve npm `dotslot` and `@dotslot`, PyPI `dotslot`, the repo `ao3575911/dotslot`, the VS Code publisher `dotslot`, and dotslot.dev. I haven't reserved or published anything yet.

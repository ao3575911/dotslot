# dotslot SPEC (v0.2): `<./____>` fixed-width slots

*§1–6 define the v0.1 base form; the section "v0.2 changes" at the end amends it and wins on any conflict. The v0.2 tool is `dotslot` (`bin/slot` below is the v0.1 reference, kept for the experiment reproductions).*

A slot is a fill-in field written inline in plain text. Its width is fixed by how it is typed, so a line's layout is decided before the slot is filled. Filling rewrites the text between `<./` and `>` and keeps the closing `>` in the same column, and a filled slot can be re-filled or cleared.

## 1. Lexical form
```
slot      = "<./" interior ">"            ; on one line; interior has no < > tab newline
interior  = empty | named | filled | cont
empty     = " "+                          ; <./      >
named     = IDENT [policy] " "*           ; <./status   >
filled    = [IDENT] [policy] "=" value " "*   ; <./status=done >   <./=42  >
cont      = "|" value? " "*               ; <./|more text   >   (block continuation)
policy    = "!" | "~" | "+"               ; error | ellipsis | grow
IDENT     = [A-Za-z_][A-Za-z0-9_-]*       ; no dots, so `<./input.txt >` is not a slot
```
- **Width W** is the display width of the interior, i.e. everything between `<./` and `>`, the name included. An empty slot's interior is ASCII, so W is its character count. Once a slot is filled, W is the cell count, so CJK and emoji values keep `>` in its column. Cells follow wcwidth ≥ 0.9 grapheme semantics, the model from experiment (g).
- **Capacity** (cells available for a value):
  - unnamed: W − 1 (the `=`)
  - named: W − len(name) − len(policy) − 1
  - continuation: W − 1 (the `|`)
- Trailing spaces are padding, so a value cannot end with a space. Inside an interior, a value may contain `=` and `|`. It may not contain `<`, `>`, tab or newline (`--escape` maps `<` `>` to `‹` `›`).
- Text that looks like a slot but has an invalid interior (`<./input.txt >`, a tab inside) is a **warning and ignored**. A `<./` with no `>` on the same line, or `<./>` (zero width), is an **error**.

## 2. Comment-embedded form
In code files (selected by extension, `--mode auto`, the default), a slot counts only when a comment marker for that language appears earlier on the same line:

| marker | extensions |
|---|---|
| `#` | py sh bash zsh yaml yml toml rb pl r mk cfg conf |
| `//` or `/*` | js ts tsx jsx c h cc cpp go rs java kt swift cs css |
| `--` | sql lua hs elm |
| `;` | ini el lisp clj scm asm |
| `<!--` | html htm xml svg vue |

Slots in a code position are reported and ignored. `--mode prose` accepts every slot; `--mode code` uses all markers on unknown extensions. The comment test is a line-local heuristic: a `#` inside a string counts as a comment (known false positive, exp. c).

## 3. Block slots
A block is a **named** slot (empty or filled) followed by one or more `<./|…>` lines in the same display column with the same width:
```
Notes: <./notes                       >
       <./|                           >
```
- The value is word-wrapped across the lines. The first line holds W − len(name) − 1 cells and each continuation W − 1.
- A word longer than a line is split hard.
- A continuation whose column or width does not match its head is an error. So is an orphan continuation with no head.
- The block's value is the line values joined by single spaces.

## 4. Overflow policies
Policy precedence: the marker on the slot, then `--overflow`, then `error`.

| policy | inline slot | block slot |
|---|---|---|
| `error` `!` | refuse; exit 2. Fill is atomic per file | refuse when words are left over |
| `ellipsis` `~` | cut to cap−1 cells, then add `…` | the last line ends in `…` |
| `truncate` (CLI only) | cut to cap cells | drop the overflow |
| `grow` `+` | interior expands and `>` moves right (the line width now depends on the value) | append `<./|…>` lines, copying the comment prefix and suffix (`# `, `<!-- … -->`) |

Wide glyphs are never split. A 2-cell glyph that does not fit leaves one padding cell.

## 5. Addressing and fill
- `--set name=value` fills every slot with that name. `--set @N=value` fills the N-th slot in scan order (continuations are not counted).
- `--clear name|@N` restores the empty form at the same width.
- `--json-values file.json` reads values from a file.
- Filling an unknown name is an error.
- Filling is idempotent: filling twice with the same value gives the same text as filling once.

## 6. Tool
```
bin/slot scan  FILE... [--json] [--mode auto|prose|code]
bin/slot fill  FILE... --set k=v ... [--overflow P] [--escape] [--clear k] [-i]
bin/slot check FILE... [--require a,b] [--require-filled] [--fit N] [--strict]
bin/slot fit   FILE... [--set k=v] [--targets 80,100,120] [--tab 8] [--preview] [--fail-at N]
```
- `fit` reuses slotfit's model: wcwidth cells, tabs measured from the absolute column, ANSI = 0.
- `fit` gives one of four statuses at each target:
  - `over`: the slot's `>` is past the target.
  - `pushes`: the slot fits but the rest of the line goes past the target.
  - `maybe`: only per-codepoint terminals cross the target.
  - `ok`: fits.
- A line is `static` unless one of its slots has the `+` policy.
- `--preview` shows where word wrap breaks the line.
- Exit codes: 0 ok, 1 lint failures, 2 fill refused.

---
# v0.2 changes (implemented in `dotslot/`; v0.1 kept in `slot/`)
- **Padding:** the padding is `_` (written by default) or space (still read). A slot keeps its own pad character when it is filled.
- **Headers:**
  - Unnamed slots have no header, so their capacity is W. `<./__________>` holds 10 cells.
  - Named slots use `name:` (`<./status:____>`). Policies go before the colon (`status~:`) or stand alone (`~:`).
  - Continuation lines stay `|`.
- **Escapes in values:** `\\ \< \> \_ \: \|`. The tool writes them; humans rarely need to.
  - `\:` is needed only when an unnamed value starts like `word:`.
  - `\_` is needed only for a trailing `_`.
  - Width counts the escaped form, because that is what sits in the file.
- **Default mode:** bare slots count only in prose files (`.md .markdown .txt .text .rst .adoc .org .slot` and stdin). Every other file is comment-only, and unknown extensions accept `# // /* -- ; <!--`. Comment markers inside `'…' "…" `…`` strings are skipped. `--mode prose|comments` overrides this.
- **Errors:** a header that leaves less than 1 cell is an error, unless the policy is `+`.
- **Ellipsis:** cuts at a word boundary when that keeps at least ⅔ of the capacity.
- **New commands:**
  - `dotslot new` generates well-formed slots and blocks.
  - `dotslot repad --base` restores widths that a hand or agent edit lost.
  - `dotslot check --base FILE | --git-base REV [--allow a,b] [--json]` is the fill-safe proof. It passes only when:
    - text outside slots is byte-identical (lines added by `+` blocks are tolerated)
    - slot count, headers and widths are unchanged (except for `+` slots)
    - changed slots are within `--allow`
  - `fill --allow` refuses to fill other slots.
- **MCP:** `python -m dotslot.mcp --root DIR` runs a stdio JSON-RPC MCP server with three tools:
  - `dotslot_scan`
  - `dotslot_fill`, which verifies the result before it writes
  - `dotslot_check`

  Paths are confined to the server root.

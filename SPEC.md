# dotslot specification, v1.0-rc1

Status: **release candidate**. Frozen for outside review; changes before 1.0 only fix errors found in review.
The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.
The fixtures in `conformance/fixtures/` are normative: where this text and a fixture disagree, report it as a spec bug.
The historical v0.1/v0.2 text is in `docs/SPEC-v0.2.md`; the `=` header syntax of v0.1 is not part of this spec
(see `dotslot migrate`).

## 1. Lexical form
```
slot      = "<./" interior ">"                  ; one line
interior  = { "\" any | char - ("<" | ">" | "\" | newline) }
header    = IDENT [policy] ":" | policy ":"
IDENT     = [A-Za-z_][A-Za-z0-9_-]*
policy    = "!" | "~" | "+"                     ; error | ellipsis | grow
pad       = "_" | " "
```
1. A slot MUST be recognised as the shortest match of `<./`, an interior, and `>` on one line. A `\` escapes the next
   character.
2. The **padding** is the longest trailing run of unescaped `_` or space. The remainder is the **body**.
3. If the body starts with `|`, the slot is a **continuation**; the rest of the body is its value.
4. Otherwise, if the body starts with a `header`, the slot is **named** (when IDENT is present) or an **unnamed slot
   with a policy**. The rest of the body is the value.
5. Otherwise the whole body is the value of an **unnamed** slot.
6. A slot is **empty** when its value is empty, else **filled**.
7. An interior containing a tab, or whose body and padding are both empty, is **invalid**: implementations MUST
   report a warning and ignore it.
8. `<./>` (zero width) and a `<./` with no closing `>` on the line MUST be reported as errors.
9. Escapes in values are `\\ \< \> \_ \: \|`. Implementations MUST unescape when reporting a value and MUST escape
   when writing one: `\ < >` always; a leading `|` and a leading `IDENT:`-like prefix in unnamed slots; a trailing pad
   character.

## 2. Width and capacity
1. **Width W** is the display width in terminal cells of the interior as it appears in the file (escaped form).
   Cells MUST follow Unicode grapheme clusters with East Asian Wide/Fullwidth and emoji presentation = 2 cells,
   combining and zero-width characters = 0, and other printable characters = 1 (the `wcwidth` model).
2. **Capacity** = W − cells(header), where a continuation's header is `|`. A non-`+` slot with capacity < 1 MUST be
   reported as an error.
3. When a slot is written, its interior MUST keep width W (except `+`), padded with the slot's own pad character.
4. The same name used with different widths SHOULD produce a warning.

## 3. Blocks
1. A named slot followed on the next lines by continuations in the same display column forms a **block**.
2. Each continuation MUST have the head's width; a mismatch is an error.
3. A continuation not owned by a block MUST be reported as an error.
4. A block's value is the non-empty line values joined by single spaces. Fill MUST word-wrap greedily across lines;
   a word longer than a line MAY be split hard.

## 4. Where slots count (modes)
1. `prose` mode: every slot counts. It is the default for `.md .markdown .txt .text .rst .adoc .org .slot` and stdin.
2. `comments` mode (every other file): a slot counts only when a comment marker for the language starts earlier on
   the same line. Markers by extension are listed in the reference implementation (`dotslot/core.py`); unknown
   extensions MUST accept `# // /* -- ; <!--`.
3. Markers inside `'…'`, `"…"` and `` `…` `` strings on the same line MUST NOT start a comment. Implementations MAY
   use a parser (e.g. tree-sitter) for more precise detection, but MUST give the same result as the fixtures on
   single-line cases.
4. A slot outside a comment in comments mode MUST be reported as a warning and ignored.
5. In Markdown files, a slot containing `_` outside a code span SHOULD produce a warning.

## 5. Addressing
1. Top-level slots (heads and inline slots, not continuations) are numbered from 1 in scan order; `@N` addresses the
   N-th. A name addresses every slot with that name.
2. Filling an unknown name or index MUST be an error.
3. With an allow list, filling a slot not in it MUST be an error.

## 6. Fill
1. Fill MUST refuse a file with any scan error.
2. Fill MUST only change slot interiors, except that a `+` block MAY insert continuation lines after its last line,
   copying the comment prefix and a closing comment suffix.
3. Overflow policy precedence: the slot's own marker, then the caller's default, then `error`.
   - `error`: refuse.
   - `ellipsis`: cut at a grapheme boundary so the escaped value plus `…` fits; prefer a word boundary when it keeps
     at least ⅔ of the capacity.
   - `grow`: the interior grows (inline) or lines are added (block).
4. Values for inline slots MUST NOT contain a tab or newline. Trailing spaces are dropped.
5. Fill MUST be idempotent.

## 7. Check (fill-safe proof)
`check(base, new, allow?, ignore_whitespace?)` passes only when all hold:
1. `new` has no scan errors.
2. With every slot interior removed, the text is identical, except continuation lines added by a `+` block.
   With `ignore_whitespace`, trailing whitespace on each line is ignored.
3. Slot count, headers (name and policy), widths and block heights are unchanged, except for `+` slots.
4. Every slot whose value changed is in `allow`, when given.

The result MUST list the changed slots by name, or `@N` for unnamed slots.

## 8. Conformance
An implementation conforms when it passes every fixture in `conformance/fixtures/`. Each fixture is JSON:
`{id, description, op: scan|fill|check, path, mode?, input, base?, values?, allow?, ignore_whitespace?, expect}`.
- `scan` expects `slots` (index, name, kind, policy, 1-based line, 0-based cell col, width, capacity, lines, value)
  and `issues` (severity `E`/`W`, line; messages are not normative).
- `fill` expects `output` (exact text) or `error: true`.
- `check` expects `ok` and `changed`.

Runners: `python conformance/run.py`.

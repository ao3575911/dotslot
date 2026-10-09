---
name: dotslot
description: Fill <./…> slots in fill-only files without touching anything else. Use when a file contains `<./` slots or the user asks to "fill in" a template, form, checklist or record.
---
1. Run `dotslot scan FILE` (or the `dotslot_scan` MCP tool) to list slots, widths and capacity.
2. Fill with `dotslot fill FILE --set name=value -i` (or `dotslot_fill`). Never hand-edit a slot: the tool keeps the width, pads with `_` and escapes `<` `>` `\` for you.
3. If a value is too long, shorten it or ask; only use `--overflow ellipsis` if the user agrees.
4. Finish with `dotslot check FILE --git-base HEAD`. It must say `fill-safe`.

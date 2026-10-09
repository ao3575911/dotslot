# Conventions: dotslot fill-only files
- A file with `<./…>` slots is fill-only: edit slot interiors and nothing else.
- Keep each slot's width: pad values with `_` up to the closing `>`; escape `<` `>` `\` as `\<` `\>` `\\`.
- Prefer running `dotslot fill FILE --set name=value -i` over hand edits.

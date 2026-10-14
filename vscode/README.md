# dotslot for VS Code

Works with [dotslot](https://github.com/ao3575911/dotslot) fixed-width slots.

- **Highlighting:** empty and filled slots are highlighted.
- **Width hints:** each slot shows `used/capacity` cells (and block height) as an inlay hint.
- **Diagnostics:** scanner errors and warnings (unterminated or zero-width slots, block width mismatches, slots
  outside comments, Markdown `_` emphasis), plus an optional line-length warning (`dotslot.maxLineLength`).
- **Fill slot** (command palette or editor context menu): fills the slot under the cursor and keeps its width.
  The input box validates against the overflow policy as you type.

Settings: `dotslot.enable`, `dotslot.inlayHints`, `dotslot.mode`, `dotslot.overflow`, `dotslot.maxLineLength`.

The scanner is the same TypeScript implementation as the npm CLI and passes the shared conformance fixtures.

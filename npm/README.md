# dotslot (npm)

TypeScript port of the [dotslot](https://github.com/ao3575911/dotslot) CLI: fixed-width `<./____>` slots that agents
fill, plus a check that proves nothing outside the slots changed. No runtime dependencies. It passes the same
conformance fixtures as the Python implementation (`conformance/fixtures`), except the tree-sitter ones.

```sh
npx dotslot scan FILE... [--json]
npx dotslot fill FILE --set owner=alice -i
npx dotslot check FILE --git-base origin/main --allow owner
```

`migrate`, `fit`, `new`, `repad` and the MCP server are Python-only: `pip install dotslot`.

Library: `import { scanText, fillText, verify } from 'dotslot'`.

Exit codes: `0` ok, `1` violation, `2` usage or input error. Install: `npm i -g dotslot` or run with `npx dotslot`.

# Security policy

## Supported versions
Only the latest release receives security fixes.

## Reporting a vulnerability
Report privately through GitHub: **Security → Report a vulnerability** on
https://github.com/ao3575911/dotslot/security/advisories/new. Do not open a public issue.

Expect an acknowledgement within 7 days. Fixes ship as a patch release with a GitHub Security Advisory.

## Scope
In scope: the `dotslot` CLI, the `dotslot-mcp` server (path escapes, writes outside slots, writes outside `--root`),
the GitHub Action and the pre-commit hooks.

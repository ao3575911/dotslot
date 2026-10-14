# Contributing

## Setup

Python 3.10+ and Node 18+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
cd npm && npm ci && cd ..
```

Optional tree-sitter backend: `pip install -e ".[treesitter,test]"`.

## Tests

```bash
pytest -q tests
python conformance/run.py          # shared fixtures in conformance/fixtures/
cd npm && npm test                 # build + conformance + CLI
cd vscode && npm test              # if you touch the extension
```

CI runs the same suite. Shared fixtures in `conformance/` must stay identical across Python and npm.

## Pull requests

- One change per PR.
- CI green before merge.
- User-facing changes: add a `CHANGELOG.md` entry under `Unreleased`.
- Version bumps follow SemVer; see [RELEASING.md](RELEASING.md).
- Keep diffs small. Match the tone of existing docs: short, plain, no hype.

## Spec

Behaviour is defined in [SPEC.md](SPEC.md). Conformance fixtures are the source of truth for fill/check/scan.

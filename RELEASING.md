# Releasing

1. Merge a PR that bumps `version` in `pyproject.toml` and `__version__` in `dotslot/__init__.py`, and moves the `CHANGELOG.md` `Unreleased` items under the new version.
2. Run the `release` workflow on `main`: `gh workflow run release -R ao3575911/dotslot` (or use the Actions tab).
3. The workflow tests, then **creates and GPG-signs the tag `vX.Y.Z` in CI** and pushes it. It builds the sdist and wheel, writes `SHA256SUMS`, attests build provenance and creates the GitHub Release.

Don't tag by hand. Nobody holds the signing key locally. PyPI publishing is manual for now.

## Signing key

- The private key exists only in the Actions secret `RELEASE_GPG_KEY`.
- The public key is `.github/release-signing-key.asc`: ed25519, fingerprint `B8A12BD87E04C08FA15C45FE54A91F394F2B32B0`, uid `<280728713+ao3575911@users.noreply.github.com>`.
- For GitHub to show **Verified** on tags, an owner of the ao3575911 account adds this public key under *Settings → SSH and GPG keys → New GPG key*, or: `gh auth refresh -s admin:gpg_key && gh gpg-key add .github/release-signing-key.asc`.

## Verify a release

```bash
sha256sum -c SHA256SUMS                                             # files match
gh attestation verify dotslot-X.Y.Z-py3-none-any.whl -R ao3575911/dotslot   # built by this repo's release workflow
gpg --import .github/release-signing-key.asc && git tag -v vX.Y.Z  # tag signature
```

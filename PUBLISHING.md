# Publishing okfgen to PyPI

Releases are automated via [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
using **PyPI Trusted Publishing** (OIDC) — no API tokens are stored in the repo.

## One-time setup

1. **Reserve the name / create the project.** If `okfgen` is unclaimed, the
   trusted-publisher flow can create it on first publish. Confirm availability at
   https://pypi.org/project/okfgen/ (or pick another name in `pyproject.toml`).

2. **Add a Trusted Publisher on PyPI.**
   PyPI → your project (or *Publishing* → *Add a pending publisher*) → GitHub, with:
   - **Owner:** `bushans`
   - **Repository:** `okfgen`
   - **Workflow name:** `publish.yml`
   - **Environment:** `pypi`

3. **Create the `pypi` environment** in GitHub:
   repo → **Settings → Environments → New environment** → name it `pypi`
   (optionally add required reviewers to gate releases).

No secrets to paste — OIDC handles auth at publish time.

## Cut a release

```bash
# 1. Bump the version in pyproject.toml (e.g. 0.1.0 -> 0.1.1)
# 2. Commit, tag, push
git commit -am "Release v0.1.1"
git tag v0.1.1 && git push --tags

# 3. Publish a GitHub Release for that tag (UI or gh):
gh release create v0.1.1 --generate-notes
```

Publishing the Release triggers the workflow: it builds the sdist + wheel, runs
`twine check`, and uploads to PyPI. You can also run it manually from the
Actions tab (**workflow_dispatch**).

## Build & verify locally

```bash
pip install -e '.[dev]'
python -m build          # -> dist/*.whl, dist/*.tar.gz
python -m twine check dist/*
```

## After the first release

The quickstart simplifies from git installs to:

```bash
uvx okfgen generate .        # zero-install
pip install okfgen           # or with extras: pip install "okfgen[all]"
```

Update the README's Install/Quickstart sections accordingly.

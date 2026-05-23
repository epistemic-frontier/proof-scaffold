# Release Policy

ProofScaffold releases are tag-driven. A release is published to PyPI by pushing
a version tag that matches `pyproject.toml`.

## Version Policy

- Use PEP 440 versions in `pyproject.toml`.
- Release tags must be exactly `v<version>`.
  - Example: `pyproject.toml` version `0.0.6` must be tagged `v0.0.6`.
- Do not reuse tags or PyPI versions. If a publish job fails after uploading
  files, bump to the next version before retrying.

## Release Checklist

1. Make sure `main` is clean and up to date.
2. Bump `project.version` in `pyproject.toml`.
3. Update `uv.lock` if the version appears there.
4. Run:

   ```bash
   uv run --frozen ruff check .
   uv run --frozen mypy .
   uv run --frozen python -m pytest
   uv build
   ```

5. Commit the version bump.
6. Tag and push:

   ```bash
   git tag v0.0.6
   git push origin main
   git push origin v0.0.6
   ```

The `Release` GitHub Actions workflow validates the tag, runs the release gate
on supported Python versions, builds the wheel and sdist, and publishes to PyPI.

## One-Time PyPI Trusted Publishing Setup

The release workflow uses PyPI Trusted Publishing, so it does not need a PyPI
API token or GitHub secret. Configure this once on PyPI:

- PyPI project: `proof-scaffold`
- Publisher: GitHub Actions
- Owner: `epistemic-frontier`
- Repository: `proof-scaffold`
- Workflow name: `release.yml`
- Environment name: `pypi`

PyPI requires the workflow job to request `id-token: write`; the release
workflow already does this for the publish job only.

## Repository Management Rules

- `main` is the release branch.
- Feature and fix work should land through reviewed PRs unless explicitly
  bypassed for urgent maintenance.
- CI must pass before tagging.
- Build artifacts under `dist/`, `build/`, and `target/` are transient and must
  not be committed.
- Release automation is the only supported PyPI publishing path.

## Recommended GitHub Settings

Configure `main` as a protected release branch:

- require pull requests before merging
- require the `CI` workflow to pass before merging
- require branches to be up to date before merging
- disallow force pushes and branch deletion
- restrict direct pushes to maintainers only

The GitHub CLI needs a valid login with repository administration permission to
apply these settings. Re-authenticate with:

```bash
gh auth login -h github.com
```

Select GitHub.com, HTTPS or SSH according to the local checkout, authenticate in
the browser, and grant `repo` scope when prompted. After that, branch protection
can be applied through the repository settings UI or GitHub's ruleset API.

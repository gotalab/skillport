# Versioning & Release Playbook (Template)
Reusable guidance for projects using semantic-release + GitHub Actions.

## Scope
- Applies to any repo following SemVer and Conventional Commits.
- Assumes GitHub Actions is available.

## Branch & Tag Strategy
- Work on `main` (or `trunk`); release via git tags `vX.Y.Z`.
- Optional: short-lived `feature/*`, `fix/*`, `hotfix/vX.Y.Z`.
- If LTS needed: create `release/vX.Y` and add it to `.releaserc` branches.

## Directory Layout for Docs
- Working SSOT: `docs/latest/`
- Release snapshots: `docs/releases/vX.Y.Z/`
- External links should prefer `docs/latest/` unless a fixed version is required.

## Semantic Versioning Rules
- **MAJOR**: breaking changes (API/tool schema/behavior).
- **MINOR**: backward-compatible feature additions.
- **PATCH**: bug fixes or non-breaking improvements.

## Required Files
- `.releaserc` (semantic-release config)
- `.github/workflows/release.yml` (CI workflow)
- `CHANGELOG.md` (Keep a Changelog format recommended)

## Minimal .releaserc
```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    ["@semantic-release/changelog", { "changelogFile": "CHANGELOG.md" }],
    ["@semantic-release/git", { "assets": ["CHANGELOG.md"] }],
    "@semantic-release/github"
  ]
}
```

## Minimal release workflow (tag-triggered)
```yaml
name: release
on:
  push:
    tags: ['v*.*.*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - name: Install semantic-release deps
        run: npm install --no-save semantic-release @semantic-release/{changelog,git,github,commit-analyzer,release-notes-generator}
      - name: Semantic Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx semantic-release
      - name: Snapshot docs
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          mkdir -p docs/releases/v${VERSION}
          cp -r docs/latest/* docs/releases/v${VERSION}/
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add docs/releases CHANGELOG.md
          git commit -m "chore: snapshot docs v${VERSION}" || true
          git push origin HEAD:${GITHUB_REF_NAME} || true
```

## Secrets / Tokens
- Default: `GITHUB_TOKEN`.
- If branch protection blocks pushes, add PAT as `SEMREL_TOKEN` with `Contents:write`, `Metadata:read`, `Workflows:write`, and set `GITHUB_TOKEN: ${{ secrets.SEMREL_TOKEN }}` in the workflow.

## Release Checklist (human)
1) Update `docs/latest` (PRD/PLAN/guides) and ensure CHANGELOG entries are ready.
2) Ensure tests/verify pass.
3) Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4) Confirm GitHub Release, CHANGELOG, and `docs/releases/vX.Y.Z` snapshot.

## Optional Enhancements
- Add behavioral regression tests (golden traces) before semantic-release step.
- Add `@semantic-release/exec` for custom packaging/publishing steps.
- Maintain `docs/releases/stable` symlink/copy to the latest non-breaking release.

## Invariants
- Never edit `docs/releases/*`; edit `docs/latest/*` only.
- Keep defaults (e.g., search limits, thresholds) consistent across code, PRD, PLAN, guides.
- Logs to stderr; stdout reserved for protocol output (if applicable).

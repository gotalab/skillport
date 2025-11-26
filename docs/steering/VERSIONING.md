# Versioning & Release Strategy

Audience: all engineers (staff+). GitHub-first, semver-aligned, automation-friendly.

Uses [Release Please](https://github.com/googleapis/release-please) for automated release management (same pattern as OpenAI/Anthropic SDKs).

## Directory layout
- **Working SSOT:** `docs/latest/` (always edit here during development).
- **Implementation plans:** `docs/latest/tasks/<task-id>.md` (大粒/並列/リスク高のみ)。小粒はPLAN行で完結。
- **Released snapshots:** `docs/releases/vX.Y.Z/` (immutable; copy of latest at release). `specs/wip/**` と `tasks/AGENTS.md` はコピーしない。
- External references: use `docs/latest/` unless pinning to a specific version.

## Semantic Versioning rules
- **MAJOR:** Breaking change (tool schema/behavior). Add "Breaking Changes" to PRD for that release.
- **MINOR:** Backward-compatible feature additions (new optional args/fields).
- **PATCH:** Bug fixes or non-functional improvements.

## Release flow (Release Please)

### Commit prefixes → Version bump
| Prefix | Effect | Example |
|--------|--------|---------|
| `feat:` | Minor (0.X.0) | `feat: add search filter` |
| `fix:` | Patch (0.0.X) | `fix: null pointer error` |
| `feat!:` or `BREAKING CHANGE:` | Major (X.0.0) | `feat!: change API schema` |
| `chore:`, `docs:`, `ci:` | No release | `docs: update README` |

### Steps
1. **Develop**: Commit with Conventional Commits to main
2. **Auto PR**: Release Please creates/updates "Release PR" automatically
3. **Review**: Check CHANGELOG diff and version bump in the PR
4. **Release**: Merge Release PR → tag created → docs snapshot created

### Override version manually
```bash
# Option 1: Edit manifest before merging Release PR
# .release-please-manifest.json
{
  ".": "1.0.0"
}

# Option 2: Commit footer
git commit -m "feat: major release

Release-As: 1.0.0"
```

## Configuration files
- `.release-please-manifest.json` - Current version tracking
- `release-please-config.json` - Release Please settings

## CI Workflows
| File | Trigger | Purpose |
|------|---------|---------|
| `ci.yml` | PR, push to main | Quality gate (lint, test, verify) |
| `release.yml` | push to main | Create Release PR, snapshot docs on release |

## Invariants
- Edit only `docs/latest/`; never change `docs/releases/*`.
- Keep defaults in code, PRD, PLAN, and guides aligned.
- MCP logging rule holds across versions: stdout = JSON-RPC only; logs to stderr.
- GitHub Actions uses stable `actions/checkout@v5` and `astral-sh/setup-uv@v5`.

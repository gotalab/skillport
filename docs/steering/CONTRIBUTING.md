# Contributing Guide

Branch-to-PR workflow for SkillHub development.

## Workflow Overview

```
1. Branch  →  2. Plan  →  3. Implement  →  4. Verify  →  5. Commit  →  6. Push  →  7. PR
```

## 1. Create Branch

```bash
git checkout main
git pull origin main
git checkout -b <branch-name>
```

**Branch naming:**
- `feat/short-description` - New features
- `fix/short-description` - Bug fixes
- `docs/short-description` - Documentation only
- `refactor/short-description` - Code refactoring

Keep names short and descriptive (e.g., `feat/add-command`, `fix/lint-errors`).

## 2. Plan

For non-trivial changes:
1. Discuss approach (if needed)
2. Update `docs/latest/PLAN.md` with task items
3. Break down into small, reviewable commits

For simple fixes, proceed directly to implementation.

## 3. Implement

- Follow existing code patterns
- Keep changes focused (one concern per PR)
- Update documentation if behavior changes

## 4. Verify (CI Checks)

Run all checks locally before committing:

```bash
# Lint (required)
uv run ruff check .

# Tests (required)
uv run pytest -q

# Server verification (required for db/search/config changes)
SKILLS_DIR=.agent/skills uv run verify_server.py
```

**Fix lint errors automatically:**
```bash
uv run ruff check . --fix
```

## 5. Commit

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | Minor (0.X.0) |
| `fix` | Bug fix | Patch (0.0.X) |
| `docs` | Documentation only | None |
| `refactor` | Code change (no feature/fix) | None |
| `test` | Adding/updating tests | None |
| `chore` | Maintenance tasks | None |
| `ci` | CI configuration | None |

**Breaking changes:** Add `!` after type or `BREAKING CHANGE:` in footer.
```
feat!: change default skills directory
```

### Commit Message Examples

```bash
# Simple fix
git commit -m "fix: remove unused import"

# Feature with body
git commit -m "$(cat <<'EOF'
feat: add `skillhub add` command

- Add hello-world and template built-in skills
- Auto-create ~/.skillhub/skills/ directory
EOF
)"

# With co-author (for AI-assisted code)
git commit -m "$(cat <<'EOF'
feat: add search filtering

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Staging Changes

```bash
# Stage specific files
git add <file1> <file2>

# Stage all changes
git add -A

# Review staged changes
git diff --staged
```

## 6. Push

```bash
# First push (set upstream)
git push -u origin <branch-name>

# Subsequent pushes
git push
```

## 7. Create PR

### Using GitHub CLI (recommended)

```bash
gh pr create --title "<type>: <description>" --body "$(cat <<'EOF'
## Summary
- Bullet points of changes

## Test plan
- [ ] Test case 1
- [ ] Test case 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### PR Title
Follow the same Conventional Commits format as commit messages.

### PR Body Template

```markdown
## Summary
- What changed and why (1-3 bullets)

## Test plan
- [ ] How to verify the changes work

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Quick Reference

```bash
# Full workflow example
git checkout -b feat/add-command
# ... make changes ...
uv run ruff check . --fix
uv run pytest -q
SKILLS_DIR=.agent/skills uv run verify_server.py
git add -A
git commit -m "feat: add skillhub add command"
git push -u origin feat/add-command
gh pr create --title "feat: add skillhub add command" --body "..."
```

## CI Pipeline

PRs trigger the following checks (must all pass):
1. **Lint**: `uv run ruff check .`
2. **Test**: `uv run pytest -q`
3. **Verify**: `uv run verify_server.py`

See `.github/workflows/ci.yml` for details.

## After PR Merge

Release Please automatically:
1. Creates/updates a Release PR based on commit types
2. Bumps version according to Conventional Commits
3. Generates CHANGELOG

See [RUNBOOK.md](./RUNBOOK.md#release-release-please) for release details.

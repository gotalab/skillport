# Runbook

Short, repeatable steps for local work and verification.

## Setup
- Install deps: `uv sync`
- Default env: `EMBEDDING_PROVIDER=none`, `SKILLS_DIR=.agent/skills`
- DB default path: `~/.skillhub/skills.lancedb` (override with `SKILLHUB_DB_PATH`)

## Run server (manual)
```
SKILLS_DIR=.agent/skills EMBEDDING_PROVIDER=none uv run skillhub-mcp  # or: uv run skillhub
```

### CLI commands (no server startup)

```bash
# List all skills
skillhub-mcp --list
# Output shows ★ for alwaysApply skills

# Validate all skills against Agent Skills spec
skillhub-mcp --lint
# Exit code: 0 (pass), 1 (issues found)

# Validate specific skill
skillhub-mcp --lint hello-world
```

**Validation checks:**
- `frontmatter.name`: required, max 64 chars, a-z/0-9/- only, must match directory, no reserved words (anthropic/claude)
- `frontmatter.description`: required, max 1024 chars, no XML tags
- `SKILL.md`: recommended ≤200 lines

### Reindex controls
- 強制リビルド: `uv run skillhub-mcp --reindex`
- 自動判定をスキップ: `uv run skillhub-mcp --skip-auto-reindex` あるいは `SKILLHUB_SKIP_AUTO_REINDEX=1`
- 起動時は `SKILL.md` のハッシュ差分で再インデックス要否を判定し、必要なときだけ実行。状態は `~/.skillhub/index_state.json`（DBと同じ場所）に保存。

### Reindex 後のクライアント反映
- **Cursor / Windsurf**: `Cmd+Q` で完全終了→再起動。ウィンドウリロードだけでは接続が残りやすい。
- **Claude Desktop**: アプリを終了して再起動（メニューから Quit か `Cmd+Q`）。
- **その他 MCP クライアント**: セッションを張り直す（接続を閉じて再度接続）。reindex 後に検索結果/ロード結果が古い場合はセッション再確立を試す。

## Verify (critical after db/search/config changes)
```
uv run verify_server.py
```
- If it fails, read stderr in the tool output (stdout is reserved for JSON-RPC).
- Verify harness lives at repo root for convenience; keep it simple and run directly.

## Minimal dev loop (early stage)
```
uv run ruff check .
uv run pytest -q
uv run verify_server.py
```
Run in this order; skip extras (mypy, coverage) until the surface stabilizes.

## Common env vars
- `SEARCH_LIMIT` (default 10)
- `SEARCH_THRESHOLD` (default 0.2)
- `SKILLHUB_ENABLED_SKILLS` / `SKILLHUB_ENABLED_CATEGORIES` for prefiltering
- `ALLOWED_COMMANDS`, `EXEC_TIMEOUT_SECONDS`, `EXEC_MAX_OUTPUT_BYTES`, `MAX_FILE_BYTES`

## Skill authoring

### PEP 723 inline dependencies (recommended)
Scripts can declare dependencies inline. `uv run` handles installation automatically:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf>=4.0"]
# ///

from pypdf import PdfReader
# ...
```

### Skill directory structure
```
my-skill/
├── SKILL.md              # AI Agent instructions (SSOT)
├── README.md             # Human documentation (optional)
└── scripts/
    └── main.py           # Use PEP 723 for dependencies
```

### Validate before publishing
```bash
skillhub-mcp --lint my-skill
```

## Safety reminders
- Don’t print logs to stdout.
- Preserve path traversal guards and command allowlist.
- When enabling external embeddings, set required API keys and expect fail-fast validation.

## Release (Release Please)

Uses [Release Please](https://github.com/googleapis/release-please) for automated release management (same pattern as OpenAI/Anthropic SDKs).

### How it works
1. **Develop**: Commit with Conventional Commits (`feat:`, `fix:`, etc.) to main
2. **Auto PR**: Release Please creates/updates a "Release PR" automatically
3. **Review**: Check CHANGELOG diff and version bump in the PR
4. **Release**: Merge the Release PR → tag created → docs snapshot created

### Commit prefixes → Version bump
| Prefix | Effect | Example |
|--------|--------|---------|
| `feat:` | Minor (0.X.0) | `feat: add search filter` |
| `fix:` | Patch (0.0.X) | `fix: null pointer error` |
| `feat!:` or `BREAKING CHANGE:` | Major (X.0.0) | `feat!: change API schema` |
| `chore:`, `docs:`, `ci:` | No release | `docs: update README` |

### Override version manually
To set a specific version instead of auto-calculated:
```bash
# Edit .release-please-manifest.json before merging Release PR
{
  ".": "1.0.0"  # Set desired version
}
```
Or add footer to any commit:
```
feat: add feature

Release-As: 1.0.0
```

### Workflows
| File | Trigger | Purpose |
|------|---------|---------|
| `ci.yml` | PR, push | Quality gate (lint, test, verify) |
| `release.yml` | push to main | Create Release PR, snapshot docs |

### Configuration files
- `.release-please-manifest.json` - Current version tracking
- `release-please-config.json` - Release Please settings

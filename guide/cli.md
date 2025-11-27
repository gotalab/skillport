# CLI Reference

SkillPod provides a command-line interface for managing [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) and running the MCP server.

## Overview

```bash
skillpod <command> [options]
```

> **Note**: `skillpod-mcp` is a legacy alias for `skillpod`. Both work identically.

## Commands

### skillpod add

Add skills from various sources.

```bash
skillpod add <source> [options]
```

#### Sources

| Type | Example | Description |
|------|---------|-------------|
| Built-in | `hello-world` | Sample skill bundled with SkillPod |
| Built-in | `template` | Starter template for creating skills |
| Local | `./my-skill/` | Single skill directory |
| Local | `./my-collection/` | Directory containing multiple skills |
| GitHub | `https://github.com/user/repo` | Repository root (auto-detects default branch) |
| GitHub | `https://github.com/user/repo/tree/main/skills` | Specific directory |

> **GitHub URL サポート**:
> - 末尾スラッシュあり/なし両対応
> - ブランチ未指定時はデフォルトブランチを自動検出
> - プライベートリポジトリは `GITHUB_TOKEN` 環境変数が必要

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--force`, `-f` | Overwrite existing skills | `false` |
| `--keep-structure/--no-keep-structure` | Preserve directory structure as namespace | Interactive |
| `--namespace`, `-n` | Custom namespace | source directory name |
| `--name` | Override skill name (single skill only) | from SKILL.md |

#### Interactive Mode

ローカルパスまたは GitHub URL を指定し、`--keep-structure` も `--namespace` も指定しない場合、対話モードでスキルの追加先を選択できます。

```
$ skillpod add ./my-collection/

Found 3 skill(s): skill-a, skill-b, skill-c
Where to add?
  [1] Flat       → skills/skill-a/, skills/skill-b/, ...
  [2] Namespace  → skills/<ns>/skill-a/, ...
  [3] Skip
Choice [1/2/3] (1):
```

| 選択 | 動作 |
|------|------|
| `1` Flat | フラットに追加 (`--no-keep-structure` と同等) |
| `2` Namespace | 名前空間付きで追加。名前空間名の入力を求める |
| `3` Skip | 何もせず終了 |

> **Note**: Built-in スキル (`hello-world`, `template`) は対話モード対象外です。

#### Examples

**Built-in skills:**
```bash
# Add sample skill
skillpod add hello-world

# Add template for creating your own
skillpod add template
```

**Local directory:**
```bash
# Single skill
skillpod add ./my-skill/

# Multiple skills - interactive mode
skillpod add ./my-collection/

# Multiple skills - flat (skip interactive)
skillpod add ./my-collection/ --no-keep-structure
# → skills/skill-a/, skills/skill-b/, skills/skill-c/

# Multiple skills - preserve structure
skillpod add ./my-collection/ --keep-structure
# → skills/my-collection/skill-a/, skills/my-collection/skill-b/

# Multiple skills - custom namespace
skillpod add ./my-collection/ --keep-structure --namespace team-tools
# → skills/team-tools/skill-a/, skills/team-tools/skill-b/
```

**GitHub:**
```bash
# Specific skill from repository
skillpod add https://github.com/user/repo/tree/main/skills/code-review

# All skills from repository
skillpod add https://github.com/user/repo

# Force overwrite existing
skillpod add https://github.com/user/repo --force
```

#### Output

**全て成功:**
```
  ✓ Added 'skill-a'
  ✓ Added 'skill-b'
Added 2 skill(s)
```

**一部スキップ (既存):**
```
  ✓ Added 'skill-c'
  ⊘ Skipped 'skill-a' (exists)
  ⊘ Skipped 'skill-b' (exists)
Added 1, skipped 2 (use --force to overwrite)
```

---

### skillpod list

List installed skills.

```bash
skillpod list [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum number to display | `100` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# List all skills
skillpod list

# Limit results
skillpod list --limit 20

# JSON output for scripting
skillpod list --json
```

#### Output Format

**Default (table view):**
```
┌─────────────────────────────────────────────────────────────┐
│                       Skills (5)                            │
├──────────────────────┬─────────────┬────────────────────────┤
│ ID                   │ Category    │ Description            │
├──────────────────────┼─────────────┼────────────────────────┤
│ hello-world          │ example     │ A simple hello world…  │
│ pdf                  │ document    │ Extract text from PDF  │
│ team/code-review     │ development │ Code review checklist  │
└──────────────────────┴─────────────┴────────────────────────┘
```

**JSON:**
```json
{
  "skills": [
    {
      "id": "hello-world",
      "name": "hello-world",
      "description": "A simple hello world skill",
      "category": "example"
    }
  ],
  "total": 5
}
```

---

### skillpod search

Search for skills.

```bash
skillpod search <query> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum results | `10` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Search by description
skillpod search "PDF text extraction"

# Limit results
skillpod search "code review" --limit 5

# JSON output
skillpod search "testing" --json
```

---

### skillpod show

Show skill details.

```bash
skillpod show <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Show skill details
skillpod show hello-world

# Show namespaced skill
skillpod show team-tools/code-review

# JSON output
skillpod show pdf --json
```

---

### skillpod remove

Remove installed skills.

```bash
skillpod remove <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--force`, `-f` | Skip confirmation | `false` |

#### Examples

```bash
# Remove with confirmation
skillpod remove hello-world
# → Remove 'hello-world'? [y/N]

# Remove without confirmation
skillpod remove hello-world --force

# Remove namespaced skill
skillpod remove team-tools/code-review --force
```

---

### skillpod lint

Validate skill files.

```bash
skillpod lint [skill-id]
```

#### Validation Rules

**Fatal (検証失敗)**

| Rule | Description |
|------|-------------|
| `name` required | frontmatter に name がない |
| `description` required | frontmatter に description がない |
| name = directory | name がディレクトリ名と一致しない |
| name ≤ 64 chars | name が長すぎる |
| name pattern | `a-z`, `0-9`, `-` のみ許可 |
| reserved words | `anthropic-helper`, `claude-tools` は予約済み |

**Warning (警告のみ)**

| Rule | Description |
|------|-------------|
| SKILL.md ≤ 500 lines | ファイルが長すぎる |
| description ≤ 1024 chars | description が長すぎる |
| no XML tags | description に `<tag>` が含まれる |

#### Examples

```bash
# Lint all skills
skillpod lint

# Lint specific skill
skillpod lint hello-world
```

#### Output

**All valid:**
```
✓ All skills pass validation
```

**Issues found:**
```
broken-skill
  - (fatal) frontmatter.name 'wrong-name' doesn't match directory 'broken-skill'
  - (warning) SKILL.md: 600 lines (recommended ≤500)

2 issue(s) found
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All valid (no fatal issues) |
| 1 | Fatal issues found |

---

### skillpod serve

Start the MCP server.

```bash
skillpod serve [options]
```

#### Options

| Option | Description |
|--------|-------------|
| `--reindex` | Force reindex on startup |
| `--skip-auto-reindex` | Skip automatic reindex check |

#### Examples

```bash
# Start server
skillpod serve

# Start with forced reindex
skillpod serve --reindex
```

#### Legacy Mode

```bash
# 以下は同等 (後方互換)
skillpod
skillpod serve
```

> **Note**: `skillpod --reindex` は **サポートしない**。常に `skillpod serve --reindex` を使用すること。

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, not found, validation failed, etc.) |

## Environment Variables

CLI commands respect these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPOD_SKILLS_DIR` | Skills directory | `~/.skillpod/skills` |
| `SKILLPOD_EMBEDDING_PROVIDER` | Embedding provider (`none`, `openai`, `gemini`) | `none` |
| `OPENAI_API_KEY` | OpenAI API key (for vector search) | |
| `GEMINI_API_KEY` | Gemini API key (for vector search) | |
| `GOOGLE_API_KEY` | Alternative to `GEMINI_API_KEY` | |
| `GITHUB_TOKEN` | GitHub authentication for private repos | |

## See Also

- [Configuration Guide](configuration.md) — All options, filtering, search
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way

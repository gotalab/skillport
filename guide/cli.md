# CLI Reference

SkillSouko provides a command-line interface for managing [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) and running the MCP server.

## Overview

```bash
skillsouko <command> [options]
```

> **Note**: `skillsouko-mcp` is a legacy alias for `skillsouko`. Both work identically.

## Commands

### skillsouko add

Add skills from various sources.

```bash
skillsouko add <source> [options]
```

#### Sources

| Type | Example | Description |
|------|---------|-------------|
| Built-in | `hello-world` | Sample skill bundled with SkillSouko |
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
| `--yes`, `-y` | Skip interactive prompts (for CI/automation) | `false` |
| `--keep-structure/--no-keep-structure` | Preserve directory structure as namespace | Interactive |
| `--namespace`, `-n` | Custom namespace | source directory name |
| `--name` | Override skill name (single skill only) | from SKILL.md |

#### Interactive Mode

ローカルパスまたは GitHub URL を指定し、`--keep-structure` も `--namespace` も指定しない場合、対話モードでスキルの追加先を選択できます。

```
$ skillsouko add ./my-collection/

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
skillsouko add hello-world

# Add template for creating your own
skillsouko add template
```

**Local directory:**
```bash
# Single skill
skillsouko add ./my-skill/

# Multiple skills - interactive mode
skillsouko add ./my-collection/

# Multiple skills - flat (skip interactive)
skillsouko add ./my-collection/ --no-keep-structure
# → skills/skill-a/, skills/skill-b/, skills/skill-c/

# Multiple skills - preserve structure
skillsouko add ./my-collection/ --keep-structure
# → skills/my-collection/skill-a/, skills/my-collection/skill-b/

# Multiple skills - custom namespace
skillsouko add ./my-collection/ --keep-structure --namespace team-tools
# → skills/team-tools/skill-a/, skills/team-tools/skill-b/
```

**GitHub:**
```bash
# Specific skill from repository
skillsouko add https://github.com/user/repo/tree/main/skills/code-review

# All skills from repository
skillsouko add https://github.com/user/repo

# Force overwrite existing
skillsouko add https://github.com/user/repo --force
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

### skillsouko list

List installed skills.

```bash
skillsouko list [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum number to display | `100` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# List all skills
skillsouko list

# Limit results
skillsouko list --limit 20

# JSON output for scripting
skillsouko list --json
```

#### Output Format

**Default (table view):**
```
                       Skills (5)
 ID                    Description
 hello-world           A simple hello world skill for testing…
 pdf                   Extract text from PDF files
 team/code-review      Code review checklist and guidelines
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

### skillsouko search

Search for skills.

```bash
skillsouko search <query> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum results | `10` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Search by description
skillsouko search "PDF text extraction"

# Limit results
skillsouko search "code review" --limit 5

# JSON output
skillsouko search "testing" --json
```

---

### skillsouko show

Show skill details.

```bash
skillsouko show <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Show skill details
skillsouko show hello-world

# Show namespaced skill
skillsouko show team-tools/code-review

# JSON output
skillsouko show pdf --json
```

---

### skillsouko remove

Remove installed skills.

```bash
skillsouko remove <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--force`, `-f` | Skip confirmation | `false` |
| `--yes`, `-y` | Skip confirmation (alias for --force) | `false` |

#### Examples

```bash
# Remove with confirmation
skillsouko remove hello-world
# → Remove 'hello-world'? [y/N]

# Remove without confirmation
skillsouko remove hello-world --force

# Remove namespaced skill
skillsouko remove team-tools/code-review --force
```

---

### skillsouko lint

Validate skill files.

```bash
skillsouko lint [skill-id] [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output as JSON (for scripting/AI agents) | `false` |

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
skillsouko lint

# Lint specific skill
skillsouko lint hello-world
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

### skillsouko serve

Start the MCP server.

```bash
skillsouko serve [options]
```

#### Options

| Option | Description |
|--------|-------------|
| `--reindex` | Force reindex on startup |
| `--skip-auto-reindex` | Skip automatic reindex check |

#### Examples

```bash
# Start server
skillsouko serve

# Start with forced reindex
skillsouko serve --reindex
```

#### Legacy Mode

```bash
# 以下は同等 (後方互換)
skillsouko
skillsouko serve
```

> **Note**: `skillsouko --reindex` は **サポートしない**。常に `skillsouko serve --reindex` を使用すること。

---

### skillsouko sync

Sync installed skills to AGENTS.md for non-MCP agents (e.g., Claude Code without MCP).

```bash
skillsouko sync [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output file path | `./AGENTS.md` |
| `--append/--replace` | Append to existing file or replace entirely | `--append` |
| `--skills` | Comma-separated skill IDs to include | all |
| `--category` | Comma-separated categories to include | all |
| `--format` | Output format: `xml` or `markdown` | `xml` |
| `--mode`, `-m` | Target agent type: `cli` or `mcp` | `cli` |
| `--force`, `-f` | Overwrite without confirmation | `false` |

#### Mode

| Mode | Description |
|------|-------------|
| `cli` | For agents using CLI commands (`skillsouko show <id>`) |
| `mcp` | For agents using MCP tools (`search_skills`, `load_skill`) |

#### Examples

```bash
# Sync all skills to ./AGENTS.md
skillsouko sync

# Sync to specific file
skillsouko sync -o .claude/AGENTS.md

# Force overwrite without confirmation
skillsouko sync -f

# Filter by category
skillsouko sync --category development,testing

# Filter by skill IDs
skillsouko sync --skills pdf,code-review

# Use markdown format (no XML tags)
skillsouko sync --format markdown

# Generate for MCP-enabled agents
skillsouko sync --mode mcp

# Replace entire file instead of appending
skillsouko sync --replace
```

#### Output Format

The generated block includes:
1. **Markers** — `<!-- SKILLSOUKO_START -->` and `<!-- SKILLSOUKO_END -->` for safe updates
2. **Instructions** — Workflow and tips for agents
3. **Skills Table** — ID, Description, Category

**CLI mode output:**
```markdown
<!-- SKILLSOUKO_START -->
<available_skills>

## SkillSouko Skills

Skills are reusable expert knowledge...

### Workflow

1. **Find a skill** - Check the table below...
2. **Get instructions** - Run `skillsouko show <skill-id>`...
3. **Follow the instructions** - Execute the steps...

### Tips
...

### Available Skills

| ID | Description | Category |
|----|-------------|----------|
| pdf | Extract text from PDF files | tools |

</available_skills>
<!-- SKILLSOUKO_END -->
```

**MCP mode output:**
```markdown
<!-- SKILLSOUKO_START -->
<available_skills>

## SkillSouko Skills
...

### Workflow

1. **Search** - Call `search_skills(query)`...
2. **Load** - Call `load_skill(skill_id)`...
3. **Execute** - Follow the instructions...

### Tools

- `search_skills(query)` - Find skills by task description
- `load_skill(id)` - Get full instructions and path
- `read_skill_file(id, file)` - Read templates or config files

### Tips
...

### Available Skills
...

</available_skills>
<!-- SKILLSOUKO_END -->
```

#### Update Behavior

| Scenario | Behavior |
|----------|----------|
| File doesn't exist | Creates new file (including parent directories) |
| File has markers | Replaces content between markers |
| File without markers + `--append` | Appends to end |
| File without markers + `--replace` | Replaces entire file |

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
| `SKILLSOUKO_SKILLS_DIR` | Skills directory | `~/.skillsouko/skills` |
| `GITHUB_TOKEN` | GitHub authentication for private repos | |

## See Also

- [Configuration Guide](configuration.md) — All options, filtering, search
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way

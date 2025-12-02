# CLI Reference

SkillPort provides a command-line interface for managing [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) and running the MCP server.

## Overview

```bash
skillport <command> [options]

# Global overrides (CLI > env > default)
skillport --skills-dir ./skills --db-path ./index.lancedb add hello-world
# Place global flags before the subcommand (e.g., skillport --skills-dir ... add ...)
```

> **Note**: `skillport-mcp` is a legacy alias for `skillport`. Both work identically.

### Global options (all commands)

| Option | Description | Notes |
|--------|-------------|-------|
| `--skills-dir` | Override skills directory path | Applies to all commands in the invocation |
| `--db-path` | Override LanceDB path | Use together with `--skills-dir` to keep index in sync |

Precedence: CLI flag > environment variable (`SKILLPORT_SKILLS_DIR` / `SKILLPORT_DB_PATH`) > default (`~/.skillport/skills`, `~/.skillport/indexes/default/skills.lancedb`).

## Commands

### skillport init

Initialize SkillPort for a project. Creates configuration and syncs skills to instruction files.

```bash
skillport init [options]
```

#### What it does

1. Creates `.skillportrc` configuration file
2. Creates skills directory if it doesn't exist
3. Builds the skill index
4. Updates instruction files (AGENTS.md, etc.) with skills table

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--skills-dir`, `-d` | Skills directory path | Interactive selection |
| `--instructions`, `-i` | Instruction files to update (repeatable) | Interactive selection |
| `--yes`, `-y` | Skip prompts, use defaults | `false` |

#### Interactive Mode

When options are not specified, init prompts for configuration:

```
$ skillport init

╭──────────────────────────────────────────────────────────────╮
│              ⚓ SkillPort  v0.3.0                             │
│     🚢 All Your Agent Skills in One Place                    │
│                                                              │
│     🚀 Initialize your project for Agent Skills              │
╰──────────────────────────────────────────────────────────────╯

? Where are your skills located?
  [1] ~/.skillport/skills (global)
  [2] .claude/skills
  [3] .agent/skills
  [4] Custom path...

? Which instruction files to update? (comma-separated)
  [1] AGENTS.md (Codex, Cursor, Antigravity)
  [2] GEMINI.md (Gemini CLI)
  [3] None (skip)
  [4] Custom...

✓ Created .skillportrc
✓ Created ~/.skillport/skills/
✓ Indexed 3 skill(s)
✓ Updated AGENTS.md

✨ Ready! Start your coding agent to use skills.
   Run 'skillport add hello-world' to add your first skill
```

#### Non-Interactive Mode

```bash
# Use defaults (skills: ~/.skillport/skills, instructions: AGENTS.md)
skillport init --yes

# Specify explicitly
skillport init --skills-dir .agent/skills --instructions AGENTS.md --instructions GEMINI.md
```

#### Generated .skillportrc

```yaml
# SkillPort Configuration
# See: https://github.com/gotalab/skillport

skills_dir: ~/.skillport/skills
instructions:
  - AGENTS.md
```

The `instructions` list is used by `skillport sync --all` to update all files at once.

---

### skillport add

Add skills from various sources.

```bash
skillport add <source> [options]
```

#### Sources

| Type | Example | Description |
|------|---------|-------------|
| Built-in | `hello-world` | Sample skill bundled with SkillPort |
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
| `--json` | Output as JSON (for scripting/AI agents) | `false` |

#### Interactive Mode

ローカルパスまたは GitHub URL を指定し、`--keep-structure` も `--namespace` も指定しない場合、対話モードでスキルの追加先を選択できます。

```
$ skillport add ./my-collection/

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
skillport add hello-world

# Add template for creating your own
skillport add template
```

**Local directory:**
```bash
# Single skill
skillport add ./my-skill/

# Multiple skills - interactive mode
skillport add ./my-collection/

# Multiple skills - flat (skip interactive)
skillport add ./my-collection/ --no-keep-structure
# → skills/skill-a/, skills/skill-b/, skills/skill-c/

# Multiple skills - preserve structure
skillport add ./my-collection/ --keep-structure
# → skills/my-collection/skill-a/, skills/my-collection/skill-b/

# Multiple skills - custom namespace
skillport add ./my-collection/ --keep-structure --namespace team-tools
# → skills/team-tools/skill-a/, skills/team-tools/skill-b/
```

**GitHub:**
```bash
# Specific skill from repository
skillport add https://github.com/user/repo/tree/main/skills/code-review

# All skills from repository
skillport add https://github.com/user/repo

# Force overwrite existing
skillport add https://github.com/user/repo --force
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

### skillport list

List installed skills.

```bash
skillport list [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum number to display | `100` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# List all skills
skillport list

# Limit results
skillport list --limit 20

# JSON output for scripting
skillport list --json
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

### skillport search

Search for skills.

```bash
skillport search <query> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Maximum results | `10` |
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Search by description
skillport search "PDF text extraction"

# Limit results
skillport search "code review" --limit 5

# JSON output
skillport search "testing" --json
```

---

### skillport show

Show skill details.

```bash
skillport show <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output as JSON | `false` |

#### Examples

```bash
# Show skill details
skillport show hello-world

# Show namespaced skill
skillport show team-tools/code-review

# JSON output
skillport show pdf --json
```

---

### skillport remove

Remove installed skills.

```bash
skillport remove <skill-id> [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--force`, `-f` | Skip confirmation | `false` |
| `--yes`, `-y` | Skip confirmation (alias for --force) | `false` |

#### Examples

```bash
# Remove with confirmation
skillport remove hello-world
# → Remove 'hello-world'? [y/N]

# Remove without confirmation
skillport remove hello-world --force

# Remove namespaced skill
skillport remove team-tools/code-review --force
```

---

### skillport lint

Validate skill files.

```bash
skillport lint [skill-id] [options]
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
skillport lint

# Lint specific skill
skillport lint hello-world
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

### skillport serve

Start the MCP server.

```bash
skillport serve [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--http` | Run as HTTP server (Remote mode) | `false` |
| `--host` | HTTP server host (only with --http) | `127.0.0.1` |
| `--port` | HTTP server port (only with --http) | `8000` |
| `--reindex` | Force reindex on startup | `false` |
| `--skip-auto-reindex` | Skip automatic reindex check | `false` |

#### Transport Modes

| Mode | Command | Tools |
|------|---------|-------|
| **Local** (stdio) | `skillport serve` | `search_skills`, `load_skill` |
| **Remote** (HTTP) | `skillport serve --http` | + `read_skill_file` |

#### Examples

```bash
# Local mode (stdio) - for Claude Code, Cursor
skillport serve

# Remote mode (HTTP) - for network access
skillport serve --http

# Remote mode with custom host/port
skillport serve --http --host 0.0.0.0 --port 8000

# Start with forced reindex
skillport serve --reindex
```

#### Local vs Remote Mode

- **Local Mode (stdio)**: Agent が直接ファイルアクセス可能。`read_skill_file` は不要。
- **Remote Mode (HTTP)**: Agent はリモートからアクセス。`read_skill_file` でファイル取得。

#### Legacy Mode

```bash
# 以下は同等 (後方互換)
skillport
skillport serve
```

> **Note**: `skillport --reindex` は **サポートしない**。常に `skillport serve --reindex` を使用すること。

---

### skillport sync

Sync installed skills to instruction files (AGENTS.md, GEMINI.md, etc.).

```bash
skillport sync [options]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output file path | `./AGENTS.md` |
| `--all`, `-a` | Update all files in `.skillportrc` `instructions` | `false` |
| `--append/--replace` | Append to existing file or replace entirely | `--append` |
| `--skills` | Comma-separated skill IDs to include | all |
| `--category` | Comma-separated categories to include | all |
| `--format` | Output format: `xml` or `markdown` | `xml` |
| `--mode`, `-m` | Target agent type: `cli` or `mcp` | `cli` |
| `--force`, `-f` | Overwrite without confirmation | `false` |

> **Note:** When `--all` is specified, `--output` is ignored and all files listed in `.skillportrc` `instructions` are updated.

#### Mode

| Mode | Description |
|------|-------------|
| `cli` | For agents using CLI commands (`skillport show <id>`) |
| `mcp` | For agents using MCP tools (`search_skills`, `load_skill`) |

#### Examples

```bash
# Sync all skills to ./AGENTS.md
skillport sync

# Update all instruction files from .skillportrc
skillport sync --all

# Sync to specific file
skillport sync -o .claude/AGENTS.md

# Force overwrite without confirmation
skillport sync -f

# Filter by category
skillport sync --category development,testing

# Filter by skill IDs
skillport sync --skills pdf,code-review

# Use markdown format (no XML tags)
skillport sync --format markdown

# Generate for MCP-enabled agents
skillport sync --mode mcp

# Replace entire file instead of appending
skillport sync --replace
```

#### Output Format

The generated block includes:
1. **Markers** — `<!-- SKILLPORT_START -->` and `<!-- SKILLPORT_END -->` for safe updates
2. **Instructions** — Workflow and tips for agents
3. **Skills Table** — ID, Description, Category

**CLI mode output:**
```markdown
<!-- SKILLPORT_START -->
<available_skills>

## SkillPort Skills

Skills are reusable expert knowledge...

### Workflow

1. **Find a skill** - Check the table below...
2. **Get instructions** - Run `skillport show <skill-id>`...
3. **Follow the instructions** - Execute the steps...

### Tips
...

### Available Skills

| ID | Description | Category |
|----|-------------|----------|
| pdf | Extract text from PDF files | tools |

</available_skills>
<!-- SKILLPORT_END -->
```

**MCP mode output:**
```markdown
<!-- SKILLPORT_START -->
<available_skills>

## SkillPort Skills
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
<!-- SKILLPORT_END -->
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

## Configuration

### Resolution Order

CLI commands resolve `skills_dir` in this order:

1. **Environment variable** — `SKILLPORT_SKILLS_DIR`
2. **Project config** — `.skillportrc` or `pyproject.toml [tool.skillport]`
3. **Default** — `~/.skillport/skills`

### Project Configuration (.skillportrc)

Created by `skillport init`. Defines project-specific settings:

```yaml
# .skillportrc
skills_dir: .agent/skills
instructions:
  - AGENTS.md
  - GEMINI.md
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_SKILLS_DIR` | Skills directory | `~/.skillport/skills` |
| `GITHUB_TOKEN` | GitHub authentication for private repos | |

## See Also

- [Configuration Guide](configuration.md) — All options, filtering, search
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way

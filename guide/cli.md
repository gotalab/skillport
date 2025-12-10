# CLI Reference

SkillPort provides a command-line interface for managing [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) and running the MCP server.

## Table of Contents

- [Overview](#overview)
- [Commands](#commands)
  - [init](#skillport-init) - Initialize project
  - [add](#skillport-add) - Add skills
  - [update](#skillport-update) - Update skills
  - [list](#skillport-list) - List installed skills
  - [search](#skillport-search) - Search skills
  - [show](#skillport-show) - Show skill details
  - [remove](#skillport-remove) - Remove skills
  - [lint](#skillport-lint) - Validate skills
  - [serve](#skillport-serve) - Start MCP server
  - [doc](#skillport-doc) - Generate AGENTS.md
- [Exit Codes](#exit-codes)
- [Configuration](#configuration)

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
| `--auto-reindex/--no-auto-reindex` | Control automatic index rebuilding | Default: enabled; respects `SKILLPORT_AUTO_REINDEX` env var |

Precedence: CLI flag > environment variable (`SKILLPORT_SKILLS_DIR` / `SKILLPORT_DB_PATH`) > default (`~/.skillport/skills`, `~/.skillport/indexes/default/skills.lancedb`).

## Commands

### skillport init

Initialize SkillPort for a project. Creates configuration and generates skills to instruction files.

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
  [1] ~/.skillport/skills (default)
  [2] .claude/skills (Claude Code)
  [3] ~/.codex/skills (Codex)
  [4] .agent/skills
  [5] Custom path...

? Which instruction files to update? (comma-separated)
  [1] AGENTS.md (Codex, Cursor, Windsurf)
  [2] GEMINI.md (Gemini CLI, Antigravity)
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
  - GEMINI.md
```

The `instructions` list is used by `skillport doc --all` to update all files at once.

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
| Local | `./mixed/` | Directory containing both skill directories and zip files |
| Zip | `./my-skill.zip` | Single skill in zip format (1 zip = 1 skill) |
| GitHub | `https://github.com/user/repo` | Repository root (auto-detects default branch) |
| GitHub | `https://github.com/user/repo/tree/main/skills` | Specific directory |

> **Zip file support**:
> - Each zip file must contain exactly one skill
> - Zip files in a directory are automatically detected and extracted
> - Useful for skills exported from Claude.ai

> **GitHub URL support**:
> - Works with or without trailing slash
> - Auto-detects default branch when not specified
> - Private repositories require `GITHUB_TOKEN` environment variable

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

When specifying a local path or GitHub URL without `--keep-structure` or `--namespace`, interactive mode lets you choose where to add skills.

```
$ skillport add ./my-collection/

Found 3 skill(s): skill-a, skill-b, skill-c
Where to add?
  [1] Flat       → skills/skill-a/, skills/skill-b/, ...
  [2] Namespace  → skills/<ns>/skill-a/, ...
  [3] Skip
Choice [1/2/3] (1):
```

| Choice | Behavior |
|--------|----------|
| `1` Flat | Add flat (`--no-keep-structure` equivalent) |
| `2` Namespace | Add with namespace. Prompts for namespace name |
| `3` Skip | Exit without adding |

> **Note**: Built-in skills (`hello-world`, `template`) skip interactive mode.

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

**Zip files:**
```bash
# Single zip file (exported from Claude.ai, etc.)
skillport add ./my-skill.zip

# Directory containing both zips and skill directories
skillport add ./mixed/
# ./mixed/
# ├── a.zip         → extracted and added
# ├── b.zip         → extracted and added
# ├── skill-c/      → added as usual
# └── skill-d/      → added as usual

# Zip with namespace
skillport add ./my-skill.zip --namespace my-ns
# → skills/my-ns/my-skill/
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

**All succeeded:**
```
  ✓ Added 'skill-a'
  ✓ Added 'skill-b'
Added 2 skill(s)
```

**Some skipped (already exists):**
```
  ✓ Added 'skill-c'
  ⊘ Skipped 'skill-a' (exists)
  ⊘ Skipped 'skill-b' (exists)
Added 1, skipped 2 (use --force to overwrite)
```

---

### skillport update

Update skills from their original sources (GitHub or local).

```bash
skillport update [skill-id] [options]
```

#### What it does

1. Checks for available updates from original sources
2. Detects local modifications (prevents accidental overwrites)
3. Updates skill files and tracks version history
4. Rebuilds the skill index after updates

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--all`, `-a` | Update all updatable skills | `false` |
| `--force`, `-f` | Overwrite local modifications | `false` |
| `--dry-run`, `-n` | Show what would be updated without making changes | `false` |
| `--check`, `-c` | Check for available updates without updating | `false` |
| `--json` | Output as JSON (for scripting/AI agents) | `false` |

#### Default Behavior

When invoked without arguments, `skillport update` automatically enters check mode:

```
$ skillport update

Updates available:
  my-skill (github @ def5678)
  team/code-review (github @ abc1234) (local changes)

Run 'skillport update --all' to update all, or 'skillport update <skill-id>' for one.

Up to date: 3 skill(s)
Not updatable: 1 skill(s)
Untracked: 2 skill(s)
  → Use 'skillport add <source>' to track

Update all listed skills now? [y/N]:
```

If updates are available, you'll be prompted to update them interactively.

#### Untracked Skills

Skills that exist in the skills directory but were not added via `skillport add` are shown as "Untracked". These include:
- Skills copied manually to the skills directory
- Skills from older versions before origin tracking was added
- Skills created directly in the skills directory

To track an untracked skill, add it from its original source:
```bash
skillport add https://github.com/user/repo/tree/main/skills/my-skill
```

#### Examples

**Check for updates:**
```bash
# Show available updates (default behavior)
skillport update

# Explicit check mode (non-interactive)
skillport update --check
```

**Update skills:**
```bash
# Update a single skill
skillport update my-skill

# Update all updatable skills
skillport update --all

# Force update despite local modifications
skillport update my-skill --force

# Preview changes without updating
skillport update --all --dry-run
```

**JSON output (for scripting):**
```bash
# Check updates as JSON
skillport update --check --json

# Bulk update with JSON output
skillport update --all --json
```

#### Update Sources

Skills track their original source (origin) and can be updated from:

| Origin | Description |
|--------|-------------|
| **GitHub** | Checks commit SHA, downloads only when changed |
| **Local** | Compares content hash with source directory |
| **Zip** | Checks file mtime, re-extracts and compares content hash when changed |
| **Built-in** | Cannot be updated (bundled with SkillPort) |

#### Local Modification Detection

SkillPort tracks a content hash for each skill. If you manually edit a skill's files:

```
$ skillport update my-skill

⚠ Local modifications detected in 'my-skill'
  Use --force to overwrite local changes
```

Use `--force` to overwrite, or update the source and re-add the skill.

#### Output

**Single skill updated:**
```
  + Updated 'my-skill' (abc1234 -> def5678)
✓ Updated my-skill from github
Rebuilding index...
```

**Bulk update:**
```
  + Updated 'skill-a' (abc1234 -> def5678)
  + Updated 'skill-b'
  - 3 skill(s) already up to date
✓ Updated 2 skill(s)
Rebuilding index...
```

**Already up to date:**
```
  - 'my-skill' is already up to date
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (or no updates available) |
| 1 | Error or local modifications detected (without `--force`) |

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
| `--json` | Output as JSON (for scripting/AI agents) | `false` |

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

**Fatal (validation fails)**

| Rule | Description |
|------|-------------|
| `name` required | Missing name in frontmatter |
| `description` required | Missing description in frontmatter |
| name = directory | Name doesn't match directory name |
| name ≤ 64 chars | Name is too long |
| name pattern | Only `a-z`, `0-9`, `-` allowed |
| no leading/trailing hyphen | Name cannot start or end with `-` |
| no consecutive hyphens | Name cannot contain `--` |
| reserved words | Name cannot contain `anthropic` or `claude` |
| description ≤ 1024 chars | Description is too long |
| no XML tags in description | Description contains `<tag>` |

**Warning (warning only)**

| Rule | Description |
|------|-------------|
| SKILL.md ≤ 500 lines | File is too long |
| allowed frontmatter keys | Only `name`, `description`, `license`, `allowed-tools`, `metadata` |

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

- **Local Mode (stdio)**: Agent has direct file access. `read_skill_file` is not needed.
- **Remote Mode (HTTP)**: Agent accesses remotely. Use `read_skill_file` to fetch files.

#### Legacy Mode

```bash
# The following are equivalent (backward compatible)
skillport
skillport serve
```

> **Note**: `skillport --reindex` is **not supported**. Always use `skillport serve --reindex`.

---

### skillport doc

Generate skill documentation for instruction files (AGENTS.md, etc.).

```bash
skillport doc [options]
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
# Generate skill docs to ./AGENTS.md
skillport doc

# Update all instruction files from .skillportrc
skillport doc --all

# Generate to specific file
skillport doc -o .claude/AGENTS.md

# Force overwrite without confirmation
skillport doc -f

# Filter by category
skillport doc --category development,testing

# Filter by skill IDs
skillport doc --skills pdf,code-review

# Use markdown format (no XML tags)
skillport doc --format markdown

# Generate for MCP-enabled agents
skillport doc --mode mcp

# Replace entire file instead of appending
skillport doc --replace
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

For full configuration options, see [Configuration Guide](configuration.md).

### Quick Reference

CLI commands resolve `skills_dir` / `db_path` in this order:

1. **CLI flags** — `--skills-dir`, `--db-path`
2. **Environment variables** — `SKILLPORT_SKILLS_DIR`, `SKILLPORT_DB_PATH`
3. **Project config** — `.skillportrc` or `pyproject.toml [tool.skillport]`
4. **Default** — `~/.skillport/skills`

### Key Environment Variables

| Variable | Description |
|----------|-------------|
| `SKILLPORT_SKILLS_DIR` | Skills directory |
| `SKILLPORT_AUTO_REINDEX` | Enable/disable automatic reindexing |
| `GITHUB_TOKEN` | GitHub authentication for private repos |

## See Also

- [Configuration Guide](configuration.md) — All options, filtering, search
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way
